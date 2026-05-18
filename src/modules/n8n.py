from pathlib import Path
import sh
from src.modules.base import BackupModule
from src.core.registry import register_module

@register_module("n8n")
class N8nModule(BackupModule):
    def backup(self, dest_path: Path, dry_run: bool = False) -> Path:
        data_dir = self.config.get("data_dir", "/home/node/.n8n")
        
        if dry_run:
            self.logger.info("Dry run: Would backup n8n data", dir=data_dir)
            return dest_path / "n8n_mock.tar.zst"

        artifact_name = "n8n_backup.tar.zst"
        artifact_path = dest_path / artifact_name
        
        self.logger.info("Backing up n8n data", dir=data_dir)
        
        # In a real LXC environment, we might use 'pct exec' to run commands inside the container
        # or mount the volume. For now, we assume local access or ssh.
        try:
            # Using tar + zstd for compression
            sh.tar("-I", "zstd", "-cvf", str(artifact_path), "-C", data_dir, ".")
        except sh.ErrorReturnCode as e:
            self.logger.error("Failed to archive n8n data", error=str(e))
            raise

        return artifact_path

    def restore(self, src_path: Path, dry_run: bool = False) -> bool:
        if dry_run:
            self.logger.info("Dry run: Would restore n8n from", path=str(src_path))
            return True
        return True

    def validate(self, artifact_path: Path) -> bool:
        # Check if it's a valid zstd archive
        try:
            sh.zstd("-t", str(artifact_path))
            return True
        except:
            return False
