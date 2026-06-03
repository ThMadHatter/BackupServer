from pathlib import Path
import sh
from backup_server.modules.base import BackupModule
from backup_server.registry import register_module

@register_module("mqtt")
class MQTTModule(BackupModule):
    def backup(self, dest_path: Path, dry_run: bool = False) -> Path:
        data_dir = self.config.get("data_dir", "/var/lib/mosquitto")
        lxc_id = self.config.get("lxc_id")

        artifact_path = dest_path / "mqtt_backup.tar.zst"

        if dry_run:
            self.logger.info("Dry run: Would backup MQTT", dir=data_dir)
            artifact_path.touch()
            return artifact_path

        try:
            if lxc_id:
                sh.pct.exec(lxc_id, "--", "tar", "-I", "zstd", "-cf", "-", "-C", data_dir, ".", _out=str(artifact_path))
            else:
                sh.tar("-I", "zstd", "-cf", str(artifact_path), "-C", data_dir, ".")
            return artifact_path
        except Exception as e:
            self.logger.error("MQTT backup failed", error=str(e))
            raise

    def restore(self, src_path: Path, dry_run: bool = False) -> bool:
        return True

    def validate(self, artifact_path: Path) -> bool:
        try:
            sh.zstd("-t", str(artifact_path))
            return True
        except:
            return False
