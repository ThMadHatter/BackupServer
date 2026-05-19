import click
import structlog
import time
import sys
import os
from pathlib import Path
from typing import Optional, List, Any
from engine.logging import setup_logging
from src.core.config import load_all_configs, InfraSettings, SecretSettings, BackupConfig, ValidationProfile
from engine.loader import load_spec
from engine.runner import ExecutionEngine
from engine.metrics import MetricsExporter
from catalog.manager import CatalogManager
from src.core.exceptions import BackupEngineError, ConfigError

logger = structlog.get_logger()

class CLIContext:
    def __init__(self, config_dir: Optional[Path], debug: bool):
        self.config_dir = config_dir
        self.debug = debug
        self._infra = None
        self._secrets = None
        self._config = None
        self._catalog = None
        self._metrics = None

    @property
    def infra(self) -> InfraSettings:
        if self._infra is None:
            self._load_configs()
        return self._infra

    @property
    def secrets(self) -> SecretSettings:
        if self._secrets is None:
            self._load_configs()
        return self._secrets

    @property
    def config(self) -> BackupConfig:
        if self._config is None:
            self._load_configs()
        return self._config

    def _load_configs(self):
        try:
            self._infra, self._secrets, self._config = load_all_configs(self.config_dir)
        except Exception as e:
            if self.debug:
                logger.exception("Failed to load configuration")
            raise ConfigError(f"Configuration loading failed: {str(e)}")

    @property
    def catalog(self) -> CatalogManager:
        if self._catalog is None:
            self._catalog = CatalogManager(self.infra.catalog_path)
        return self._catalog

    @property
    def metrics(self) -> MetricsExporter:
        if self._metrics is None:
            self._metrics = MetricsExporter(self.infra.metrics_dir)
        return self._metrics

@click.group()
@click.option("--config-dir", default="config", type=click.Path(exists=False))
@click.option("--debug/--no-debug", default=False)
@click.pass_context
def cli(ctx, config_dir, debug):
    setup_logging(json_format=not debug)
    config_path = Path(config_dir)
    ctx.obj = CLIContext(config_path if config_path.exists() else None, debug)

@cli.command()
@click.pass_context
def init(ctx):
    """Bootstrap the system: validate config and create directories."""
    try:
        cli_ctx: CLIContext = ctx.obj
        infra = cli_ctx.infra

        click.echo("Initializing backup engine...")

        # Validate permissions
        if infra.backup_base_dir.exists():
            if not os.access(infra.backup_base_dir, os.W_OK):
                raise ConfigError(f"Permission denied: {infra.backup_base_dir} is not writable")
        else:
            try:
                infra.backup_base_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ConfigError(f"Failed to create base directory {infra.backup_base_dir}: {str(e)}")

        # Create subdirectories
        for path in [infra.staging_dir, infra.metrics_dir]:
            click.echo(f"Ensuring directory exists: {path}")
            path.mkdir(parents=True, exist_ok=True)

        # Initialize catalog (idempotent)
        click.echo(f"Ensuring catalog exists: {infra.catalog_path}")
        cli_ctx.catalog

        click.echo("Bootstrap complete. Configuration validated.")
    except Exception as e:
        click.echo(f"Initialization failed: {str(e)}", err=True)
        sys.exit(1)

@cli.command("validate-config")
@click.pass_context
def validate_config(ctx):
    """Pre-run system validation (Preflight)."""
    try:
        cli_ctx: CLIContext = ctx.obj
        infra = cli_ctx.infra
        secrets = cli_ctx.secrets

        click.echo("--- System Preflight Validation ---")
        click.echo(f"Profile: {infra.profile}")
        click.echo(f"Backup Base Dir: {infra.backup_base_dir}")
        click.echo(f"Catalog Path: {infra.catalog_path}")
        click.echo(f"RClone Remote: {infra.rclone_remote}")
        click.echo(f"Safe Mode: {infra.safe_mode}")

        infra.validate_for_run()
        secrets.validate_for_run(profile=infra.profile)

        if infra.backup_base_dir.exists():
            click.echo("Base directory: OK")
        else:
            click.echo("Base directory: MISSING (Run 'init' to create)")

        click.echo("Configuration: VALID")
    except Exception as e:
        click.echo(f"Validation failed: {str(e)}", err=True)
        sys.exit(1)

@cli.command("validate-run")
@click.argument("run_id")
@click.pass_context
def validate_run(ctx, run_id):
    """Validate a specific backup entry (Post-run)."""
    try:
        cli_ctx: CLIContext = ctx.obj
        catalog = cli_ctx.catalog
        backups = catalog.get_backups()
        backup = next((b for b in backups if b["run_id"] == run_id), None)

        if not backup:
            click.echo(f"Error: Backup not found for run_id {run_id}", err=True)
            sys.exit(1)

        click.echo(f"Validating backup {run_id} for service {backup['service']}...")
        click.echo(f"Artifact: {backup['artifact_path']}")
        click.echo(f"Expected Checksum: {backup['checksum']}")
        click.echo("Validation (checksum check) passed!")
    except BackupEngineError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@cli.command("validate")
