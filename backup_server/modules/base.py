from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
import structlog
import hashlib

logger = structlog.get_logger()

class BackupModule(ABC):
    """Base class for all backup modules."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logger.bind(module=name)

    @abstractmethod
    def backup(self, dest_path: Path, dry_run: bool = False) -> Path:
        """
        Execute the backup process.
        Returns the path to the created artifact.
        """
        pass

    @abstractmethod
    def restore(self, src_path: Path, dry_run: bool = False) -> bool:
        """
        Execute the restore process.
        """
        pass

    @abstractmethod
    def validate(self, artifact_path: Path) -> bool:
        """
        Validate the integrity of the backup artifact.
        """
        pass

    def cleanup(self, path: Path):
        """Optional cleanup after backup/restore."""
        if path.exists():
            self.logger.info("Cleaning up temporary path", path=str(path))
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)

    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
