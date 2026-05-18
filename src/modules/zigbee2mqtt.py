from pathlib import Path
import sh
from src.modules.base import BackupModule
from src.core.registry import register_module

@register_module("zigbee2mqtt")
class Zigbee2MQTTModule(BackupModule):
    def backup(self, dest_path: Path, dry_run: bool = False) -> Path:
        data_dir = self.config.get("data_dir", "/app/data")
        lxc_id = self.config.get("lxc_id")

        artifact_path = dest_path / "z2m_backup.tar.zst"

        if dry_run:
            self.logger.info("Dry run: Would backup Zigbee2MQTT", dir=data_dir)
            artifact_path.touch()
            return artifact_path

        try:
            if lxc_id:
                sh.pct.exec(lxc_id, "--", "tar", "-I", "zstd", "-cf", "-", "-C", data_dir, ".", _out=str(artifact_path))
            else:
                sh.tar("-I", "zstd", "-cf", str(artifact_path), "-C", data_dir, ".")
            return artifact_path
        except Exception as e:
            self.logger.error("Zigbee2MQTT backup failed", error=str(e))
            raise

    def restore(self, src_path: Path, dry_run: bool = False) -> bool:
        return True

    def validate(self, artifact_path: Path) -> bool:
        try:
            sh.zstd("-t", str(artifact_path))
            return True
        except:
            return False
