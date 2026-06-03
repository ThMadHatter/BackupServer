import pytest
import shutil
from pathlib import Path
from backup_server.engine import ExecutionEngine
from backup_server.loader import ServiceSpec, StepSpec

def test_staging_isolation(tmp_path):
    staging_base = tmp_path / "staging"
    engine1 = ExecutionEngine(staging_base=staging_base)
    engine2 = ExecutionEngine(staging_base=staging_base)

    spec = ServiceSpec(name="test_service", backup=[StepSpec(name="step1", type="template", options={"template": "hello"})])

    ctx1 = engine1.run_service(spec)
    ctx2 = engine2.run_service(spec)

    assert ctx1["run_id"] != ctx2["run_id"]
    assert ctx1["staging_dir"] != ctx2["staging_dir"]

def test_failed_run_preserves_staging(tmp_path):
    staging_base = tmp_path / "staging"
    engine = ExecutionEngine(staging_base=staging_base)

    # Primitive that will fail
    spec = ServiceSpec(name="fail_service", backup=[StepSpec(name="fail", type="http_get", options={"url": "http://nonexistent.void"})])

    with pytest.raises(Exception):
        engine.run_service(spec)

    run_id = engine.context.run_id
    staging_dir = staging_base / run_id
    assert staging_dir.exists()

    # Cleanup for next tests
    shutil.rmtree(staging_dir)
