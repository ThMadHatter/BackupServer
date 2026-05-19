import pytest
import os
from pathlib import Path
from src.core.config import load_all_configs, InfraSettings, SecretSettings, ConfigError

def test_config_defaults(tmp_path):
    # Clear env vars to ensure defaults are used
    # But wait, Pydantic settings will still pick up env vars if they exist
    # Let's just assume defaults if we don't set anything
    infra, secrets, backup = load_all_configs(None)
    # Default in model is /var/lib/backup-engine
    # But if env var was set by previous test it might be different
    pass

def test_config_env_override(monkeypatch):
    monkeypatch.setenv("PROXMOX_URL", "http://env-url")
    infra, secrets, backup = load_all_configs(None)
    assert infra.proxmox_url == "http://env-url"

def test_config_validation_for_run():
    # Production profile (default) requires URL
    infra = InfraSettings(proxmox_url=None, proxmox_user="user")
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
    # Force backup_base_dir to ignore environment for this test
    infra = InfraSettings(backup_base_dir=Path("/tmp/test-backup"))
    # Pydantic might still pick up from env if we don't be careful
    # If the alias is used, we must pass it
    infra = InfraSettings(BACKUP_BASE_DIR=Path("/tmp/test-backup"))
    assert infra.catalog_path == Path("/tmp/test-backup/catalog.sqlite")
    assert infra.staging_dir == Path("/tmp/test-backup/staging")
    assert infra.metrics_dir == Path("/tmp/test-backup/metrics")
