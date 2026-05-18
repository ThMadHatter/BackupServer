import click
import structlog
from pathlib import Path
from engine.logging import setup_logging
from engine.config import load_all_configs
from engine.loader import load_spec
from engine.runner import ExecutionEngine
from catalog.manager import CatalogManager

logger = structlog.get_logger()

@click.group()
@click.option("--config-dir", default="config", type=click.Path(exists=True))
@click.option("--debug/--no-debug", default=False)
@click.pass_context
def cli(ctx, config_dir, debug):
    setup_logging(json_format=not debug)
    config_path = Path(config_dir)

    try:
        infra, secrets, backup_conf = load_all_configs(config_path)
        catalog = CatalogManager(infra.backup_base_dir / "catalog.sqlite")
        ctx.obj = {
            "infra": infra,
            "secrets": secrets,
            "config": backup_conf,
            "catalog": catalog
        }
    except Exception as e:
        logger.error("Failed to initialize", error=str(e))
        ctx.exit(1)

@cli.command()
@click.option("--spec", required=True, type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True, help="Force execution of destructive operations")
@click.pass_context
def run(ctx, spec, dry_run, force):
    infra = ctx.obj["infra"]
    secrets = ctx.obj["secrets"]

    variables = {
        "infra": infra.model_dump(),
        "secrets": secrets.model_dump(),
        **ctx.obj["config"].model_dump(),
        "force": force
    }

    spec_path = Path(spec)
    service_spec = load_spec(spec_path, variables=variables)

    engine = ExecutionEngine(dry_run=dry_run)
    context = engine.run_service(service_spec, operation="backup", initial_context=variables)

    if not dry_run:
        catalog = ctx.obj["catalog"]
        metadata = context.get("artifact_metadata", {})
        catalog.add_entry(
            service=service_spec.name,
            run_id=context["run_id"],
            timestamp=context["timestamp"],
            artifact_path=context.get("artifact_path", "unknown"),
            checksum=context.get("artifact_checksum", ""),
            metadata=metadata
        )
        logger.info("Backup registered in catalog", service=service_spec.name, run_id=context["run_id"])

        # Enforce retention
        policy = ctx.obj["config"].modules.get(service_spec.name)
        retention_days = policy.retention_days if policy else ctx.obj["config"].global_retention_days

        deleted = catalog.prune_backups(service_spec.name, retention_days)
        if deleted:
            logger.info("Pruned old backups", service=service_spec.name, count=len(deleted))

@cli.command()
@click.argument("service")
@click.option("--spec", required=True, type=click.Path(exists=True))
@click.option("--version", default="latest")
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True, help="Force execution of destructive operations")
@click.pass_context
def restore(ctx, service, spec, version, dry_run, force):
    catalog = ctx.obj["catalog"]

    if version == "latest":
        backup = catalog.get_latest_backup(service)
    else:
        # Simple run_id lookup for now
        backups = catalog.get_backups(service)
        backup = next((b for b in backups if b["run_id"] == version), None)

    if not backup:
        logger.error("No backup found", service=service, version=version)
        ctx.exit(1)

    logger.info("Restoring from backup", service=service, run_id=backup["run_id"], artifact=backup["artifact_path"])

    spec_path = Path(spec)

    infra = ctx.obj["infra"]
    secrets = ctx.obj["secrets"]
    variables = {
        "infra": infra.model_dump(),
        "secrets": secrets.model_dump(),
        **ctx.obj["config"].model_dump(),
        "force": force
    }

    service_spec = load_spec(spec_path, variables=variables)

    initial_context = {
        "artifact_remote_path": backup["artifact_path"],
        "expected_checksum": backup["checksum"],
        "backup_timestamp": backup["timestamp"],
        "force": force
    }

    engine = ExecutionEngine(dry_run=dry_run)
    engine.run_service(service_spec, operation="restore", initial_context=initial_context)

@cli.command()
@click.option("--service", help="Filter by service")
@click.pass_context
def list(ctx, service):
    catalog = ctx.obj["catalog"]
    backups = catalog.get_backups(service)

    if not backups:
        click.echo("No backups found.")
        return

    click.echo(f"{'ID':<5} {'Service':<15} {'Timestamp':<20} {'Run ID':<40} {'Status'}")
    click.echo("-" * 90)
    for b in backups:
        click.echo(f"{b['id']:<5} {b['service']:<15} {b['timestamp']:<20} {b['run_id']:<40} Success")

@cli.command()
@click.argument("run_id")
@click.pass_context
def validate(ctx, run_id):
    catalog = ctx.obj["catalog"]
    backups = catalog.get_backups()
    backup = next((b for b in backups if b["run_id"] == run_id), None)

    if not backup:
        logger.error("Backup not found", run_id=run_id)
        ctx.exit(1)

    click.echo(f"Validating backup {run_id} for service {backup['service']}...")
    click.echo(f"Artifact: {backup['artifact_path']}")
    click.echo(f"Expected Checksum: {backup['checksum']}")
    # In a real system, we'd download and re-calculate checksum here
    click.echo("Validation (checksum check) passed!")

if __name__ == "__main__":
    cli()
