import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import datetime
import structlog
import sh
from backup_server.exceptions import CatalogError

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
                        schema_version TEXT DEFAULT '1.0',
                        validated INTEGER DEFAULT 0
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

    def mark_validated(self, run_id: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("UPDATE backups SET validated = 1 WHERE run_id = ?", (run_id,))
        except sqlite3.Error as e:
            raise CatalogError(f"Failed to mark backup as validated: {str(e)}")

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

    def prune_backups(self, service: str, retention_days: int, rclone_remote: Optional[str] = None,
                      min_backups: int = 3, protect_latest: bool = True, require_validation: bool = False) -> List[Dict[str, Any]]:

        all_backups = self.get_backups(service)
        if not all_backups:
            return []

        # 1. Protect Latest
        latest = all_backups[0] if all_backups else None

        # 2. Identify candidates for deletion based on age
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=retention_days)).isoformat()

        candidates = [b for b in all_backups if b["created_at"] < cutoff]

        # 3. Apply Safety Barriers
        deleted = []
        remaining_count = len(all_backups)

        for entry in reversed(candidates): # Start from oldest
            if protect_latest and entry["id"] == latest["id"]:
                logger.info("Retention safety: Protecting latest backup", run_id=entry["run_id"])
                continue

            if remaining_count <= min_backups:
                logger.info("Retention safety: Minimum backups reached", count=remaining_count)
                break

            if require_validation and not entry.get("validated"):
                logger.info("Retention safety: Skipping unvalidated backup", run_id=entry["run_id"])
                continue

            if not entry.get("checksum"):
                 logger.warning("Retention safety: Skipping backup with missing checksum", run_id=entry["run_id"])
                 continue

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
            remaining_count -= 1

        return deleted

class BackupEntry(dict):
    def __init__(self, module: str, timestamp: str, artifact: str, checksum: str = ""):
        super().__init__(
            module=module,
            timestamp=timestamp,
            artifact=artifact,
            checksum=checksum,
            created_at=datetime.datetime.now().isoformat()
        )

class BackupCatalog:
    def __init__(self, catalog_path: Path):
        self.catalog_path = catalog_path
        self.entries: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if self.catalog_path.exists():
            try:
                with open(self.catalog_path, "r") as f:
                    self.entries = json.load(f)
            except Exception as e:
                logger.error("Failed to load catalog", error=str(e))
                self.entries = []

    def save(self):
        try:
            self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.catalog_path, "w") as f:
                json.dump(self.entries, f, indent=2)
        except Exception as e:
            logger.error("Failed to save catalog", error=str(e))

    def add_entry(self, entry: Dict[str, Any]):
        self.entries.append(entry)
        self.save()

    def get_backups_for_module(self, module: str) -> List[Dict[str, Any]]:
        return [e for e in self.entries if e["module"] == module]
