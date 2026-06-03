import pytest
from backup_server.catalog.manager import CatalogManager
from backup_server.exceptions import CatalogError
from pathlib import Path

def test_catalog_auto_create_dir(tmp_path):
    db_path = tmp_path / "subdir" / "catalog.sqlite"
    # Subdir does not exist
    CatalogManager(db_path)
    assert db_path.exists()

def test_catalog_permission_denied():
    # Attempting to create in a path that should be restricted (on most systems)
    # or just use a path we can't write to.
    db_path = Path("/proc/invalid_path/catalog.sqlite")
    with pytest.raises(CatalogError, match="Permission denied|Failed to create catalog directory"):
        CatalogManager(db_path)
