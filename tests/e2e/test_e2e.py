import pytest
from pathlib import Path
from backup_server.loader import load_spec
from backup_server.engine import ExecutionEngine

def test_e2e_dry_run():
    spec_path = Path("specs/qdrant.yaml")
    infra = {
        "rclone_remote": "gdrive:backups",
        "backup_base_dir": "/tmp/backups",
    }
    spec = load_spec(spec_path, {"infra": infra, "qdrant_url": "http://localhost:6333", "item": "test", "snapshot_name": "test.snap", "timestamp": "123"})

    engine = ExecutionEngine(dry_run=True)
    context = engine.run_service(spec)

    assert context["service"] == "qdrant"
    assert context["dry_run"] is True
