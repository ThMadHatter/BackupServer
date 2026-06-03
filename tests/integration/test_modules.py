import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from backup_server.modules.n8n import N8nModule
from backup_server.modules.qdrant import QdrantModule

def test_n8n_backup_local(tmp_path):
    dest = tmp_path / "dest"
    dest.mkdir()
    data = tmp_path / "data"
    data.mkdir()
    (data / "config").touch()

    module = N8nModule("n8n", {"data_dir": str(data)})

    with patch("sh.tar") as mock_tar:
        artifact = module.backup(dest)
        assert artifact == dest / "n8n_backup.tar.zst"
        mock_tar.assert_called_once()

@patch("requests.get")
@patch("requests.post")
@patch("requests.delete")
@patch("sh.tar")
def test_qdrant_backup(mock_tar, mock_delete, mock_post, mock_get, tmp_path):
    dest = tmp_path / "dest"
    dest.mkdir()

    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: {"result": {"collections": [{"name": "col1"}]}}),
        MagicMock(status_code=200, iter_content=lambda chunk_size: [b"data"])
    ]
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {"result": {"name": "snap1"}})
    mock_delete.return_value = MagicMock(status_code=200)

    module = QdrantModule("qdrant", {"host": "localhost"})
    artifact = module.backup(dest)

    assert artifact == dest / "qdrant_snapshots.tar.zst"
    assert mock_post.called
    assert mock_tar.called
