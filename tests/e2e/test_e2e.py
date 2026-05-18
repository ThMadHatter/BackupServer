import pytest
from pathlib import Path
from engine.loader import load_spec
from engine.runner import ExecutionEngine

def test_e2e_dry_run():
    spec_path = Path("specs/qdrant.yaml")
    spec = load_spec(spec_path, {"qdrant_url": "http://localhost:6333", "item": "test", "snapshot_name": "test.snap", "timestamp": "123"})

    engine = ExecutionEngine(dry_run=True)
    context = engine.run_service(spec)

    assert context["service"] == "qdrant"
    assert context["dry_run"] is True
