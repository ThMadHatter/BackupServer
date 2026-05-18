import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import datetime
import structlog

logger = structlog.get_logger()

class CatalogManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    artifact_path TEXT NOT NULL,
                    checksum TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_service ON backups(service)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_run_id ON backups(run_id)")

    def add_entry(self, service: str, run_id: str, timestamp: str, artifact_path: str, checksum: str, metadata: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO backups (service, run_id, timestamp, artifact_path, checksum, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (service, run_id, timestamp, artifact_path, checksum, json.dumps(metadata)))

    def get_backups(self, service: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM backups"
        params = []
        if service:
            query += " WHERE service = ?"
            params.append(service)
        query += " ORDER BY created_at DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_backup(self, service: str) -> Optional[Dict[str, Any]]:
        backups = self.get_backups(service)
        return backups[0] if backups else None

    def delete_entry(self, backup_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM backups WHERE id = ?", (backup_id,))
