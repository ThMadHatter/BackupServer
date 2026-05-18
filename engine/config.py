import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml
from pathlib import Path
from dotenv import load_dotenv

class InfraSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
    
    proxmox_url: str = Field(..., alias="PROXMOX_URL")
    proxmox_user: str = Field(..., alias="PROXMOX_USER")
    backup_base_dir: Path = Field(default=Path("/tmp/backups"))
    rclone_config_path: Path = Field(default=Path("~/.config/rclone/rclone.conf").expanduser())
    rclone_remote: str = Field(default="gdrive:backups")

class SecretSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env.secrets', env_file_encoding='utf-8', extra='ignore')
    
    proxmox_password: str = Field(..., alias="PROXMOX_PASSWORD")
    rclone_api_key: Optional[str] = Field(None, alias="RCLONE_API_KEY")

class ModulePolicy(BaseModel):
    enabled: bool = True
    schedule: str = "0 2 * * *"  # Cron format
    retention_days: int = 30
    options: Dict[str, Any] = {}

class BackupConfig(BaseModel):
    global_retention_days: int = 30
    modules: Dict[str, ModulePolicy]

def load_all_configs(config_dir: Path) -> tuple[InfraSettings, SecretSettings, BackupConfig]:
    # Load env files
    load_dotenv(config_dir / "infra.env")
    load_dotenv(config_dir / "secrets.env")
    
    infra = InfraSettings()
    secrets = SecretSettings()
    
    with open(config_dir / "backup.yaml", "r") as f:
        conf_data = yaml.safe_load(f)
        backup_conf = BackupConfig(**conf_data)
        
    return infra, secrets, backup_conf
