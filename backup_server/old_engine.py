import datetime
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog
from backup_server.registry import registry
from backup_server.storage import StorageProvider
from backup_server.config import BackupConfig, InfraSettings
from backup_server.catalog.manager import BackupCatalog, BackupEntry

logger = structlog.get_logger()

class BackupEngine:
    def __init__(self, infra: InfraSettings, config: BackupConfig, storage: StorageProvider, catalog: Optional[BackupCatalog] = None):
        self.infra = infra
        self.config = config
        self.storage = storage
        self.catalog = catalog or BackupCatalog(infra.backup_base_dir / "catalog.json")

    def run_all(self, dry_run: bool = False, parallel: bool = False):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report = {"timestamp": timestamp, "modules": {}}
        
        logger.info("Starting backup run", dry_run=dry_run, parallel=parallel)

        enabled_modules = [
            (name, policy) for name, policy in self.config.modules.items() if policy.enabled
        ]

        if parallel:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {
                    executor.submit(self.run_module, name, policy, timestamp, dry_run): name
                    for name, policy in enabled_modules
                }
                for future in concurrent.futures.as_completed(futures):
                    module_name = futures[future]
                    try:
                        report["modules"][module_name] = future.result()
                    except Exception as e:
                        logger.exception("Module backup failed", module=module_name, error=str(e))
                        report["modules"][module_name] = {"status": "failed", "reason": str(e)}
        else:
            for module_name, policy in enabled_modules:
                try:
                    report["modules"][module_name] = self.run_module(module_name, policy, timestamp, dry_run)
                except Exception as e:
                    logger.exception("Module backup failed", module=module_name, error=str(e))
                    report["modules"][module_name] = {"status": "failed", "reason": str(e)}

        if not dry_run:
            self.enforce_retention()

        self.generate_report(report)
        return report

    def run_module(self, module_name: str, policy: Any, timestamp: str, dry_run: bool) -> Dict[str, Any]:
        try:
            module_class = registry.get_module(module_name)
            module_instance = module_class(module_name, policy.options)

            dest_dir = self.infra.backup_base_dir / module_name / timestamp
            if not dry_run:
                dest_dir.mkdir(parents=True, exist_ok=True)

            logger.info("Running module backup", module=module_name)
            artifact_path = module_instance.backup(dest_dir, dry_run=dry_run)

            if not dry_run:
                # Validate
                if module_instance.validate(artifact_path):
                    logger.info("Validation successful", module=module_name)

                    checksum = module_instance.calculate_checksum(artifact_path)

                    # Upload
                    remote_path = f"{module_name}/{timestamp}/{artifact_path.name}"
                    self.storage.upload(artifact_path, remote_path)

                    # Add to catalog
                    entry = BackupEntry(
                        module=module_name,
                        timestamp=timestamp,
                        artifact=remote_path,
                        checksum=checksum
                    )
                    self.catalog.add_entry(entry)

                    return {"status": "success", "artifact": str(artifact_path), "checksum": checksum}
                else:
                    logger.error("Validation failed", module=module_name)
                    return {"status": "failed", "reason": "validation_failure"}
            else:
                return {"status": "dry_run"}
        except Exception as e:
            logger.exception("Module backup failed", module=module_name, error=str(e))
            return {"status": "failed", "reason": str(e)}

    def enforce_retention(self):
        logger.info("Enforcing retention policies")
        now = datetime.datetime.now()

        remaining_entries = []
        for entry in self.catalog.entries:
            module_name = entry["module"]
            policy = self.config.modules.get(module_name)
            retention_days = policy.retention_days if policy else self.config.global_retention_days

            created_at = datetime.datetime.fromisoformat(entry["created_at"])
            if (now - created_at).days > retention_days:
                logger.info("Entry expired, deleting", module=module_name, artifact=entry["artifact"])
                try:
                    self.storage.delete(entry["artifact"])
                except Exception as e:
                    logger.error("Failed to delete expired artifact", artifact=entry["artifact"], error=str(e))
                # We don't add it to remaining_entries
            else:
                remaining_entries.append(entry)

        self.catalog.entries = remaining_entries
        self.catalog.save()

    def generate_report(self, report: Dict[str, Any]):
        logger.info("Backup run finished", report=report)
        # Here we could send notifications
