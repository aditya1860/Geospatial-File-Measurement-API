from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class FileStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class FileUploadResponse(BaseModel):
    id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Uploaded file name")
    file_type: str = Field(..., description="Detected file format (.shp / .kml)")
    feature_count: int = Field(0, description="Total number of features extracted")
    crs: str = Field(..., description="Detected Coordinate Reference System (e.g. EPSG:4326)")
    status: FileStatus = Field(FileStatus.COMPLETED, description="Processing status")
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Upload timestamp")
    message: Optional[str] = Field("File processed successfully", description="Status message")

class FileInfoResponse(BaseModel):
    id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Uploaded file name")
    file_type: str = Field(..., description="Detected file format (.shp / .kml)")
    feature_count: int = Field(..., description="Total number of features")
    crs: str = Field(..., description="Detected Coordinate Reference System (e.g. EPSG:4326)")
    status: FileStatus = Field(..., description="Processing status")
    file_size_bytes: Optional[int] = Field(None, description="Size of uploaded file in bytes")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    error_message: Optional[str] = Field(None, description="Error message if status is FAILED")

class FileListResponse(BaseModel):
    total: int = Field(..., description="Total number of files stored")
    files: List[FileInfoResponse] = Field(..., description="List of file records")
