from pathlib import Path
import sh
import structlog
from typing import Optional

logger = structlog.get_logger()

class StorageProvider:
    def upload(self, local_path: Path, remote_path: str):
        pass

    def download(self, remote_path: str, local_path: Path):
        pass

    def delete(self, remote_path: str):
        pass

    def list(self, remote_path: str):
        pass

class RCloneStorage(StorageProvider):
    def __init__(self, remote: str, config_path: Optional[Path] = None):
        self.remote = remote
        self.config_path = config_path
        self.rclone = sh.rclone.bake(config=str(config_path)) if config_path else sh.rclone

    def upload(self, local_path: Path, remote_path: str):
        logger.info("Uploading via rclone", local=str(local_path), remote=f"{self.remote}/{remote_path}")
        try:
            self.rclone.copy(str(local_path), f"{self.remote}/{remote_path}")
        except sh.ErrorReturnCode as e:
            logger.error("Rclone upload failed", error=str(e))
            raise

    def delete(self, remote_path: str):
        logger.info("Deleting remote path", path=f"{self.remote}/{remote_path}")
        self.rclone.delete(f"{self.remote}/{remote_path}")

    def list(self, remote_path: str):
        return self.rclone.lsjson(f"{self.remote}/{remote_path}")
