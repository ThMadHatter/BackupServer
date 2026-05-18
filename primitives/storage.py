import sh
from pathlib import Path
from typing import Any, Dict
from primitives.base import Primitive

class RCloneUpload(Primitive):
    def execute(self, context: Dict[str, Any]) -> Any:
        local_path = self.options.get("local_path")
        remote_path = self.options.get("remote_path")
        remote_name = self.options.get("remote_name")
        config_path = self.options.get("config_path")

        rclone = sh.rclone.bake(config=str(config_path)) if config_path else sh.rclone

        self.logger.info("Executing RClone Upload", local=local_path, remote=f"{remote_name}:{remote_path}")
        rclone.copyto(str(local_path), f"{remote_name}:{remote_path}")
        return remote_path

class RCloneDownload(Primitive):
    def execute(self, context: Dict[str, Any]) -> Any:
        remote_path = self.options.get("remote_path")
        local_path = self.options.get("local_path")
        remote_name = self.options.get("remote_name")
        config_path = self.options.get("config_path")

        rclone = sh.rclone.bake(config=str(config_path)) if config_path else sh.rclone

        self.logger.info("Executing RClone Download", remote=f"{remote_name}:{remote_path}", local=local_path)
        rclone.copyto(f"{remote_name}:{remote_path}", str(local_path))
        return local_path
