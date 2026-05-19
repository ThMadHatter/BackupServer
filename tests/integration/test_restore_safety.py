import pytest
import shutil
from pathlib import Path
from engine.runner import ExecutionEngine
from engine.loader import ServiceSpec, StepSpec
from src.core.exceptions import RestoreSafetyError

def test_restore_overwrite_protection(tmp_path):
    target = tmp_path / "target_file"
    target.write_text("existing")

    engine = ExecutionEngine(staging_base=tmp_path / "staging")
    # Step that would overwrite 'target'
    spec = ServiceSpec(
        name="test",
        backup=[],
        restore=[StepSpec(name="restore_file", type="copy", options={"source": "/tmp/src", "dest": str(target)})]
    )

    # Without force, it should raise
    with pytest.raises(RestoreSafetyError, match="Restore safety: target path .* exists"):
        engine.run_service(spec, operation="restore")

def test_restore_force_overwrite(tmp_path):
    target = tmp_path / "target_file"
    target.write_text("existing")

    # Create source file for the copy primitive to succeed (or at least not fail due to overwrite check)
    src = tmp_path / "src_file"
    src.write_text("new")

    engine = ExecutionEngine(staging_base=tmp_path / "staging")
    spec = ServiceSpec(
        name="test",
        backup=[],
        restore=[StepSpec(name="restore_file", type="copy", options={"source": str(src), "dest": str(target)})]
    )

    # With force, it should NOT raise the overwrite error
    engine.run_service(spec, operation="restore", initial_context={"force": True})
    assert target.read_text() == "new"
