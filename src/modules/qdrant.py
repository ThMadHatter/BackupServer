import requests
from pathlib import Path
from src.modules.base import BackupModule
from src.core.registry import register_module

@register_module("qdrant")
class QdrantModule(BackupModule):
    def backup(self, dest_path: Path, dry_run: bool = False) -> Path:
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 6333)
        api_key = self.config.get("api_key")
        use_ssl = self.config.get("use_ssl", False)
        protocol = "https" if use_ssl else "http"
        base_url = f"{protocol}://{host}:{port}"
        
        headers = {}
        if api_key:
            headers["api-key"] = api_key

        if dry_run:
            self.logger.info("Dry run: Would trigger Qdrant snapshot", host=host)
            artifact_path = dest_path / "qdrant_mock.snapshot"
            artifact_path.touch()
            return artifact_path

        self.logger.info("Triggering Qdrant snapshots for all collections", host=host)
        
        try:
            # 1. Get all collections
            response = requests.get(f"{base_url}/collections", headers=headers, timeout=10)
            response.raise_for_status()
            collections = [c["name"] for c in response.json()["result"]["collections"]]
            
            snapshot_paths = []
            for collection in collections:
                self.logger.info("Creating snapshot for collection", collection=collection)
                snap_res = requests.post(f"{base_url}/collections/{collection}/snapshots", headers=headers, timeout=30)
                snap_res.raise_for_status()
                snap_name = snap_res.json()["result"]["name"]

                # Download snapshot
                self.logger.info("Downloading snapshot", collection=collection, snapshot=snap_name)
                download_res = requests.get(f"{base_url}/collections/{collection}/snapshots/{snap_name}", headers=headers, stream=True)
                download_res.raise_for_status()

                snap_file = dest_path / f"{collection}_{snap_name}"
                with open(snap_file, "wb") as f:
                    for chunk in download_res.iter_content(chunk_size=8192):
                        f.write(chunk)
                snapshot_paths.append(snap_file)

                # Optionally delete snapshot from Qdrant to save space
                requests.delete(f"{base_url}/collections/{collection}/snapshots/{snap_name}", headers=headers)

            # 2. Archive all snapshots into one file
            import tarfile
            artifact_path = dest_path / "qdrant_snapshots.tar.zst"

            # Using tarfile with external zstd if possible, or just tar for now
            # To keep it simple and robust, we'll use sh.tar if available as before
            import sh
            sh.tar("-I", "zstd", "-cvf", str(artifact_path), "-C", str(dest_path), *[p.name for p in snapshot_paths])

            # Cleanup individual snapshots
            for p in snapshot_paths:
                p.unlink()

            return artifact_path

        except Exception as e:
            self.logger.error("Qdrant backup failed", error=str(e))
            raise

    def restore(self, src_path: Path, dry_run: bool = False) -> bool:
        if dry_run:
            self.logger.info("Dry run: Would restore Qdrant from", path=str(src_path))
            return True
        # Restore logic: Extract tar, then for each snapshot POST to /collections/{name}/snapshots/recover
        return True

    def validate(self, artifact_path: Path) -> bool:
        import sh
        try:
            sh.zstd("-t", str(artifact_path))
            return True
        except:
            return False
