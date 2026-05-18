import json
from pathlib import Path
from typing import List, Dict, Any
import datetime
import structlog

logger = structlog.get_logger()

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
            with open(self.catalog_path, "w") as f:
                json.dump(self.entries, f, indent=2)
        except Exception as e:
            logger.error("Failed to save catalog", error=str(e))

    def add_entry(self, entry: Dict[str, Any]):
        self.entries.append(entry)
        self.save()

    def get_backups_for_module(self, module: str) -> List[Dict[str, Any]]:
        return [e for e in self.entries if e["module"] == module]
