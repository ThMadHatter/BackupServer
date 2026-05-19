import pytest
from click.testing import CliRunner
from backup_server.cli import cli
from pathlib import Path
from backup_server.config import ValidationProfile

def test_cli_validate_config(tmp_path, monkeypatch):
    base_dir = tmp_path / "base"
    monkeypatch.setenv("BACKUP_BASE_DIR", str(base_dir))
    monkeypatch.setenv("BACKUP_PROFILE", "dry_run")

    runner = CliRunner()
    result = runner.invoke(cli, ["validate-config"])
    assert result.exit_code == 0
    assert "dry_run" in result.output.lower()
    assert "Configuration: VALID" in result.output

def test_cli_validate_deprecated(tmp_path, monkeypatch):
    runner = CliRunner()
    # No run_id
    result = runner.invoke(cli, ["validate"])
    assert result.exit_code == 1
    assert "use 'validate-config'" in result.output

    # With run_id
    result = runner.invoke(cli, ["validate", "some-run-id"])
    assert "Use 'validate-run' instead" in result.output

def test_cli_list_auto_init(tmp_path, monkeypatch):
    base_dir = tmp_path / "base"
    monkeypatch.setenv("BACKUP_BASE_DIR", str(base_dir))

    runner = CliRunner()
    # First check it fails with suggestion
    result = runner.invoke(cli, ["list"])
    assert "Run 'init' to bootstrap" in result.output

    # Then auto-init
    result = runner.invoke(cli, ["list", "--auto-init"])
    assert "Auto-initializing..." in result.output
    assert (base_dir / "catalog.sqlite").exists()
    assert "No backups found." in result.output

def test_cli_init_idempotency(tmp_path, monkeypatch):
    base_dir = tmp_path / "base"
    monkeypatch.setenv("BACKUP_BASE_DIR", str(base_dir))

    runner = CliRunner()
    # Run once
    runner.invoke(cli, ["init"])
    assert (base_dir / "catalog.sqlite").exists()

    # Run again
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert "Bootstrap complete" in result.output

def test_profile_strictness(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_PROFILE", "production")
    monkeypatch.setenv("PROXMOX_URL", "") # Missing

    runner = CliRunner()
    result = runner.invoke(cli, ["validate-config"])
    assert result.exit_code == 1
    assert "PROXMOX_URL is required for PRODUCTION" in result.output
