import pytest
from pathlib import Path
from backup_server.catalog.manager import CatalogManager

def test_catalog_manager(tmp_path):
    db_path = tmp_path / "test.sqlite"
    manager = CatalogManager(db_path)

    manager.add_entry(
        service="test",
        run_id="run1",
        timestamp="20230101",
        artifact_path="/path/to/art",
        checksum="abc",
        metadata={"foo": "bar"}
    )

    backups = manager.get_backups("test")
    assert len(backups) == 1
    assert backups[0]["run_id"] == "run1"

    latest = manager.get_latest_backup("test")
    assert latest["run_id"] == "run1"
