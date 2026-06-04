import sh
from typing import Any, Dict
from backup_server.primitives.base import Primitive, PrimitiveContract

class PctExec(Primitive):
    contract = PrimitiveContract(
        inputs=["vmid", "command", "user"],
        outputs=["stdout"],
        side_effects=["mutation_in_lxc_container"],
        failure_modes=["container_not_running", "command_failed"],
        retryable=False,
        idempotent=False
    )

    def execute(self, context: Dict[str, Any]) -> Any:
        vmid = self.options.get("vmid")
        command = self.options.get("command")
        user = self.options.get("user")

        self.logger.info("Executing Pct Exec", vmid=vmid, command=command, user=user)

        args = [str(vmid)]
        if user:
            args.extend(["--user", user])
        args.append("--")
        if isinstance(command, list):
            args.extend(command)
        else:
            args.append(command)

        result = sh.pct.exec(*args)
        return result.stdout.decode()

class PctPull(Primitive):
    contract = PrimitiveContract(
        inputs=["vmid", "source", "dest"],
        outputs=["dest"],
        side_effects=["file_copied_from_lxc"],
        failure_modes=["container_not_running", "source_not_found"],
        retryable=True,
        idempotent=True
    )

    def execute(self, context: Dict[str, Any]) -> Any:
        vmid = self.options.get("vmid")
        source = self.options.get("source")
        dest = self.options.get("dest")

        self.logger.info("Executing Pct Pull", vmid=vmid, source=source, dest=dest)
        sh.pct.pull(str(vmid), source, dest)
        return dest

class PctPush(Primitive):
    contract = PrimitiveContract(
        inputs=["vmid", "source", "dest"],
        outputs=["dest"],
        side_effects=["file_copied_to_lxc"],
        failure_modes=["container_not_running", "dest_not_writable"],
        retryable=True,
        idempotent=True
    )

    def execute(self, context: Dict[str, Any]) -> Any:
        vmid = self.options.get("vmid")
        source = self.options.get("source")
        dest = self.options.get("dest")

        self.logger.info("Executing Pct Push", vmid=vmid, source=source, dest=dest)
        sh.pct.push(str(vmid), source, dest)
        return dest
