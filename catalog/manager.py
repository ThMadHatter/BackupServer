import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import datetime
import structlog
import sh
from src.core.exceptions import CatalogError

logger = structlog.get_logger()

class CatalogManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_parent_exists()
        self._init_db()

    def _ensure_parent_exists(self):
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise CatalogError(f"Permission denied: Cannot create directory {self.db_path.parent}")
        except Exception as e:
            raise CatalogError(f"Failed to create catalog directory {self.db_path.parent}: {str(e)}")

    def _init_db(self):
        try:
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
        except sqlite3.OperationalError as e:
            if "unable to open database file" in str(e):
                raise CatalogError(f"Unable to open database file at {self.db_path}. Ensure path is valid and writable.")
            raise CatalogError(f"Database initialization failed: {str(e)}")

    def add_entry(self, service: str, run_id: str, timestamp: str, artifact_path: str, checksum: str, metadata: Dict[str, Any], schema_version: str = "1.0"):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO backups (service, run_id, timestamp, artifact_path, checksum, metadata, schema_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (service, run_id, timestamp, artifact_path, checksum, json.dumps(metadata), schema_version))
        except sqlite3.Error as e:
            raise CatalogError(f"Failed to add entry to catalog: {str(e)}")

    def get_backups(self, service: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM backups"
        params = []
        if service:
            query += " WHERE service = ?"
            params.append(service)
        query += " ORDER BY created_at DESC"

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise CatalogError(f"Failed to retrieve backups from catalog: {str(e)}")

    def get_latest_backup(self, service: str) -> Optional[Dict[str, Any]]:
        backups = self.get_backups(service)
        return backups[0] if backups else None

    def delete_entry(self, backup_id: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM backups WHERE id = ?", (backup_id,))
        except sqlite3.Error as e:
            raise CatalogError(f"Failed to delete entry from catalog: {str(e)}")

    def prune_backups(self, service: str, retention_days: int, rclone_remote: Optional[str] = None) -> List[Dict[str, Any]]:
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=retention_days)).isoformat()

        to_delete = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM backups WHERE service = ? AND created_at < ?", (service, cutoff))
                to_delete = [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise CatalogError(f"Failed to identify backups for pruning: {str(e)}")

        deleted = []
        for entry in to_delete:
            if rclone_remote and entry["artifact_path"] != "unknown":
                try:
                    full_remote_path = f"{rclone_remote}:{entry['artifact_path']}"
                    logger.info("Purging remote artifact", path=full_remote_path)
                    sh.rclone.purge(full_remote_path)
                except Exception as e:
                    try:
                        sh.rclone.delete(full_remote_path)
                    except Exception as e2:
                        logger.error("Failed to delete remote artifact", error=str(e2), path=entry["artifact_path"])
                        continue

            self.delete_entry(entry["id"])
            deleted.append(entry)

        return deleted
