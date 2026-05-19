import pytest
import os
from pathlib import Path
from src.core.config import load_all_configs, InfraSettings, SecretSettings, ConfigError

def test_config_defaults(tmp_path):
    # No config files, should use defaults
    infra, secrets, backup = load_all_configs(None)
    assert infra.backup_base_dir == Path("/var/lib/backup-engine")
    assert infra.safe_mode is True

def test_config_env_override(monkeypatch):
    monkeypatch.setenv("PROXMOX_URL", "http://env-url")
    infra, secrets, backup = load_all_configs(None)
    assert infra.proxmox_url == "http://env-url"

def test_config_validation_for_run():
    infra = InfraSettings(PROXMOX_URL=None, PROXMOX_USER="user")
    with pytest.raises(ConfigError, match="PROXMOX_URL is required"):
        infra.validate_for_run()

def test_config_layered_loading(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    infra_env = config_dir / "infra.env"
    infra_env.write_text("PROXMOX_URL=http://file-url\nPROXMOX_USER=file-user")

    infra, secrets, backup = load_all_configs(config_dir)
    assert infra.proxmox_url == "http://file-url"
    assert infra.proxmox_user == "file-user"

def test_derived_paths():
    infra = InfraSettings(backup_base_dir=Path("/tmp/test-backup"))
    assert infra.catalog_path == Path("/tmp/test-backup/catalog.sqlite")
    assert infra.staging_dir == Path("/tmp/test-backup/staging")
    assert infra.metrics_dir == Path("/tmp/test-backup/metrics")
