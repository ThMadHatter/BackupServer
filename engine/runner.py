import uuid
import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Type
import structlog
from jinja2 import Template
from engine.loader import ServiceSpec, StepSpec
from primitives.base import Primitive
from primitives.network import HttpGet, HttpPost, HttpDownload
from primitives.filesystem import Tar, Copy, Compress, Checksum
from primitives.storage import RCloneUpload, RCloneDownload
from primitives.lxc import PctExec
from primitives.utils import JsonQuery, TemplatePrimitive

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
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.context: Dict[str, Any] = {}

    def run_service(self, spec: ServiceSpec, operation: str = "backup", initial_context: Dict[str, Any] = {}):
        run_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        log = logger.bind(service=spec.name, run_id=run_id, operation=operation)
        log.info("Starting service operation")

        self.context = {
            "service": spec.name,
            "run_id": run_id,
            "timestamp": timestamp,
            "dry_run": self.dry_run,
            **initial_context
        }

        steps = getattr(spec, operation)
        if not steps:
            log.warning("No steps defined for operation", operation=operation)
            return

        for step in steps:
            self.execute_step(step, log)

        log.info("Service operation completed")

        if operation == "backup":
            self.generate_artifact_metadata(spec, log)

        return self.context

    def generate_artifact_metadata(self, spec: ServiceSpec, log: Any):
        artifact_metadata = {
            "service": spec.name,
            "timestamp": self.context["timestamp"],
            "run_id": self.context["run_id"],
            "artifact_path": self.context.get("artifact_path"),
            "checksum": self.context.get("artifact_checksum"),
            "metadata": {
                "compression": self.context.get("compression", "zstd"),
                "source": spec.name
            }
        }

        # Save to a local file as well
        metadata_path = Path(f"/tmp/{spec.name}_{self.context['run_id']}_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(artifact_metadata, f, indent=2)

        self.context["artifact_metadata"] = artifact_metadata
        self.context["metadata_file"] = str(metadata_path)
        log.info("Artifact metadata generated", path=str(metadata_path))

    def execute_step(self, step: StepSpec, log: Any):
        log = log.bind(step=step.name, type=step.type)

        if self.dry_run:
            log.info("Dry run: Skipping step execution")
            return

        primitive_class = PRIMITIVE_MAP.get(step.type)
        if not primitive_class:
            raise ValueError(f"Unknown primitive type: {step.type}")

        # Template the options using the current context
        templated_options = self._template_options(step.options, self.context)

        primitive = primitive_class(step.name, templated_options)

        retries = step.retry or 0
        attempt = 0

        while attempt <= retries:
            try:
                log.info("Executing step", attempt=attempt+1)
                result = primitive.execute(self.context)

                if step.register:
                    self.context[step.register] = result

                log.info("Step completed successfully")
                return result
            except Exception as e:
                attempt += 1
                log.error("Step failed", error=str(e), attempt=attempt)
                if attempt > retries:
                    if step.ignore_errors:
                        log.warning("Ignoring step failure")
                        return None
                    raise
                time.sleep(2 ** attempt) # Exponential backoff

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
