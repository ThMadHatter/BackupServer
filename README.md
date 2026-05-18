# Homelab Modular Backup System (Evolution)

This is a **self-describing, declarative backup orchestration platform** for Proxmox/LXC environments.

## 🏗️ Architecture

The system uses a declarative engine that interprets YAML specifications and executes them as a Directed Acyclic Graph (DAG).

### Core Components

- **Engine**: The core runner that parses YAML specs, builds an execution DAG, and manages the execution lifecycle.
- **DAG Executor**: Formally validates dependencies, detects cycles, and ensures correct execution ordering.
- **Staging Area**: Isolated, deterministic directories for each run.
- **Primitives**: Reusable building blocks (Network, FS, LXC, Storage) with formal contracts.
- **Catalog**: SQLite-based system tracking all backup runs, artifacts, and checksums with schema versioning.

## 🛡️ Reliability & Safety

### Execution DAG Model
- **Explicit DAG**: Generated from `depends_on` fields in YAML.
- **Validation**: Strict cycle detection and missing dependency validation.
- **Ordering**: Deterministic topological sort based on dependencies and spec order.

### Staging Lifecycle
- **Isolation**: Each run gets a unique `/var/lib/backup-engine/staging/<run_id>/`.
- **Cleanup**: Successful runs are automatically cleaned up.
- **Crash Recovery**: Failed runs preserve the staging area for forensic debugging.

### Restore Safety
- **Mandatory Integrity**: Checksums are verified *before* any restore steps are executed.
- **Overwrite Protection**: Restores will fail if target paths already exist unless `--force` is provided.
- **Dry-run Restore**: Full support for simulated recovery drills.

### Consistency Classification
Services define their consistency guarantees:
- `crash_consistent`: No guest-level freeze.
- `application_consistent`: Guest-level hooks used to quiesce apps.
- `eventual_consistent`: Data reconciled over time.

## 🚀 Usage

### Running a Backup
```bash
backup-cli run --spec specs/my_service.yaml
```

### Restoring a Service
```bash
backup-cli restore <service_name> --spec specs/my_service.yaml --version latest --force
```

## 📊 Metrics & Observability
Lightweight Prometheus textfile export available at `/var/lib/backup-engine/metrics/`.
- `backup_duration_seconds`
- `backup_status` (0/1)
- `backup_artifact_bytes`
- `backup_last_run_timestamp_seconds`

## 🛠️ Retention Model
- **Catalog-driven**: Deletion is triggered by the catalog, not just filesystem scans.
- **Atomic Promotion**: Artifacts are uploaded to temporary locations and promoted only after successful transfer.
- **Remote Cleanup**: Retention policy automatically purges old artifacts from remote storage via rclone.

## 🧪 Testing
```bash
export PYTHONPATH=.
pytest tests/
```
The suite includes DAG validation, staging isolation, and integrity verification tests.
