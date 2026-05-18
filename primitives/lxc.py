import sh
from typing import Any, Dict
from primitives.base import Primitive, PrimitiveContract

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
