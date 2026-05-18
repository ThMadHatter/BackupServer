import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import datetime
import structlog
import sh

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
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    schema_version TEXT DEFAULT '1.0'
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_service ON backups(service)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_run_id ON backups(run_id)")

    def add_entry(self, service: str, run_id: str, timestamp: str, artifact_path: str, checksum: str, metadata: Dict[str, Any], schema_version: str = "1.0"):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO backups (service, run_id, timestamp, artifact_path, checksum, metadata, schema_version)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (service, run_id, timestamp, artifact_path, checksum, json.dumps(metadata), schema_version))

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

    def prune_backups(self, service: str, retention_days: int, rclone_remote: Optional[str] = None) -> List[Dict[str, Any]]:
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=retention_days)).isoformat()

        to_delete = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM backups WHERE service = ? AND created_at < ?", (service, cutoff))
            to_delete = [dict(row) for row in cursor.fetchall()]

        deleted = []
        for entry in to_delete:
            if rclone_remote and entry["artifact_path"] != "unknown":
                try:
                    full_remote_path = f"{rclone_remote}:{entry['artifact_path']}"
                    logger.info("Purging remote artifact", path=full_remote_path)
                    # Use purge for robustness (handles files and directories)
                    sh.rclone.purge(full_remote_path)
                except Exception as e:
                    # If purge fails, try delete as fallback (purge might fail if it's just a single file in some rclone versions/remotes, although move/copy should be fine)
                    try:
                        sh.rclone.delete(full_remote_path)
                    except Exception as e2:
                        logger.error("Failed to delete remote artifact", error=str(e2), path=entry["artifact_path"])
                        continue

            self.delete_entry(entry["id"])
            deleted.append(entry)

        return deleted
