from pathlib import Path
import sh
from backup_server.modules.base import BackupModule
from backup_server.registry import register_module

@register_module("cloudflared")
class CloudflaredModule(BackupModule):
    def backup(self, dest_path: Path, dry_run: bool = False) -> Path:
        config_dir = self.config.get("config_dir", "/etc/cloudflared")
        lxc_id = self.config.get("lxc_id")

        artifact_path = dest_path / "cloudflared_backup.tar.zst"

        if dry_run:
            self.logger.info("Dry run: Would backup Cloudflared", dir=config_dir)
            artifact_path.touch()
            return artifact_path

        try:
            if lxc_id:
                sh.pct.exec(lxc_id, "--", "tar", "-I", "zstd", "-cf", "-", "-C", config_dir, ".", _out=str(artifact_path))
            else:
                sh.tar("-I", "zstd", "-cf", str(artifact_path), "-C", config_dir, ".")
            return artifact_path
        except Exception as e:
            self.logger.error("Cloudflared backup failed", error=str(e))
            raise

    def restore(self, src_path: Path, dry_run: bool = False) -> bool:
        return True

    def validate(self, artifact_path: Path) -> bool:
        try:
            sh.zstd("-t", str(artifact_path))
            return True
        except:
            return False
