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

## 🛡️ Reliability & Safety

### Retention Safety Gates
Retention policy is protected by multiple barriers:
- **Protect Latest**: Never deletes the most recent successful backup.
- **Minimum Count**: Enforces a minimum number of backups per service.
- **Validation Required**: Optionally prevents deletion of backups that haven't passed a restore drill.
- **Checksum Guard**: Won't delete backups with missing or mismatched checksums.

### Restore Safety
- **Mandatory Integrity**: Checksums are verified *before* and *after* restore.
- **Overwrite Protection**: Prevents accidental data loss unless `--force` is used.
- **E2E Drills**: Fully automated restore drills verify byte-level equality.

### Concurrency
- **Per-Service Locking**: Prevents overlapping runs for the same service.
- **Global Locking**: Orchestration-level protection.

## 🚀 Usage

### Installation
```bash
pip install pydantic pydantic-settings structlog click python-dotenv zstandard sh pyyaml requests jinja2 jmespath
```

### Bootstrapping
```bash
python -m backup_server.main init
```

### Execution
```bash
# Run a backup
python -m backup_server.main run --spec specs/qdrant.yaml

# System Preflight
python -m backup_server.main validate-config

# Validate a specific run
python -m backup_server.main validate-run <run_id>

# System Health
python -m backup_server.main doctor
```

## 📊 Observability
Prometheus textfile exporter (`<BACKUP_BASE_DIR>/metrics/`).

## 🧪 Testing
```bash
export PYTHONPATH=.
pytest -v
```
Includes unit, integration, and E2E restore drills.
