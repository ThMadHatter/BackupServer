import datetime
from pathlib import Path
from typing import List, Dict, Any
import structlog
from src.core.registry import registry
from src.core.storage import StorageProvider
from src.core.config import BackupConfig, InfraSettings

logger = structlog.get_logger()

class BackupEngine:
    def __init__(self, infra: InfraSettings, config: BackupConfig, storage: StorageProvider):
        self.infra = infra
        self.config = config
        self.storage = storage

    def run_all(self, dry_run: bool = False):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report = {"timestamp": timestamp, "modules": {}}
        
        logger.info("Starting backup run", dry_run=dry_run)

        for module_name, policy in self.config.modules.items():
            if not policy.enabled:
                logger.info("Module disabled, skipping", module=module_name)
                continue

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
                        # Upload
                        remote_path = f"{module_name}/{timestamp}/{artifact_path.name}"
                        self.storage.upload(artifact_path, remote_path)
                        report["modules"][module_name] = {"status": "success", "artifact": str(artifact_path)}
                    else:
                        logger.error("Validation failed", module=module_name)
                        report["modules"][module_name] = {"status": "failed", "reason": "validation_failure"}
                else:
                    report["modules"][module_name] = {"status": "dry_run"}

            except Exception as e:
                logger.exception("Module backup failed", module=module_name, error=str(e))
                report["modules"][module_name] = {"status": "failed", "reason": str(e)}

        self.generate_report(report)
        return report

    def generate_report(self, report: Dict[str, Any]):
        logger.info("Backup run finished", report=report)
        # Here we could send notifications
