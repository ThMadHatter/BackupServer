import pytest
import hashlib
from pathlib import Path
from engine.runner import ExecutionEngine
from engine.loader import ServiceSpec, StepSpec

def test_restore_checksum_verification(tmp_path):
    artifact = tmp_path / "backup.tar.zst"
    artifact.write_text("corrupted content")
    expected_checksum = "correct_checksum" # obviously wrong

    engine = ExecutionEngine(staging_base=tmp_path / "staging")
    spec = ServiceSpec(name="test", backup=[])

    initial_context = {
        "artifact_local_path": str(artifact),
        "expected_checksum": expected_checksum
    }

    with pytest.raises(ValueError, match="Checksum mismatch"):
        engine.run_service(spec, operation="restore", initial_context=initial_context)

def test_restore_checksum_success(tmp_path):
    content = b"valid content"
    artifact = tmp_path / "backup.tar.zst"
    artifact.write_bytes(content)
    expected_checksum = hashlib.sha256(content).hexdigest()

    engine = ExecutionEngine(staging_base=tmp_path / "staging")
    # Define a simple restore step that does nothing but exists
    spec = ServiceSpec(name="test", backup=[], restore=[StepSpec(name="dummy", type="template", options={"template": "ok"})])

    initial_context = {
        "artifact_local_path": str(artifact),
        "expected_checksum": expected_checksum
    }

    # Should not raise
    engine.run_service(spec, operation="restore", initial_context=initial_context)
