"""Authentication API endpoints."""
import logging
import re
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select
from app.database import get_session
from app.models.user import User, UserCreate, UserLogin, UserRead, Token, TokenWithRefresh, RefreshTokenRequest, PasswordChange
from app.utils.auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_refresh_token
from app.utils.audit import log_audit_event, get_client_ip, get_user_agent
from app.utils.rate_limit import check_rate_limit
from app.models.audit import AuditAction
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password meets security requirements.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Hasło musi mieć minimum 8 znaków"
    if not re.search(r'[A-Z]', password):
        return False, "Hasło musi zawierać przynajmniej jedną wielką literę"
    if not re.search(r'[a-z]', password):
        return False, "Hasło musi zawierać przynajmniej jedną małą literę"
    if not re.search(r'\d', password):
        return False, "Hasło musi zawierać przynajmniej jedną cyfrę"
    return True, ""


def validate_email_format(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, request: Request, session: Session = Depends(get_session)):
    """Register a new user."""
    try:
        logger.info(f"Registration attempt for email domain: {user_data.email.split('@')[-1] if '@' in user_data.email else 'invalid'}")

        # Validate email format
        if not validate_email_format(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nieprawidłowy format adresu email"
            )

        # Validate password strength
        is_valid, error_msg = validate_password_strength(user_data.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Check if email already exists
        statement = select(User).where(User.email == user_data.email)
        existing_user = session.exec(statement).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ten email jest już zarejestrowany"
            )

        # Check if username already exists
        statement = select(User).where(User.username == user_data.username)
        existing_user = session.exec(statement).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ta nazwa użytkownika jest już zajęta"
            )

        hashed_pw = hash_password(user_data.password)

        # Create new user
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_pw
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        logger.info(f"User registered successfully: ID={user.id}")

        # Log audit event
        await log_audit_event(
            session=session,
            action=AuditAction.REGISTER,
            user_id=user.id,
            resource_type="user",
            resource_id=user.id,
            details=f"User registered: {user.username}",
            request=request,
        )

        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {type(e).__name__}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rejestracja nie powiodła się. Spróbuj ponownie później."
        )


@router.post("/login", response_model=TokenWithRefresh)
async def login(credentials: UserLogin, request: Request, session: Session = Depends(get_session)):
    """Login and get access and refresh tokens.

    Rate limited to 5 attempts per minute per IP address to prevent brute force attacks.
    """
    # Apply login-specific rate limiting (5 attempts per minute)
    check_rate_limit(request, user_id=None, limit=5)

    # Find user by email
    statement = select(User).where(User.email == credentials.email)
    user = session.exec(statement).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    # Create tokens
    token_data = {"user_id": user.id, "email": user.email}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    logger.info(f"User logged in: ID={user.id}")

    # Log audit event
    await log_audit_event(
        session=session,
        action=AuditAction.LOGIN,
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        details="User logged in successfully",
        request=request,
    )

    return TokenWithRefresh(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenWithRefresh)
async def refresh_tokens(
    refresh_request: RefreshTokenRequest,
    request: Request,
    session: Session = Depends(get_session)
):
    """Refresh access token using refresh token."""
    # Decode refresh token
    payload = decode_refresh_token(refresh_request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user
    user_id = payload.get("user_id")
    user = session.get(User, user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new tokens
    token_data = {"user_id": user.id, "email": user.email}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    logger.info(f"Tokens refreshed for user: ID={user.id}")

    # Log audit event
    await log_audit_event(
        session=session,
        action=AuditAction.TOKEN_REFRESH,
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        details="Tokens refreshed",
        request=request,
    )

    return TokenWithRefresh(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserRead)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information."""
    return current_user


@router.patch("/me/password")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Change current user's password."""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowe obecne hasło"
        )

    # Validate new password strength
    is_valid, error_msg = validate_password_strength(password_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Update password
    current_user.hashed_password = hash_password(password_data.new_password)
    session.add(current_user)
    session.commit()

    logger.info(f"Password changed for user: ID={current_user.id}")

    # Log audit event
    await log_audit_event(
        session=session,
        action=AuditAction.PASSWORD_CHANGE,
        user_id=current_user.id,
        resource_type="user",
        resource_id=current_user.id,
        details="Password changed successfully",
        request=request,
    )

    return {"message": "Hasło zostało zmienione pomyślnie"}
