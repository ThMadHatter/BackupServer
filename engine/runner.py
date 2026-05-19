import uuid
import time
import json
import shutil
import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Type, Optional
import structlog
from jinja2 import Template

from engine.loader import ServiceSpec, StepSpec, HookSpec
from engine.context import ExecutionContext
from engine.dag import ExecutionDAG
from primitives.base import Primitive
from primitives.network import HttpGet, HttpPost, HttpDownload
from primitives.filesystem import Tar, Copy, Compress, Checksum
from primitives.storage import RCloneUpload, RCloneDownload
from primitives.lxc import PctExec
from primitives.utils import JsonQuery, TemplatePrimitive
from src.core.exceptions import RestoreSafetyError, PrimitiveError, BackupEngineError

logger = structlog.get_logger()

PRIMITIVE_MAP: Dict[str, Type[Primitive]] = {
    "http_get": HttpGet,
    "http_post": HttpPost,
    "http_download": HttpDownload,
    "tar": Tar,
    "copy": Copy,
    "compress": Compress,
    "checksum": Checksum,
    "rclone_upload": RCloneUpload,
    "rclone_download": RCloneDownload,
    "pct_exec": PctExec,
    "json_query": JsonQuery,
    "template": TemplatePrimitive,
}

class ExecutionEngine:
    def __init__(self, dry_run: bool = False, staging_base: Optional[Path] = None):
        self.dry_run = dry_run
        self.staging_base = staging_base
        self.context: Optional[ExecutionContext] = None

    def _create_run_id(self) -> str:
        return f"{datetime.now().strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"

    def run_service(self, spec: ServiceSpec, operation: str = "backup", initial_context: Dict[str, Any] = {}, skip_steps: List[str] = []):
        run_id = self._create_run_id()
        timestamp = datetime.now()

        # Use provided staging_base or fallback to /tmp
        actual_staging_base = self.staging_base or Path("/tmp/backup-engine/staging")
        staging_dir = actual_staging_base / run_id

        if not self.dry_run:
            try:
                staging_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error("Failed to create staging directory", path=str(staging_dir), error=str(e))
                raise

        self.context = ExecutionContext(
            run_id=run_id,
            timestamp=timestamp,
            service=spec.name,
            staging_dir=staging_dir,
            variables=initial_context,
            dry_run=self.dry_run
        )

        log = logger.bind(service=spec.name, run_id=run_id, operation=operation, staging_dir=str(staging_dir))
        log.info("Starting service operation")

        try:
            if operation == "restore":
                self._verify_restore_safety(log, spec)

            if operation == "backup":
                self.execute_steps(spec.hooks.pre_backup, log, "pre_backup")
            elif operation == "restore":
                self.execute_steps(spec.hooks.pre_restore, log, "pre_restore")

            steps = getattr(spec, operation)
            if not steps:
                log.warning("No steps defined for operation", operation=operation)
            else:
                dag = ExecutionDAG(steps)
                execution_order = dag.get_execution_order()
                self.execute_steps(execution_order, log, operation, skip_steps=skip_steps)

            if operation == "backup":
                self.execute_steps(spec.hooks.post_backup, log, "post_backup")
                self.generate_artifact_metadata(spec, log)
            elif operation == "restore":
                self.execute_steps(spec.hooks.post_restore, log, "post_restore")

            log.info("Service operation completed successfully")
        except Exception as e:
            log.error("Service operation failed", error=str(e))
            self.execute_steps(spec.hooks.on_failure, log, "on_failure")
            if self.context:
                self.context.execution_metadata["failed"] = True
            raise
        finally:
            self.cleanup_staging(log)

        return self.context.to_dict()

    def _verify_restore_safety(self, log: Any, spec: ServiceSpec):
        if self.dry_run:
            log.info("Dry run: Skipping restore safety verification")
            return

        expected_checksum = self.context.variables.get("expected_checksum")
        artifact_local_path = self.context.variables.get("artifact_local_path")

        if artifact_local_path and expected_checksum:
            log.info("Verifying artifact checksum before restore", path=artifact_local_path)
            sha256 = hashlib.sha256()
            try:
                with open(artifact_local_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256.update(chunk)

                actual_checksum = sha256.hexdigest()
                if actual_checksum != expected_checksum:
                    raise RestoreSafetyError(f"Checksum mismatch! Expected {expected_checksum}, got {actual_checksum}")
                log.info("Checksum verification passed")
            except FileNotFoundError:
                raise RestoreSafetyError(f"Artifact not found at {artifact_local_path}")

        if not self.context.variables.get("force"):
            log.info("Checking for potential overwrite during restore")
            for step in (spec.restore or []):
                if step.type == "copy":
                    dest = step.options.get("dest")
                    if dest:
                        templated_dest = self._template_options(dest, self.context.to_dict())
                        if Path(templated_dest).exists():
                            raise RestoreSafetyError(f"Restore safety: target path '{templated_dest}' exists. Use --force to overwrite.")

    def execute_steps(self, steps: List[StepSpec], log: Any, phase: str, skip_steps: List[str] = []):
        for step in steps:
            if step.name in skip_steps:
                log.info("Skipping step (already completed)", step=step.name, phase=phase)
                continue
            self.execute_step(step, log.bind(phase=phase))

    def cleanup_staging(self, log: Any):
        if self.dry_run or not self.context:
            return

        staging_dir = self.context.staging_dir
        if staging_dir.exists():
            if self.context.execution_metadata.get("failed"):
                log.warning("Preserving staging directory for debugging due to failure", path=str(staging_dir))
                return

            log.info("Cleaning up staging directory", path=str(staging_dir))
            try:
                shutil.rmtree(staging_dir)
            except Exception as e:
                log.error("Failed to cleanup staging directory", path=str(staging_dir), error=str(e))

    def generate_artifact_metadata(self, spec: ServiceSpec, log: Any):
        if not self.context:
            return

        ctx_dict = self.context.to_dict()
        artifact_metadata = {
            "service": spec.name,
            "timestamp": ctx_dict["timestamp"],
            "run_id": self.context.run_id,
            "artifact_path": self.context.variables.get("artifact_path"),
            "checksum": self.context.variables.get("artifact_checksum"),
            "consistency": spec.consistency,
            "schema_version": spec.schema_version,
            "metadata": {
                "compression": self.context.variables.get("compression", "zstd"),
                "source": spec.name
            }
        }

        metadata_path = self.context.staging_dir / "metadata.json"
        if not self.dry_run:
            with open(metadata_path, "w") as f:
                json.dump(artifact_metadata, f, indent=2)

        self.context.execution_metadata["artifact_metadata"] = artifact_metadata
        log.info("Artifact metadata generated", path=str(metadata_path))

    def execute_step(self, step: StepSpec, log: Any):
        log = log.bind(step=step.name, type=step.type)

        if self.dry_run:
            log.info("Dry run: Skipping step execution")
            return

        primitive_class = PRIMITIVE_MAP.get(step.type)
        if not primitive_class:
            raise PrimitiveError(f"Unknown primitive type: {step.type}")

        templated_options = self._template_options(step.options, self.context.to_dict())
        primitive = primitive_class(step.name, templated_options)

        retries = step.retry or 0
        attempt = 0

        while attempt <= retries:
            try:
                log.info("Executing step", attempt=attempt+1)
                result = primitive.execute(self.context.to_dict())

                if step.register:
                    self.context.variables[step.register] = result

                log.info("Step completed successfully")
                return result
            except Exception as e:
                attempt += 1
                log.error("Step failed", error=str(e), attempt=attempt)
                if attempt > retries:
                    if step.ignore_errors:
                        log.warning("Ignoring step failure")
                        return None
                    if isinstance(e, BackupEngineError):
                        raise
                    raise PrimitiveError(f"Step '{step.name}' failed after {attempt} attempts: {str(e)}")
                time.sleep(2 ** attempt)

    def _template_options(self, options: Any, context: Dict[str, Any]) -> Any:
        if isinstance(options, str):
            if "{{" in options:
                return Template(options).render(**context)
            return options
        elif isinstance(options, dict):
            return {k: self._template_options(v, context) for k, v in options.items()}
        elif isinstance(options, list):
            return [self._template_options(i, context) for i in options]
        return options
