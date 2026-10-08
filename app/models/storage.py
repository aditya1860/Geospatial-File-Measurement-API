import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.config import settings
from app.schemas.file import FileInfoResponse, FileStatus
from app.schemas.measurement import FeatureMeasurement, MeasurementSummary, FileMeasurementsResponse, MeasurementValues

class DatabaseManager:
    def __init__(self, db_path: str = str(settings.DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size_bytes INTEGER,
                    feature_count INTEGER DEFAULT 0,
                    crs TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    default_projected_crs TEXT,
                    summary_json TEXT,
                    uploaded_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL,
                    feature_id TEXT NOT NULL,
                    geometry_type TEXT NOT NULL,
                    geometry_json TEXT NOT NULL,
                    properties_json TEXT NOT NULL,
                    is_measurable BOOLEAN NOT NULL,
                    measurements_json TEXT NOT NULL,
                    projected_crs TEXT,
                    status TEXT NOT NULL,
                    note TEXT,
                    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_features_file_id ON features(file_id)")
            conn.commit()

db_manager = DatabaseManager()
