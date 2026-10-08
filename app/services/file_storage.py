import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from shapely.geometry import mapping

from app.models.storage import db_manager
from app.schemas.file import FileInfoResponse, FileStatus
from app.schemas.measurement import (
    FeatureMeasurement,
    MeasurementSummary,
    FileMeasurementsResponse,
    MeasurementValues
)
from app.services.parser_service import ParsedFeature

class FileStorageService:
    @staticmethod
    def create_file_record(
        file_id: str,
        filename: str,
        file_type: str,
        file_path: str,
        file_size_bytes: int,
        crs: str = "UNKNOWN"
    ) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO files (
                    id, filename, file_type, file_path, file_size_bytes, 
                    feature_count, crs, status, uploaded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id,
                filename,
                file_type,
                file_path,
                file_size_bytes,
                0,
                crs,
                FileStatus.PROCESSING.value,
                now_str
            ))
            conn.commit()

    @staticmethod
    def update_file_success(
        file_id: str,
        feature_count: int,
        crs: str,
        default_projected_crs: str,
        summary: MeasurementSummary,
        features: List[ParsedFeature],
        measurements: List[FeatureMeasurement]
    ) -> None:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Update file record
            cursor.execute("""
                UPDATE files
                SET feature_count = ?,
                    crs = ?,
                    status = ?,
                    default_projected_crs = ?,
                    summary_json = ?
                WHERE id = ?
            """, (
                feature_count,
                crs,
                FileStatus.COMPLETED.value,
                default_projected_crs,
                summary.model_dump_json(),
                file_id
            ))

            # Insert feature records
            for feat, meas in zip(features, measurements):
                geom_json = json.dumps(mapping(feat.geometry)) if feat.geometry else "{}"
                props_json = json.dumps(feat.properties, default=str)
                meas_json = meas.measurements.model_dump_json()

                cursor.execute("""
                    INSERT INTO features (
                        file_id, feature_id, geometry_type, geometry_json,
                        properties_json, is_measurable, measurements_json,
                        projected_crs, status, note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_id,
                    meas.feature_id,
                    meas.geometry_type,
                    geom_json,
                    props_json,
                    meas.is_measurable,
                    meas_json,
                    meas.projected_crs,
                    meas.status,
                    meas.note
                ))

            conn.commit()

    @staticmethod
    def update_file_failure(file_id: str, error_message: str) -> None:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE files
                SET status = ?,
                    error_message = ?
                WHERE id = ?
            """, (
                FileStatus.FAILED.value,
                error_message,
                file_id
            ))
            conn.commit()

    @staticmethod
    def get_file_info(file_id: str) -> FileInfoResponse:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File with ID '{file_id}' not found."
                )

            return FileInfoResponse(
                id=row["id"],
                filename=row["filename"],
                file_type=row["file_type"],
                feature_count=row["feature_count"],
                crs=row["crs"],
                status=FileStatus(row["status"]),
                file_size_bytes=row["file_size_bytes"],
                uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
                error_message=row["error_message"]
            )

    @staticmethod
    def list_all_files() -> List[FileInfoResponse]:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files ORDER BY uploaded_at DESC")
            rows = cursor.fetchall()
            return [
                FileInfoResponse(
                    id=row["id"],
                    filename=row["filename"],
                    file_type=row["file_type"],
                    feature_count=row["feature_count"],
                    crs=row["crs"],
                    status=FileStatus(row["status"]),
                    file_size_bytes=row["file_size_bytes"],
                    uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
                    error_message=row["error_message"]
                )
                for row in rows
            ]

    @staticmethod
    def get_file_measurements(file_id: str) -> FileMeasurementsResponse:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE id = ?", (file_id,))
            file_row = cursor.fetchone()
            if not file_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File with ID '{file_id}' not found."
                )

            if file_row["status"] == FileStatus.FAILED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File processing failed: {file_row['error_message']}"
                )

            # Parse summary
            summary_dict = json.loads(file_row["summary_json"] or "{}")
            summary = MeasurementSummary(**summary_dict) if summary_dict else MeasurementSummary()

            # Retrieve feature measurements
            cursor.execute("SELECT * FROM features WHERE file_id = ? ORDER BY id ASC", (file_id,))
            feature_rows = cursor.fetchall()

            feature_measurements: List[FeatureMeasurement] = []
            for row in feature_rows:
                meas_values = MeasurementValues(**json.loads(row["measurements_json"]))
                props = json.loads(row["properties_json"])
                feature_measurements.append(
                    FeatureMeasurement(
                        feature_id=row["feature_id"],
                        geometry_type=row["geometry_type"],
                        is_measurable=bool(row["is_measurable"]),
                        measurements=meas_values,
                        projected_crs=row["projected_crs"],
                        properties=props,
                        status=row["status"],
                        note=row["note"]
                    )
                )

            return FileMeasurementsResponse(
                file_id=file_row["id"],
                filename=file_row["filename"],
                original_crs=file_row["crs"],
                default_projected_crs=file_row["default_projected_crs"] or file_row["crs"],
                total_features=file_row["feature_count"],
                summary=summary,
                features=feature_measurements
            )

    @staticmethod
    def delete_file(file_id: str) -> bool:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File with ID '{file_id}' not found."
                )
            
            file_path = Path(row["file_path"])
            if file_path.exists():
                try:
                    if file_path.is_file():
                        file_path.unlink()
                except Exception:
                    pass

            cursor.execute("DELETE FROM features WHERE file_id = ?", (file_id,))
            cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
            conn.commit()
            return True
