# Homelab Modular Backup System (Production Grade)

This is a **self-describing, declarative backup orchestration platform** for Proxmox/LXC environments.

## 🏗️ Architecture

The system is built as a single Python package (`backup_server`) with a unified Directed Acyclic Graph (DAG) execution model.

### Core Components

- **Engine**: DAG-based runner with explicit dependency injection.
- **CLI**: Stabilized entrypoint (`python -m backup_server.main`) with lazy initialization.
- **Catalog**: SQLite-based system tracking all backup runs, artifacts, and checksums with mandatory validation flags.
- **Manifests**: Every run generates an immutable `manifest.json` capturing host info, execution steps, and artifact hashes.
- **Staging**: Isolated directories per run (`<BACKUP_BASE_DIR>/staging/<run_id>`) with deterministic cleanup.

## ⚙️ Configuration

The system uses a hierarchical configuration loading mechanism.

### 1. `config/infra.env`
Non-sensitive infrastructure settings.
```env
PROXMOX_URL=https://192.168.1.10:8006/api2/json
PROXMOX_USER=root@pam
BACKUP_BASE_DIR=/mnt/pve/backups/homelab
RCLONE_REMOTE=gdrive:homelab-backups
SAFE_MODE=True
BACKUP_PROFILE=production
```

### 2. `config/secrets.env`
Sensitive credentials.
```env
PROXMOX_PASSWORD=your_password
RCLONE_API_KEY=your_key
HA_TOKEN=your_homeassistant_token
```

### 3. `config/backup.yaml`
Global policies and module-specific configurations.
```yaml
global_retention_days: 30
retention:
  minimum_backups: 3
  protect_latest: true
  require_restore_validation: false
modules:
  n8n:
    enabled: true
    retention_days: 14
```

## 🚀 Usage Guide

### Installation
```bash
pip install pydantic pydantic-settings structlog click python-dotenv zstandard sh pyyaml requests jinja2
```

### 1. Bootstrapping
- **`init`**: Bootstraps the environment.
  ```bash
  python3 -m backup_server.main init
  ```
  Creates `staging/`, `metrics/`, and the `catalog.sqlite` database in your `BACKUP_BASE_DIR`.

### 2. Pre-flight & Maintenance
- **`validate-config`**: Validates all configuration files and environment variables.
  ```bash
  python3 -m backup_server.main validate-config
  ```

- **`doctor`**: Detailed health check of the local system.
  ```bash
  python3 -m backup_server.main doctor
  ```
  Checks directory permissions, SQLite integrity, and RClone reachability.

- **`audit`**: Detects inconsistencies between the catalog and remote storage.
  ```bash
  python3 -m backup_server.main audit
  ```

### 3. Service Specifications
- **`generate-spec`**: Creates a boilerplate YAML for new services.
  ```bash
  python3 -m backup_server.main generate-spec --type lxc > specs/my_app.yaml
  ```
  Available types: `lxc`, `generic`, `http`.

### 4. Backup & Restore Operations
- **`run`**: Executes the backup DAG.
  ```bash
  python3 -m backup_server.main run --spec specs/n8n.yaml
  ```
  **Options:**
  - `--dry-run`: Log actions without executing side effects (uploads, container execs).
  - `--force`: Ignore safety locks and execute destructive steps.
  - `--skip <step_name>`: Skip a specific DAG node.

- **`restore`**: Executes the restore DAG.
  ```bash
  python3 -m backup_server.main restore n8n --spec specs/n8n.yaml
  ```
  **Options:**
  - `--version <run_id>`: Restore a specific version (default: `latest`).
  - `--force`: Required if target files already exist (overwrite protection).

### 5. Monitoring & Catalog
- **`list`**: Shows history of backup runs.
  ```bash
  python3 -m backup_server.main list --service n8n
  ```

- **`validate-run`**: Verifies the checksum of a completed backup.
  ```bash
  python3 -m backup_server.main validate-run <run_id>
  ```

## 📊 Observability
Metrics are exported to `<BACKUP_BASE_DIR>/metrics/` in Prometheus textfile format.

## 🧪 Testing
```bash
export PYTHONPATH=.
pytest -v
```
