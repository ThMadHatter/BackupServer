import pytest
from pathlib import Path
import json
from src.core.catalog import BackupCatalog

def test_catalog_save_load(tmp_path):
    catalog_path = tmp_path / "catalog.json"
    catalog = BackupCatalog(catalog_path)

    entry = {"module": "test", "artifact": "path", "created_at": "2023-01-01T00:00:00"}
    catalog.add_entry(entry)

    assert catalog_path.exists()

    new_catalog = BackupCatalog(catalog_path)
    assert len(new_catalog.entries) == 1
    assert new_catalog.entries[0]["module"] == "test"

def test_catalog_get_backups(tmp_path):
    catalog = BackupCatalog(tmp_path / "catalog.json")
    catalog.add_entry({"module": "m1", "artifact": "a1"})
    catalog.add_entry({"module": "m2", "artifact": "a2"})

    m1_backups = catalog.get_backups_for_module("m1")
    assert len(m1_backups) == 1
    assert m1_backups[0]["artifact"] == "a1"
