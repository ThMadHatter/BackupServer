import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from backup_server.old_engine import BackupEngine
from backup_server.config import BackupConfig, InfraSettings, ModulePolicy
from backup_server.storage import StorageProvider

class MockStorage(StorageProvider):
    def __init__(self):
        self.uploaded = []
    def upload(self, local, remote):
        self.uploaded.append(remote)
    def delete(self, remote):
        pass

def test_full_backup_run(tmp_path):
    # Ensure isolation by using tmp_path for EVERYTHING
    backup_base = tmp_path / "local_backups"
    backup_base.mkdir()

    infra = InfraSettings(
        PROXMOX_URL="http://test",
        PROXMOX_USER="test",
        BACKUP_BASE_DIR=backup_base
    )
    config = BackupConfig(
        modules={
            "n8n": ModulePolicy(enabled=True, options={"data_dir": str(tmp_path / "n8n")})
        }
    )
    # Setup mock data
    (tmp_path / "n8n").mkdir()
    (tmp_path / "n8n" / "test.txt").touch()

    storage = MockStorage()
    # Explicitly pass a new catalog for this test to avoid sharing state
    from backup_server.catalog.manager import BackupCatalog
    catalog = BackupCatalog(backup_base / "catalog.json")

    engine = BackupEngine(infra, config, storage, catalog=catalog)

    with patch("sh.tar", create=True), patch("sh.zstd", create=True):
        with patch("backup_server.modules.n8n.N8nModule.backup") as mock_backup:
            artifact_path = backup_base / "n8n/20260518_103030/n8n_backup.tar.zst"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.touch()
            mock_backup.return_value = artifact_path

            report = engine.run_all()

    assert report["modules"]["n8n"]["status"] == "success"
    assert len(storage.uploaded) == 1
    assert "n8n/" in storage.uploaded[0]

    # Check catalog
    assert len(engine.catalog.entries) == 1
    assert engine.catalog.entries[0]["module"] == "n8n"
