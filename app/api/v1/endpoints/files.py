import shutil
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, status

from app.config import settings
from app.schemas.file import FileUploadResponse, FileInfoResponse, FileListResponse, FileStatus
from app.schemas.measurement import FileMeasurementsResponse
from app.services.file_storage import FileStorageService
from app.services.parser_service import ParserService
from app.services.measurement_service import MeasurementService
from app.utils.file_validator import validate_uploaded_file, validate_and_extract_shapefile_zip
from app.utils.logger import logger

router = APIRouter(prefix="/files", tags=["Geospatial Files"])

@router.post("/", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_and_process_file(file: UploadFile = File(...)):
    """
    Upload and process a geospatial file (.zip containing Shapefile or .kml).
    Extracts features, reprojects CRS to optimal metric coordinate system, and computes measurements.
    """
    file_ext = validate_uploaded_file(file)
    file_id = str(uuid.uuid4())[:8]

    # Target directory for this upload
    file_upload_dir = settings.UPLOAD_DIR / file_id
    file_upload_dir.mkdir(parents=True, exist_ok=True)
    
    saved_file_path = file_upload_dir / file.filename

    # Save uploaded file
    try:
        with saved_file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Error saving uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    finally:
        await file.close()

    file_size = saved_file_path.stat().st_size
    file_type = "Shapefile (.zip)" if file_ext == ".zip" else "KML (.kml)"

    # Record initial file status
    FileStorageService.create_file_record(
        file_id=file_id,
        filename=file.filename,
        file_type=file_type,
        file_path=str(saved_file_path),
        file_size_bytes=file_size
    )

    try:
        # Step 1: Parse Features based on format
        if file_ext == ".zip":
            extract_dir = file_upload_dir / "extracted"
            shp_path = validate_and_extract_shapefile_zip(saved_file_path, extract_dir)
            features, source_crs = ParserService.parse_shapefile(shp_path)
        elif file_ext == ".kml":
            features, source_crs = ParserService.parse_kml(saved_file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file extension.")

        crs_str = source_crs.to_string() if hasattr(source_crs, "to_string") else str(source_crs)
        if "EPSG" in crs_str.upper() or "4326" in crs_str:
            try:
                epsg_code = source_crs.to_epsg()
                if epsg_code:
                    crs_str = f"EPSG:{epsg_code}"
            except Exception:
                pass

        # Step 2: Compute Measurements and Reprojections
        measurements, summary, default_proj_crs = MeasurementService.process_all_measurements(
            features=features,
            source_crs=source_crs
        )

        # Step 3: Persist results in SQLite database
        FileStorageService.update_file_success(
            file_id=file_id,
            feature_count=len(features),
            crs=crs_str,
            default_projected_crs=default_proj_crs,
            summary=summary,
            features=features,
            measurements=measurements
        )

        return FileUploadResponse(
            id=file_id,
            filename=file.filename,
            file_type=file_type,
            feature_count=len(features),
            crs=crs_str,
            status=FileStatus.COMPLETED,
            message="Geospatial file uploaded, parsed, and measured successfully."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing file {file_id}: {e}", exc_info=True)
        FileStorageService.update_file_failure(file_id=file_id, error_message=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process geospatial file: {str(e)}"
        )

@router.get("/", response_model=FileListResponse)
async def list_files():
    """List all uploaded geospatial files and their current status."""
    files = FileStorageService.list_all_files()
    return FileListResponse(total=len(files), files=files)

@router.get("/{file_id}/", response_model=FileInfoResponse)
async def get_file_info(file_id: str):
    """
    Returns information about the uploaded file.
    Example: { "id": "abc123", "filename": "survey.kml", "feature_count": 120, "crs": "EPSG:4326", "status": "COMPLETED" }
    """
    return FileStorageService.get_file_info(file_id)

@router.get("/{file_id}/measurements/", response_model=FileMeasurementsResponse)
async def get_file_measurements(file_id: str):
    """
    Returns spatial measurements (area for polygons, length for linestrings) for all features in the file.
    """
    return FileStorageService.get_file_measurements(file_id)

@router.delete("/{file_id}/", status_code=status.HTTP_200_OK)
async def delete_file(file_id: str):
    """Deletes the file and its associated feature records."""
    FileStorageService.delete_file(file_id)
    return {"message": f"File '{file_id}' successfully deleted."}
