import pytest
import os
from pathlib import Path
from backup_server.config import load_all_configs, InfraSettings, SecretSettings, ConfigError, ValidationProfile

def test_config_defaults(tmp_path):
    # Pass empty config dir to avoid loading local env files
    config_dir = tmp_path / "empty_config"
    config_dir.mkdir()
    infra, secrets, backup = load_all_configs(config_dir)
    # Use alias for comparison if needed, or check the specific field
    assert infra.safe_mode is True

def test_config_env_override(monkeypatch, tmp_path):
    config_dir = tmp_path / "empty_config"
    config_dir.mkdir()
    monkeypatch.setenv("PROXMOX_URL", "http://env-url")
    infra, secrets, backup = load_all_configs(config_dir)
    assert infra.proxmox_url == "http://env-url"

def test_config_validation_for_run():
    # Force profile to PRODUCTION to test strict validation
    infra = InfraSettings(BACKUP_PROFILE=ValidationProfile.PRODUCTION, PROXMOX_URL=None, PROXMOX_USER="user")
    with pytest.raises(ConfigError, match="PROXMOX_URL is required for PRODUCTION"):
        infra.validate_for_run()

def test_config_layered_loading(tmp_path, monkeypatch):
    # Clear environment variables that might interfere
    monkeypatch.delenv("PROXMOX_URL", raising=False)
    monkeypatch.delenv("PROXMOX_USER", raising=False)

    config_dir = tmp_path / "config"
    config_dir.mkdir()

    infra_env = config_dir / "infra.env"
    infra_env.write_text("PROXMOX_URL=http://file-url\nPROXMOX_USER=file-user")

    infra, secrets, backup = load_all_configs(config_dir)
    assert infra.proxmox_url == "http://file-url"
    assert infra.proxmox_user == "file-user"

def test_derived_paths():
    infra = InfraSettings(BACKUP_BASE_DIR=Path("/tmp/test-backup"))
    assert infra.catalog_path == Path("/tmp/test-backup/catalog.sqlite")
    assert infra.staging_dir == Path("/tmp/test-backup/staging")
    assert infra.metrics_dir == Path("/tmp/test-backup/metrics")
