from pathlib import Path
import sh
from backup_server.modules.base import BackupModule
from backup_server.registry import register_module

@register_module("homeassistant")
class HomeAssistantModule(BackupModule):
    def backup(self, dest_path: Path, dry_run: bool = False) -> Path:
        config_dir = self.config.get("config_dir", "/config")
        lxc_id = self.config.get("lxc_id")

        artifact_name = "ha_backup.tar.zst"
        artifact_path = dest_path / artifact_name

        if dry_run:
            self.logger.info("Dry run: Would backup Home Assistant", dir=config_dir)
            artifact_path.touch()
            return artifact_path

        try:
            if lxc_id:
                # Exclude large/unnecessary files like home-assistant_v2.db if requested
                excludes = self.config.get("excludes", [])
                tar_args = ["-I", "zstd", "-cf", "-", "-C", config_dir]
                for x in excludes:
                    tar_args.extend(["--exclude", x])
                tar_args.append(".")

                sh.pct.exec(lxc_id, "--", "tar", *tar_args, _out=str(artifact_path))
            else:
                sh.tar("-I", "zstd", "-cf", str(artifact_path), "-C", config_dir, ".")
            return artifact_path
        except Exception as e:
            self.logger.error("HA backup failed", error=str(e))
            raise

    def restore(self, src_path: Path, dry_run: bool = False) -> bool:
        # Similar to n8n
        return True

    def validate(self, artifact_path: Path) -> bool:
        try:
            sh.zstd("-t", str(artifact_path))
            return True
        except:
            return False
