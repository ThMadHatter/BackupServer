import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml
from pathlib import Path
from dotenv import load_dotenv
from src.core.exceptions import ConfigError

class InfraSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None, # We load manually
        extra='ignore',
        env_prefix=''
    )

    proxmox_url: Optional[str] = Field(None, alias="PROXMOX_URL")
    proxmox_user: Optional[str] = Field(None, alias="PROXMOX_USER")
    backup_base_dir: Path = Field(default=Path("/var/lib/backup-engine"))
    rclone_config_path: Optional[Path] = Field(default=None)
    rclone_remote: str = Field(default="local:/tmp/backups")
    safe_mode: bool = Field(default=True, alias="SAFE_MODE")

    @property
    def catalog_path(self) -> Path:
        return self.backup_base_dir / "catalog.sqlite"

    @property
    def staging_dir(self) -> Path:
        return self.backup_base_dir / "staging"

    @property
    def metrics_dir(self) -> Path:
        return self.backup_base_dir / "metrics"

    def validate_for_run(self):
        if not self.proxmox_url:
            raise ConfigError("PROXMOX_URL is required for execution")
        if not self.proxmox_user:
            raise ConfigError("PROXMOX_USER is required for execution")

class SecretSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,
        extra='ignore',
        env_prefix=''
    )

    proxmox_password: Optional[str] = Field(None, alias="PROXMOX_PASSWORD")
    rclone_api_key: Optional[str] = Field(None, alias="RCLONE_API_KEY")

    def validate_for_run(self):
        if not self.proxmox_password:
            raise ConfigError("PROXMOX_PASSWORD is required for execution")

class ModulePolicy(BaseModel):
    enabled: bool = True
    schedule: str = "0 2 * * *"
    retention_days: int = 30
    options: Dict[str, Any] = Field(default_factory=dict)

class BackupConfig(BaseModel):
    global_retention_days: int = 30
    modules: Dict[str, ModulePolicy] = Field(default_factory=dict)

def load_all_configs(config_dir: Optional[Path] = None) -> tuple[InfraSettings, SecretSettings, BackupConfig]:
    # 1. Defaults are in Pydantic models

    # 2 & 3. Load env files if they exist
    if config_dir:
        infra_env = config_dir / "infra.env"
        if infra_env.exists():
            load_dotenv(infra_env)

        secrets_env = config_dir / "secrets.env"
        if secrets_env.exists():
            load_dotenv(secrets_env)

    # 4. OS Env overrides are handled by Pydantic naturally because load_dotenv sets them in os.environ

    infra = InfraSettings()
    secrets = SecretSettings()

    backup_conf = BackupConfig(modules={})
    if config_dir:
        yaml_path = config_dir / "backup.yaml"
        if yaml_path.exists():
            with open(yaml_path, "r") as f:
                conf_data = yaml.safe_load(f)
                if conf_data:
                    backup_conf = BackupConfig(**conf_data)

    return infra, secrets, backup_conf
