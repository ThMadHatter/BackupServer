# ⚙️ 2. Step-by-Step Setup & Installation

### A. Clone the Repository
Clone the repository directly onto your Proxmox host:
```bash
git clone https://github.com/ThMadHatter/BackupServer.git /opt/backup-server
cd /opt/backup-server
```

### B. Install Dependencies
It is recommended to use a virtual environment, but you can also install globally if this is a dedicated management node:
```bash
# Modern pip install (reads pyproject.toml)
pip install .
```

### C. Configure Environment Files
Navigate to the `config/` directory and set up your environment:

1. **`config/infra.env`**: Non-sensitive settings.
```env
PROXMOX_URL=https://127.0.0.1:8006/api2/json
PROXMOX_USER=root@pam
BACKUP_BASE_DIR=/mnt/pve/backups/homelab
RCLONE_REMOTE=gdrive:homelab-backups
SAFE_MODE=True
BACKUP_PROFILE=production
```

2. **`config/secrets.env`**: Sensitive credentials.
```env
PROXMOX_PASSWORD=your_secure_password
RCLONE_API_KEY=optional_key
HA_TOKEN=optional_homeassistant_token
```

3. **`config/backup.yaml`**: Global policies.
```yaml
global_retention_days: 30
retention:
  minimum_backups: 3
  protect_latest: true
  require_restore_validation: false
```

### D. Initialization & Health Checks
Bootstrap the system and verify everything is correct:
```bash
# Initialize directories and the SQLite catalog
python3 -m backup_server.main init

# Run preflight validation
python3 -m backup_server.main validate-config

# Run a full system health check
python3 -m backup_server.main doctor
```

[Back to Index](./README.md)
