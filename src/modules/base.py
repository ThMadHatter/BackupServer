from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
import structlog

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
            # Implementation for cleanup if needed
