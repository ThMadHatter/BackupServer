import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.core.engine import BackupEngine
from src.core.config import BackupConfig, InfraSettings, ModulePolicy
from src.core.storage import StorageProvider

class MockStorage(StorageProvider):
    def __init__(self):
        self.uploaded = []
    def upload(self, local, remote):
        self.uploaded.append(remote)
    def delete(self, remote):
        pass

def test_full_backup_run(tmp_path):
    infra = InfraSettings(
        PROXMOX_URL="http://test",
        PROXMOX_USER="test",
        backup_base_dir=tmp_path / "local_backups"
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
    engine = BackupEngine(infra, config, storage)

    with patch("sh.tar", create=True), patch("sh.zstd", create=True):
        # We need to make sure the artifact file is "created" by the mock or the engine will fail later
        # Actually n8n.backup returns artifact_path.
        # Let's mock n8n.backup to actually create the file since sh.tar is mocked.
        with patch("src.modules.n8n.N8nModule.backup") as mock_backup:
            artifact_path = tmp_path / "local_backups/n8n/20260518_103030/n8n_backup.tar.zst"
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
