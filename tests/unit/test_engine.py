import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import datetime
from src.core.engine import BackupEngine
from src.core.config import BackupConfig, InfraSettings, ModulePolicy
from src.core.catalog import BackupEntry

@pytest.fixture
def mock_storage():
    return MagicMock()

@pytest.fixture
def infra_settings(tmp_path):
    return InfraSettings(
        PROXMOX_URL="http://test",
        PROXMOX_USER="test",
        backup_base_dir=tmp_path / "backups"
    )

@pytest.fixture
def backup_config():
    return BackupConfig(
        modules={
            "test_module": ModulePolicy(enabled=True, retention_days=1)
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

def test_engine_retention(infra_settings, backup_config, mock_storage):
    with patch("src.core.engine.registry") as mock_registry:
        engine = BackupEngine(infra_settings, backup_config, mock_storage)

        # Add an old entry
        old_date = (datetime.datetime.now() - datetime.timedelta(days=5)).isoformat()
        entry = {
            "module": "test_module",
            "timestamp": "20230101_000000",
            "artifact": "test_module/20230101_000000/art.tar.zst",
            "checksum": "abc",
            "created_at": old_date
        }
        engine.catalog.entries.append(entry)

        engine.enforce_retention()

        mock_storage.delete.assert_called_once_with(entry["artifact"])
        assert len(engine.catalog.entries) == 0

def test_engine_parallel_run(infra_settings, backup_config, mock_storage):
    backup_config.modules["module2"] = ModulePolicy(enabled=True)

    with patch("src.core.engine.registry") as mock_registry:
        mock_module_cls = MagicMock()
        mock_module_instance = MagicMock()
        mock_module_instance.backup.return_value = Path("test.tar.zst")
        mock_module_instance.validate.return_value = True
        mock_module_instance.calculate_checksum.return_value = "hash"
        mock_module_cls.return_value = mock_module_instance
        mock_registry.get_module.return_value = mock_module_cls

        engine = BackupEngine(infra_settings, backup_config, mock_storage)
        report = engine.run_all(parallel=True)

        assert len(report["modules"]) == 2
        assert report["modules"]["test_module"]["status"] == "success"
        assert report["modules"]["module2"]["status"] == "success"
