import pytest
from click.testing import CliRunner
from backup_server.cli import cli
from pathlib import Path

def test_cli_help_no_deps():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "List backups in the catalog" in result.output

def test_cli_init_creates_dirs(tmp_path, monkeypatch):
    base_dir = tmp_path / "base"
    monkeypatch.setenv("BACKUP_BASE_DIR", str(base_dir))

    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert base_dir.exists()
    assert (base_dir / "catalog.sqlite").exists()
    assert (base_dir / "staging").exists()

def test_cli_run_fails_missing_proxmox_url(tmp_path, monkeypatch):
    base_dir = tmp_path / "base"
    monkeypatch.setenv("BACKUP_BASE_DIR", str(base_dir))
    monkeypatch.setenv("PROXMOX_URL", "") # Empty

    # Create a dummy spec
    spec_file = tmp_path / "test.yaml"
    spec_file.write_text("name: test\nbackup: []")

    runner = CliRunner()
    with monkeypatch.context() as m:
        m.setenv("BACKUP_PROFILE", "production")
        result = runner.invoke(cli, ["run", "--spec", str(spec_file)])
    assert result.exit_code == 1
    assert "PROXMOX_URL is required" in result.output

def test_cli_list_no_db(tmp_path, monkeypatch):
    base_dir = tmp_path / "base"
    monkeypatch.setenv("BACKUP_BASE_DIR", str(base_dir))
    # DB doesn't exist

    runner = CliRunner()
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "Catalog does not exist yet" in result.output
