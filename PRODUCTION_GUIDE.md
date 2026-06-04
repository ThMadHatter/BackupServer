# 🛡️ BackupServer: Production Deployment & User Guide

Welcome to the official production guide for **BackupServer**, a self-describing, declarative backup orchestration platform designed specifically for Proxmox/LXC environments. This guide will walk you through a full deployment, from initial setup to advanced monitoring.

---

## 🚀 1. Introduction & Prerequisites

### What is BackupServer?
BackupServer is a DAG-based orchestration engine that allows you to define backup and restore procedures as simple YAML specifications. It provides:
- **Declarative Specs**: Define *what* to backup, not *how*.
- **Atomic Operations**: Integrated support for Proxmox `pct` commands and `rclone`.
- **Immutable Audit Trail**: Every run is captured in a local SQLite catalog with cryptographic checksums.
- **Dependency Awareness**: Automatically handles the order of operations (e.g., stopping a service before backup).

### Prerequisites
Before installing BackupServer on your Proxmox host, ensure you meet the following requirements:
- **Hardware**: A Proxmox VE host (7.x or 8.x).
- **Python**: Python 3.10 or higher.
- **System Tools**:
  - `git`
  - `rclone` (configured with at least one remote)
  - `proxmox-ve` (standard PVE installation)
- **Privileges**: The tool should be run as `root` (or a user with sudo access to `pct` and backup directories).

---

## ⚙️ 2. Step-by-Step Setup & Installation

### A. Clone the Repository
Clone the repository directly onto your Proxmox host:
```bash
git clone https://github.com/ThMadHatter/BackupServer.git /opt/backup-server
cd /opt/backup-server
```

### B. Install Dependencies
It is recommended to use a virtual environment, but you can also install globally if this is a dedicated management node:
```bash
pip install -r pyproject.toml
# Or if using the modern pip:
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

---

## 📦 3. Container Backup Guide

BackupServer uses YAML specs to define backup logic. You can generate a template to get started:
```bash
python3 -m backup_server.main generate-spec --type lxc > specs/my_container.yaml
```

### Scenario A: Basic LXC File-System Backup
A simple backup that pulls a directory from a container and stores it locally.

```yaml
name: simple-lxc-backup
schema_version: "1.0"
backup:
  - name: archive_container_data
    type: pct_exec
    options:
      vmid: 101
      command: "tar -I zstd -cf /tmp/data.tar.zst -C /var/www/html ."

  - name: pull_to_host
    type: pct_pull
    options:
      vmid: 101
      source: "/tmp/data.tar.zst"
      dest: "/tmp/backup.tar.zst"
    store_result: artifact_path
```

### Scenario B: Complex Application Backup (PostgreSQL)
A production-grade backup that stops a service, performs a database dump, pulls the artifact, and uploads it offsite via `rclone`.

```yaml
name: postgres-app
schema_version: "1.0"
backup:
  - name: stop_app
    type: pct_exec
    options:
      vmid: 105
      command: "systemctl stop my-app"

  - name: db_dump
    type: pct_exec
    options:
      vmid: 105
      command: "pg_dump -U postgres my_db > /tmp/db_dump.sql"

  - name: pull_dump
    type: pct_pull
    options:
      vmid: 105
      source: "/tmp/db_dump.sql"
      dest: "/tmp/db_dump_{{ timestamp }}.sql"
    store_result: artifact_path

  - name: upload_offsite
    type: rclone_upload
    options:
      local_path: "{{ artifact_path }}"
      remote_name: "gdrive"
      remote_path: "backups/postgres/{{ timestamp }}.sql"

  - name: start_app
    type: pct_exec
    options:
      vmid: 105
      command: "systemctl start my-app"
```

### Executing the Backup
```bash
python3 -m backup_server.main run --spec specs/postgres-app.yaml
```

---

## 🔄 4. Container Restore Procedures

### Listing Available Backups
View the history of successful backups tracked in the SQLite catalog:
```bash
python3 -m backup_server.main list --service postgres-app
```

### Running an Audit
Ensure that the catalog matches reality (remote storage consistency):
```bash
python3 -m backup_server.main audit
```

### Executing a Restore
To restore a specific version, use the `restore` command. By default, it will attempt to restore the `latest` version unless `--version` is specified.

```bash
# Restore latest
python3 -m backup_server.main restore postgres-app --spec specs/postgres-app.yaml

# Restore a specific run ID
python3 -m backup_server.main restore postgres-app --spec specs/postgres-app.yaml --version run_20231027_120000
```

---

## 📊 5. Grafana Monitoring Integration

BackupServer exports metrics in two ways: via the local SQLite `catalog.sqlite` and via Prometheus-compatible `.prom` files in the `metrics/` directory.

### Option A: Grafana SQLite Data Source
The easiest way to visualize backup history is to connect Grafana directly to the SQLite catalog.

1. Install the **SQLite Data Source** plugin in Grafana.
2. Add a new Data Source and point the path to your `catalog.sqlite` (e.g., `/mnt/pve/backups/homelab/catalog.sqlite`).
3. Use the following SQL queries for your panels:

**Backup Success vs. Failure (Pie Chart)**:
```sql
SELECT
  CASE WHEN validated = 1 THEN 'Validated' ELSE 'Success' END as Status,
  count(*) as Count
FROM backups
GROUP BY validated
```

**Artifact Sizes over Time (Time Series)**:
```sql
SELECT
  datetime(timestamp) as time,
  json_extract(metadata, '$.size') as size_bytes
FROM backups
WHERE service = 'postgres-app'
ORDER BY time ASC
```

### Option B: Telegraf & Prometheus (Textfile Collector)
BackupServer writes `.prom` files to the `metrics/` subdirectory under your `BACKUP_BASE_DIR`. Configure Telegraf to read these:

```toml
[[inputs.file]]
  files = ["/mnt/pve/backups/homelab/metrics/*.prom"]
  data_format = "prometheus"
```

### Recommended Dashboard Panels
- **Backup Health**: A "Stat" panel showing the count of successful backups in the last 24 hours.
- **Storage Consumption**: A "Gauge" panel showing the total size of current artifacts.
- **Duration Heatmap**: Visualize how long backups are taking over time to identify performance regressions.
