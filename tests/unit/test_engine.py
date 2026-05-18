import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.core.engine import BackupEngine
from src.core.config import BackupConfig, InfraSettings, ModulePolicy

@pytest.fixture
def mock_storage():
    return MagicMock()

@pytest.fixture
def infra_settings():
    return InfraSettings(
        PROXMOX_URL="http://test",
        PROXMOX_USER="test",
        backup_base_dir=Path("/tmp/test_backups")
    )

@pytest.fixture
def backup_config():
    return BackupConfig(
        modules={
            "test_module": ModulePolicy(enabled=True)
        }
    )

def test_engine_run_all_dry_run(infra_settings, backup_config, mock_storage):
    with patch("src.core.engine.registry") as mock_registry:
        mock_module_cls = MagicMock()
        mock_module_instance = MagicMock()
        mock_module_cls.return_value = mock_module_instance
        mock_registry.get_module.return_value = mock_module_cls
        
        engine = BackupEngine(infra_settings, backup_config, mock_storage)
        report = engine.run_all(dry_run=True)
        
        assert "test_module" in report["modules"]
        assert report["modules"]["test_module"]["status"] == "dry_run"
        mock_module_instance.backup.assert_called_once()
        mock_storage.upload.assert_not_called()
