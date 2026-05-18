import sh
from pathlib import Path
from typing import Any, Dict
from primitives.base import Primitive, PrimitiveContract

class RCloneUpload(Primitive):
    contract = PrimitiveContract(
        inputs=["local_path", "remote_path", "remote_name", "config_path", "atomic"],
        outputs=["remote_path"],
        side_effects=["uploads_to_remote"],
        failure_modes=["authentication_error", "network_error", "remote_full"],
        retryable=True,
        idempotent=True
    )

    def execute(self, context: Dict[str, Any]) -> Any:
        local_path = self.options.get("local_path")
        remote_path = self.options.get("remote_path")
        remote_name = self.options.get("remote_name")
        config_path = self.options.get("config_path")
        atomic = self.options.get("atomic", True)

        rclone = sh.rclone.bake(config=str(config_path)) if config_path else sh.rclone

        if atomic:
            temp_remote_path = f"{remote_path}.tmp"
            self.logger.info("Executing Atomic RClone Upload", local=local_path, remote=f"{remote_name}:{temp_remote_path}")
            rclone.copyto(str(local_path), f"{remote_name}:{temp_remote_path}")

            # In a real scenario, we might want to verify integrity here if rclone doesn't already

            self.logger.info("Promoting artifact", temp=temp_remote_path, final=remote_path)
            rclone.moveto(f"{remote_name}:{temp_remote_path}", f"{remote_name}:{remote_path}")
        else:
            self.logger.info("Executing RClone Upload", local=local_path, remote=f"{remote_name}:{remote_path}")
            rclone.copyto(str(local_path), f"{remote_name}:{remote_path}")

        return remote_path

class RCloneDownload(Primitive):
    contract = PrimitiveContract(
        inputs=["remote_path", "local_path", "remote_name", "config_path"],
        outputs=["local_path"],
        side_effects=["downloads_from_remote"],
        failure_modes=["authentication_error", "network_error", "file_not_found"],
        retryable=True,
        idempotent=True
    )

    def execute(self, context: Dict[str, Any]) -> Any:
        remote_path = self.options.get("remote_path")
        local_path = self.options.get("local_path")
        remote_name = self.options.get("remote_name")
        config_path = self.options.get("config_path")

        rclone = sh.rclone.bake(config=str(config_path)) if config_path else sh.rclone

        self.logger.info("Executing RClone Download", remote=f"{remote_name}:{remote_path}", local=local_path)
        rclone.copyto(f"{remote_name}:{remote_path}", str(local_path))
        return local_path
