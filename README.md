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

## 🚀 CLI Command Reference

### `init`
Bootstraps the environment by creating the necessary directory structure and the SQLite catalog.
- **Usage**: `python3 -m backup_server.main init`

### `run`
Executes a backup operation for a service.
- **Usage**: `python3 -m backup_server.main run --spec <path_to_yaml> [OPTIONS]`
- **Options**:
    - `--spec`: (Required) Path to the service specification YAML.
    - `--dry-run`: Simulate execution. Skips destructive primitives (`pct_exec`, `rclone_upload`, etc.) and doesn't update the catalog.
    - `--force`: Force execution even if safety checks fail.
    - `--skip <step_name>`: Skip one or more steps in the backup DAG.

### `restore`
Restores a service from a previous backup.
- **Usage**: `python3 -m backup_server.main restore <service_name> --spec <path_to_yaml> [OPTIONS]`
- **Options**:
    - `--version <run_id>`: Specify the run ID to restore (defaults to `latest`).
    - `--force`: Required if the restore target path already exists on disk.
    - `--dry-run`: Simulate the restore process.

### `list`
Lists backup history from the catalog.
- **Usage**: `python3 -m backup_server.main list [OPTIONS]`
- **Options**:
    - `--service`: Filter the list by a specific service name.
    - `--auto-init`: Automatically run `init` if the catalog is missing.

### `generate-spec`
Generates a boilerplate YAML specification.
- **Usage**: `python3 -m backup_server.main generate-spec --type <lxc|generic|http>`
- **Types**:
    - `lxc`: Standard Proxmox container pattern using `pct_exec` and `pct_pull`.
    - `generic`: Simple filesystem-based backup.
    - `http`: API-triggered backup pattern.

### `validate-config`
Validates all configuration files and environment variables.
- **Usage**: `python3 -m backup_server.main validate-config`

### `doctor`
Detailed health check of the local system (permissions, DB integrity, storage reachability).
- **Usage**: `python3 -m backup_server.main doctor`

### `audit`
Detects inconsistencies between the catalog database and actual remote storage artifacts.
- **Usage**: `python3 -m backup_server.main audit`

## 🛠️ Primitives Library

Primitives are the atomic building blocks used in your YAML specs.

### LXC (Proxmox)
- **`pct_exec`**: Run a command inside a container.
    - `vmid`: Container ID.
    - `command`: String or list of command arguments.
- **`pct_pull`**: Copy a file from a container to the host.
    - `vmid`, `source` (in-container), `dest` (host).
- **`pct_push`**: Copy a file from the host to a container.
    - `vmid`, `source` (host), `dest` (in-container).

### Storage & Filesystem
- **`rclone_upload`**: Upload a file/dir to remote storage.
    - `local_path`, `remote_name`, `remote_path`.
- **`tar`**: Create a compressed archive.
    - `source_dir`, `dest_file`.
- **`copy`**: Copy files locally.
    - `source`, `dest`.
- **`checksum`**: Calculate SHA256 of a file.
    - `file_path`.

### Network & Utilities
- **`http_get` / `http_post`**: Perform API requests.
- **`http_download`**: Download a file via URL.
- **`json_query`**: Extract data from a JSON response using JMESPath.
- **`template`**: Render a Jinja2 template (useful for logging or complex paths).

## 💡 Best Practices

1. **Avoid Direct Rootfs Access**: Instead of reading `/var/lib/lxc/.../rootfs`, use `pct_pull` to copy artifacts out of the container. This is safer and Proxmox-native.
2. **Use Staging Paths**: Leverage the `{{ staging_dir }}` variable for temporary files to ensure they are cleaned up automatically after the run.
3. **Atomic Uploads**: The `rclone_upload` primitive supports atomic promotion (uploading to `.tmp` first) by default.

## 🧪 Testing
```bash
export PYTHONPATH=.
pytest -v
```
