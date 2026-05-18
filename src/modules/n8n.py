from pathlib import Path
import sh
from src.modules.base import BackupModule
from src.core.registry import register_module

@register_module("n8n")
class N8nModule(BackupModule):
    def backup(self, dest_path: Path, dry_run: bool = False) -> Path:
        data_dir = self.config.get("data_dir", "/home/node/.n8n")
        lxc_id = self.config.get("lxc_id")  # If running on Proxmox host, we might use pct exec
        
        artifact_name = "n8n_backup.tar.zst"
        artifact_path = dest_path / artifact_name

        if dry_run:
            self.logger.info("Dry run: Would backup n8n data", dir=data_dir, lxc_id=lxc_id)
            artifact_path.touch()
            return artifact_path
        
        self.logger.info("Backing up n8n data", dir=data_dir, lxc_id=lxc_id)
        
        try:
            if lxc_id:
                # Execution inside LXC via pct
                # pct exec <id> -- tar -I zstd -cvf - -C <dir> . > local_path
                sh.pct.exec(lxc_id, "--", "tar", "-I", "zstd", "-cf", "-", "-C", data_dir, ".", _out=str(artifact_path))
            else:
                # Local execution
                sh.tar("-I", "zstd", "-cf", str(artifact_path), "-C", data_dir, ".")
        except sh.ErrorReturnCode as e:
            self.logger.error("Failed to archive n8n data", error=str(e))
            raise

        return artifact_path

    def restore(self, src_path: Path, dry_run: bool = False) -> bool:
        data_dir = self.config.get("data_dir", "/home/node/.n8n")
        lxc_id = self.config.get("lxc_id")

        if dry_run:
            self.logger.info("Dry run: Would restore n8n from", path=str(src_path), dest=data_dir)
            return True

        try:
            if lxc_id:
                # pct exec <id> -- tar -I zstd -xf - -C <dir> < local_path
                sh.pct.exec(lxc_id, "--", "tar", "-I", "zstd", "-xf", "-", "-C", data_dir, _in=open(src_path, "rb"))
            else:
                sh.tar("-I", "zstd", "-xf", str(src_path), "-C", data_dir)
            return True
        except Exception as e:
            self.logger.error("Restore failed", error=str(e))
            return False

    def validate(self, artifact_path: Path) -> bool:
        try:
            sh.zstd("-t", str(artifact_path))
            return True
        except:
            return False
