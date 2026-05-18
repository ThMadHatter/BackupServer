import click
import structlog
from pathlib import Path
from src.core.logging import setup_logging
from src.core.config import load_all_configs
from src.core.engine import BackupEngine
from src.core.storage import RCloneStorage
from src.core.locking import Lock

# Import modules to register them
import src.modules.qdrant
import src.modules.n8n
import src.modules.homeassistant
import src.modules.mqtt
import src.modules.zigbee2mqtt
import src.modules.cloudflared

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
        ctx.obj = {
            "infra": infra,
            "secrets": secrets,
            "config": backup_conf
        }
    except Exception as e:
        logger.error("Failed to load configuration", error=str(e))
        ctx.exit(1)

@cli.command()
@click.option("--dry-run", is_flag=True)
@click.option("--parallel", is_flag=True)
@click.pass_context
def backup(ctx, dry_run, parallel):
    infra = ctx.obj["infra"]
    backup_conf = ctx.obj["config"]
    
    with Lock(Path("/tmp/backup_server.lock")):
        storage = RCloneStorage(remote=infra.rclone_remote, config_path=infra.rclone_config_path)
        engine = BackupEngine(infra, backup_conf, storage)
        engine.run_all(dry_run=dry_run, parallel=parallel)

@cli.command()
@click.argument("module")
@click.argument("artifact")
@click.pass_context
def restore(ctx, module, artifact):
    logger.info("Restore not yet fully implemented via CLI", module=module, artifact=artifact)

if __name__ == "__main__":
    cli()
