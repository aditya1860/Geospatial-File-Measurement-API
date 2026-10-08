import os
import zipfile
from pathlib import Path
from typing import List, Tuple
from fastapi import HTTPException, UploadFile, status
from app.config import settings

def validate_uploaded_file(upload_file: UploadFile) -> str:
    """
    Validates file extension and basic file characteristics.
    Returns the normalized extension.
    """
    if not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty."
        )
    
    file_ext = Path(upload_file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file_ext}'. Allowed formats: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    return file_ext

def validate_and_extract_shapefile_zip(zip_path: Path, extract_dir: Path) -> Path:
    """
    Validates zip integrity, protects against Zip Slip attacks,
    extracts contents, and locates the main .shp file.
    """
    if not zipfile.is_zipfile(zip_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid ZIP archive."
        )

    extract_dir.mkdir(parents=True, exist_ok=True)
    resolved_target_dir = extract_dir.resolve()

    shp_files: List[Path] = []

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for member in zip_ref.infolist():
            # Security check: Zip Slip path traversal mitigation
            member_path = (extract_dir / member.filename).resolve()
            if not str(member_path).startswith(str(resolved_target_dir)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Zip file contains unsafe path traversal member: {member.filename}"
                )
            
            # Extract
            zip_ref.extract(member, extract_dir)
            if member.filename.lower().endswith(".shp") and not member.filename.startswith("__MACOSX"):
                shp_files.append(member_path)

    if not shp_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ZIP archive must contain at least one valid .shp (Shapefile) file."
        )

    # Return the primary .shp file
    return shp_files[0]
