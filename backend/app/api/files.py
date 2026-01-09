"""File CRUD API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func
from app.database import get_session
from app.models.user import User
from app.models.project import Project
from app.models.file import File, FileCreate, FileUpdate, FileRead, FileReadWithContent
from app.api.deps import get_current_user
from app.config import settings
from app.utils.access import verify_project_access

router = APIRouter(prefix="/projects/{project_id}/files", tags=["files"])


def validate_code_content(content: str, filename: str) -> dict:
    """Validate code content and return warnings/errors."""
    result = {"valid": True, "warnings": [], "errors": []}

    # Check for empty content
    stripped = content.strip()
    if not stripped:
        result["valid"] = False
        result["errors"].append("File content cannot be empty")
        return result

    # Check minimum length
    if len(stripped) < 10:
        result["warnings"].append("File content is very short - review may be limited")

    # Check for common code indicators
    code_indicators = [
        'def ', 'class ', 'function', 'import ', 'from ', 'const ', 'let ', 'var ',
        'public ', 'private ', 'return', 'if ', 'for ', 'while ', '#include',
        '<?php', '<!DOCTYPE', '<html', 'package ', 'func ', 'fn ', 'struct '
    ]

    has_code = any(indicator in content for indicator in code_indicators)

    # Check for brackets/symbols common in code
    code_symbols = ['{', '}', '(', ')', '[', ']', ';', ':', '=']
    symbol_count = sum(content.count(s) for s in code_symbols)

    if not has_code and symbol_count < 5:
        result["warnings"].append("Content doesn't appear to be code - review results may be irrelevant")

    # Check for repetitive/garbage content
    lines = stripped.split('\n')
    if len(lines) > 3:
        unique_lines = set(line.strip() for line in lines if line.strip())
        if len(unique_lines) < len(lines) * 0.3:
            result["warnings"].append("Many repeated lines detected - may indicate low-quality content")

    # Check for binary/garbage characters
    non_printable = sum(1 for c in content if ord(c) < 32 and c not in '\n\r\t')
    if non_printable > len(content) * 0.1:
        result["valid"] = False
        result["errors"].append("File contains too many non-printable characters - may be binary file")

    return result


@router.post("", response_model=FileRead, status_code=status.HTTP_201_CREATED)
async def create_file(
    project_id: int,
    file_data: FileCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new file in a project."""
    project = await verify_project_access(project_id, current_user, session)

    # Validate content
    validation = validate_code_content(file_data.content, file_data.name)
    if not validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation["errors"][0] if validation["errors"] else "Invalid file content"
        )

    # Check file count limit
    file_count_stmt = select(func.count(File.id)).where(File.project_id == project_id)
    file_count = session.exec(file_count_stmt).one()

    if file_count >= settings.max_files_per_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {settings.max_files_per_project} files per project"
        )

    # Check file size
    content_bytes = len(file_data.content.encode('utf-8'))
    if content_bytes > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum of {settings.max_file_size_mb}MB"
        )

    # Create file
    file = File(
        project_id=project_id,
        name=file_data.name,
        content=file_data.content,
        language=file_data.language,
        size_bytes=content_bytes,
        content_hash=File.compute_hash(file_data.content)
    )

    session.add(file)
    session.commit()
    session.refresh(file)

    # Update project timestamp
    from datetime import datetime
    project.updated_at = datetime.utcnow()
    session.add(project)
    session.commit()

    # Return file - FastAPI will use response_model to convert
    return file


@router.get("", response_model=list[FileRead])
async def list_files(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """List all files in a project."""
    await verify_project_access(project_id, current_user, session)

    statement = (
        select(File)
        .where(File.project_id == project_id)
        .order_by(File.name)
    )
    files = session.exec(statement).all()

    return files


@router.get("/{file_id}", response_model=FileReadWithContent)
async def get_file(
    project_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get a specific file with its content."""
    await verify_project_access(project_id, current_user, session)

    file = session.get(File, file_id)

    if not file or file.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    return file


@router.patch("/{file_id}", response_model=FileRead)
async def update_file(
    project_id: int,
    file_id: int,
    file_update: FileUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update a file."""
    project = await verify_project_access(project_id, current_user, session)

    file = session.get(File, file_id)

    if not file or file.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Update fields
    update_data = file_update.model_dump(exclude_unset=True)

    if "content" in update_data:
        content = update_data["content"]
        content_bytes = len(content.encode('utf-8'))

        if content_bytes > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum of {settings.max_file_size_mb}MB"
            )

        file.content = content
        file.size_bytes = content_bytes
        file.content_hash = File.compute_hash(content)

    for field, value in update_data.items():
        if field != "content":
            setattr(file, field, value)

    from datetime import datetime
    file.updated_at = datetime.utcnow()
    project.updated_at = datetime.utcnow()

    session.add(file)
    session.add(project)
    session.commit()
    session.refresh(file)

    return file


@router.post("/validate", response_model=dict)
async def validate_files(
    project_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Validate all files in a project before review."""
    await verify_project_access(project_id, current_user, session)

    statement = select(File).where(File.project_id == project_id)
    files = session.exec(statement).all()

    if not files:
        return {
            "valid": False,
            "can_review": False,
            "errors": ["No files in project"],
            "warnings": [],
            "files": []
        }

    all_warnings = []
    all_errors = []
    file_validations = []
    total_code_size = 0

    for file in files:
        validation = validate_code_content(file.content, file.name)
        total_code_size += len(file.content)

        file_validations.append({
            "id": file.id,
            "name": file.name,
            "valid": validation["valid"],
            "warnings": validation["warnings"],
            "errors": validation["errors"]
        })

        all_warnings.extend([f"{file.name}: {w}" for w in validation["warnings"]])
        all_errors.extend([f"{file.name}: {e}" for e in validation["errors"]])

    # Overall validation
    has_valid_files = any(f["valid"] for f in file_validations)

    if total_code_size < 20:
        all_warnings.append("Very little code to review - results may be limited")

    return {
        "valid": len(all_errors) == 0,
        "can_review": has_valid_files,
        "errors": all_errors,
        "warnings": all_warnings,
        "files": file_validations,
        "total_size": total_code_size
    }


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    project_id: int,
    file_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete a file."""
    project = await verify_project_access(project_id, current_user, session)

    file = session.get(File, file_id)

    if not file or file.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    session.delete(file)

    # Update project timestamp
    from datetime import datetime
    project.updated_at = datetime.utcnow()
    session.add(project)

    session.commit()

    return None
