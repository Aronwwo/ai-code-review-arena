"""Authentication API endpoints."""
import logging
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlmodel import Session, select
from app.database import get_session
from app.models.user import User, UserCreate, UserLogin, UserRead, Token, TokenWithRefresh, RefreshTokenRequest, PasswordChange
from app.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.utils.validation import validate_email_format, validate_password_strength
from app.config import settings
from app.utils.audit import log_audit_event, get_client_ip, get_user_agent
from app.utils.rate_limit import check_rate_limit
from app.models.audit import AuditAction
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> str:
    csrf_token = secrets.token_urlsafe(32)
    secure = settings.is_production
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=secure,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )
    return csrf_token


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
async def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    session: Session = Depends(get_session)
):
    """Login and get access and refresh tokens.

    Rate limited to 5 attempts per minute per IP address to prevent brute force attacks.
    """
    logger.info(f"Login attempt for email: {credentials.email}")

    # Apply login-specific rate limiting (5 attempts per minute)
    check_rate_limit(request, user_id=None, limit=5)

    # Find user by email
    statement = select(User).where(User.email == credentials.email)
    user = session.exec(statement).first()

    logger.info(f"User found: {user is not None}")
    if user:
        password_valid = verify_password(credentials.password, user.hashed_password)
        logger.info(f"Password valid: {password_valid}")

    if not user or not verify_password(credentials.password, user.hashed_password):
        logger.warning(f"Login failed for: {credentials.email}")
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

    _set_auth_cookies(response, access_token, refresh_token)
    return TokenWithRefresh(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenWithRefresh)
async def refresh_tokens(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    refresh_request: RefreshTokenRequest | None = None,
):
    """Refresh access token using refresh token."""
    # Decode refresh token
    refresh_token = None
    if refresh_request:
        refresh_token = refresh_request.refresh_token
    if not refresh_token:
        refresh_token = request.cookies.get("refresh_token")
    payload = decode_refresh_token(refresh_token) if refresh_token else None
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

    _set_auth_cookies(response, access_token, refresh_token)
    return TokenWithRefresh(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout")
async def logout(response: Response):
    """Clear auth cookies."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("csrf_token", path="/")
    return {"detail": "Logged out"}


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
