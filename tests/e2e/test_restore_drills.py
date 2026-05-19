import pytest
import shutil
import hashlib
from pathlib import Path
from backup_server.engine import ExecutionEngine
from backup_server.loader import ServiceSpec, StepSpec
from backup_server.config import InfraSettings

def test_n8n_restore_drill(tmp_path):
    # Setup paths
    base_dir = tmp_path / "backup_system"
    data_dir = tmp_path / "n8n_data"
    restore_dir = tmp_path / "n8n_restore"

    base_dir.mkdir()
    data_dir.mkdir()
    restore_dir.mkdir()

    # Create fake data
    original_file = data_dir / "workflow.json"
    original_content = b'{"name": "test-workflow"}'
    original_file.write_bytes(original_content)

    infra = InfraSettings(BACKUP_BASE_DIR=base_dir, BACKUP_PROFILE="dry_run")
    # We use the new ExecutionEngine
    engine = ExecutionEngine(infra=infra)

    # 1. Backup
    backup_spec = ServiceSpec(
        name="n8n_drill",
        backup=[
            StepSpec(
                name="archive",
                type="tar",
                options={
                    "source_dir": str(data_dir),
                    "dest_file": str(base_dir / "n8n.tar"),
                    "compression": "none"
                },
                store_result="artifact_path"
            ),
            StepSpec(
                name="checksum",
                type="checksum",
                options={"file_path": str(base_dir / "n8n.tar")},
                store_result="artifact_checksum"
            )
        ]
    )

    backup_ctx = engine.run_service(backup_spec, operation="backup")
    artifact_path = base_dir / "n8n.tar"
    artifact_checksum = backup_ctx["artifact_checksum"]

    # 2. Destroy original data
    shutil.rmtree(data_dir)
    data_dir.mkdir()

    # 3. Restore
    restore_spec = ServiceSpec(
        name="n8n_drill",
        backup=[], # required by model
        restore=[
            StepSpec(
                name="extract",
                type="copy",
                options={"source": str(artifact_path), "dest": str(restore_dir / "n8n.tar")}
            )
        ]
    )

    # Post-restore integrity requires 'restore_dest_path' and 'expected_checksum'
    initial_context = {
        "force": True,
        "restore_dest_path": str(restore_dir / "n8n.tar"),
        "expected_checksum": artifact_checksum
    }

    engine.run_service(restore_spec, operation="restore", initial_context=initial_context)

    assert (restore_dir / "n8n.tar").exists()
    restored_hash = hashlib.sha256((restore_dir / "n8n.tar").read_bytes()).hexdigest()
    assert restored_hash == artifact_checksum