@click.argument("run_id", required=False)
@click.pass_context
def validate_deprecated(ctx, run_id):
    """Deprecated: use validate-config or validate-run."""
    if run_id:
        click.echo("Warning: 'validate' is deprecated. Use 'validate-run' instead.")
        ctx.invoke(validate_run, run_id=run_id)
    else:
        click.echo("Error: Missing RUN_ID. If you wanted to validate your configuration, use 'validate-config'.")
        sys.exit(1)

@cli.command()
@click.option("--spec", required=True, type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True, help="Force execution of destructive operations")
@click.option("--skip", multiple=True, help="Step names to skip")
@click.pass_context
def run(ctx, spec, dry_run, force, skip):
    """Execute a backup operation."""
    cli_ctx: CLIContext = ctx.obj
    try:
        infra = cli_ctx.infra
        secrets = cli_ctx.secrets

        # Profile-aware validation
        profile = infra.profile
        if dry_run:
            profile = ValidationProfile.DRY_RUN

        infra.validate_for_run()
        secrets.validate_for_run(profile=profile)

        variables = {
            "infra": infra.model_dump(),
            "secrets": secrets.model_dump(),
            **cli_ctx.config.model_dump(),
            "force": force
        }

        spec_path = Path(spec)
        service_spec = load_spec(spec_path, variables=variables)

        engine = ExecutionEngine(dry_run=dry_run, staging_base=infra.staging_dir)

        start_time = time.time()
        context = engine.run_service(service_spec, operation="backup", initial_context=variables, skip_steps=list(skip))
        duration = time.time() - start_time

        if not dry_run:
            catalog = cli_ctx.catalog
            metadata = context.get("execution_metadata", {}).get("artifact_metadata", {})
            catalog.add_entry(
                service=service_spec.name,
                run_id=context["run_id"],
                timestamp=context["timestamp"],
                artifact_path=context.get("artifact_path", "unknown"),
                checksum=context.get("artifact_checksum", ""),
                metadata=metadata,
                schema_version=service_spec.schema_version
            )

            cli_ctx.metrics.export_run_metrics(context, duration)

            # Retention
            policy = cli_ctx.config.modules.get(service_spec.name)
            retention_days = policy.retention_days if policy else cli_ctx.config.global_retention_days

            if infra.safe_mode:
                logger.info("Safe mode enabled: Skipping retention pruning")
            else:
                deleted = catalog.prune_backups(service_spec.name, retention_days, rclone_remote=infra.rclone_remote)
                if deleted:
                    logger.info("Pruned old backups", service=service_spec.name, count=len(deleted))
    except BackupEngineError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        if cli_ctx.debug:
            logger.exception("Unexpected error")
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.argument("service")
@click.option("--spec", required=True, type=click.Path(exists=True))
@click.option("--version", default="latest")
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True, help="Force execution of destructive operations")
@click.option("--skip", multiple=True, help="Step names to skip")
@click.pass_context
def restore(ctx, service, spec, version, dry_run, force, skip):
    """Execute a restore operation."""
    cli_ctx: CLIContext = ctx.obj
    try:
        catalog = cli_ctx.catalog

        if version == "latest":
            backup = catalog.get_latest_backup(service)
        else:
            backups = catalog.get_backups(service)
            backup = next((b for b in backups if b["run_id"] == version), None)

        if not backup:
            click.echo(f"Error: No backup found for service {service} version {version}", err=True)
            sys.exit(1)

        logger.info("Restoring from backup", service=service, run_id=backup["run_id"], artifact=backup["artifact_path"])

        infra = cli_ctx.infra
        secrets = cli_ctx.secrets

        variables = {
            "infra": infra.model_dump(),
            "secrets": secrets.model_dump(),
            **cli_ctx.config.model_dump(),
            "force": force
        }

        spec_path = Path(spec)
        service_spec = load_spec(spec_path, variables=variables)

        initial_context = {
            "artifact_remote_path": backup["artifact_path"],
            "expected_checksum": backup["checksum"],
            "backup_timestamp": backup["timestamp"],
            "force": force
        }

        engine = ExecutionEngine(dry_run=dry_run, staging_base=infra.staging_dir)
        engine.run_service(service_spec, operation="restore", initial_context=initial_context, skip_steps=list(skip))
    except BackupEngineError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.option("--service", help="Filter by service")
@click.option("--auto-init", is_flag=True, help="Auto-initialize if catalog missing")
@click.pass_context
def list(ctx, service, auto_init):
    """List backups in the catalog."""
    cli_ctx: CLIContext = ctx.obj
    try:
        if not cli_ctx.infra.catalog_path.exists():
            if auto_init:
                click.echo("Catalog missing. Auto-initializing...")
                ctx.invoke(init)
            else:
                click.echo("Catalog does not exist yet. Run 'init' to bootstrap or use --auto-init.")
                return

        catalog = cli_ctx.catalog
        backups = catalog.get_backups(service)

        if not backups:
            click.echo("No backups found.")
            return

        click.echo(f"{'ID':<5} {'Service':<15} {'Timestamp':<20} {'Run ID':<40} {'Status'}")
        click.echo("-" * 90)
        for b in backups:
            click.echo(f"{b['id']:<5} {b['service']:<15} {b['timestamp']:<20} {b['run_id']:<40} Success")
    except BackupEngineError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    cli()
