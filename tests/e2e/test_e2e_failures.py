import pytest
from pathlib import Path
from backup_server.engine import BackupEngine
from backup_server.config import BackupConfig, InfraSettings, ModulePolicy

def test_failure_module_exception(tmp_path):
    infra = InfraSettings(
        PROXMOX_URL="http://test",
        PROXMOX_USER="test",
        backup_base_dir=tmp_path / "backups"
    )
    config = BackupConfig(
        modules={
            "broken": ModulePolicy(enabled=True)
        }
    )

    class MockStorage:
        def upload(self, l, r): pass
        def delete(self, r): pass

    engine = BackupEngine(infra, config, MockStorage())

    # We expect it to catch exception from registry if module not found
    report = engine.run_all()

    assert report["modules"]["broken"]["status"] == "failed"
    assert "not found in registry" in report["modules"]["broken"]["reason"]

def test_failure_validation(tmp_path):
    from backup_server.registry import registry, register_module
    from backup_server.modules.base import BackupModule
    from unittest.mock import MagicMock

    @register_module("invalid")
    class InvalidModule(BackupModule):
        def backup(self, dest, dry_run=False):
            p = dest / "test.txt"
            p.touch()
            return p
        def restore(self, s, dry_run=False): return True
        def validate(self, p): return False

    infra = InfraSettings(
        PROXMOX_URL="http://test",
        PROXMOX_USER="test",
        backup_base_dir=tmp_path / "backups"
    )
    config = BackupConfig(modules={"invalid": ModulePolicy(enabled=True)})

    engine = BackupEngine(infra, config, MagicMock())
    report = engine.run_all()

    assert report["modules"]["invalid"]["status"] == "failed"
    assert report["modules"]["invalid"]["reason"] == "validation_failure"
