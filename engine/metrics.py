from pathlib import Path
from typing import Dict, Any

class MetricsExporter:
    def __init__(self, export_path: Path):
        self.export_path = export_path

    def export_run_metrics(self, context: Dict[str, Any], duration: float):
        service = context.get("service")
        run_id = context.get("run_id")
        status = "success" if not context.get("execution_metadata", {}).get("failed") else "failure"
        artifact_size = context.get("execution_metadata", {}).get("artifact_metadata", {}).get("size", 0)

        # Prometheus expects Unix timestamps for gauge values that represent time
        # context["timestamp"] is a datetime object in the ExecutionContext,
        # but to_dict() converted it to a string.
        # Let's ensure we use a float unix timestamp if possible.
        # Actually, let's just use the current time for 'last run' if we don't have the exact start time as float.
        import time
        unix_ts = time.time()

        metrics = [
            f'backup_duration_seconds{{service="{service}",run_id="{run_id}"}} {duration}',
            f'backup_status{{service="{service}",run_id="{run_id}"}} {1 if status == "success" else 0}',
            f'backup_artifact_bytes{{service="{service}",run_id="{run_id}"}} {artifact_size}',
            f'backup_last_run_timestamp_seconds{{service="{service}"}} {unix_ts}',
        ]

        service_metrics_path = self.export_path / f"{service}.prom"
        service_metrics_path.parent.mkdir(parents=True, exist_ok=True)

        with open(service_metrics_path, "w") as f:
            f.write("\n".join(metrics) + "\n")
