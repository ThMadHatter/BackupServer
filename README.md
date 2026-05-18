# Homelab Modular Backup System

A production-grade, modular backup framework designed for Proxmox VE environments running LXC containers.

## Architecture

The system is built with a core-plugin architecture:

- **Core Engine**: Orchestrates backup runs, handles configuration, locking, parallel execution, and retention policies.
- **Modules**: Independent plugins for each service (n8n, Qdrant, Home Assistant, etc.).
- **Storage Abstraction**: Decouples the backup logic from the storage provider (initially supporting Google Drive via rclone).
- **Catalog**: Tracks backup artifacts, timestamps, and checksums for automated retention and easy recovery.

## Design Decisions

1. **Python Implementation**: Chosen for its superior error handling, testability (pytest), and modularity compared to Bash.
2. **zstd Compression**: High performance and excellent compression ratios for homelab workloads.
3. **Pydantic**: Used for robust configuration loading and validation.
4. **Structured Logging**: JSON logging via `structlog` for easy observability and integration with monitoring stacks.
5. **Atomic-like Operations**: Backups are validated and checksummed before being uploaded to remote storage.
6. **LXC Integration**: Modules support `pct exec` to perform operations directly inside LXC containers from the Proxmox host.

## Components

### Core
- `src/core/engine.py`: The heart of the system.
- `src/core/storage.py`: RClone abstraction.
- `src/core/catalog.py`: JSON-based backup tracking.
- `src/core/locking.py`: File-based locking to prevent concurrent runs.

### Modules
- **Qdrant**: Uses snapshot API for consistent vector database backups.
- **n8n**: Archives the data directory (local or LXC).
- **Home Assistant**: Archives configuration with exclude support.
- **MQTT/Zigbee2MQTT/Cloudflared**: Robust directory archiving.

## Installation

1. Clone the repository to `/opt/backup-server`.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your environment in `config/`:
   - `infra.env`: Host specific paths and rclone remotes.
   - `secrets.env`: Credentials and API keys.
   - `backup.yaml`: Backup policies and module options.

## Usage

### Run Backup
```bash
backup-cli backup --parallel
```

### Dry Run
```bash
backup-cli backup --dry-run
```

## Restore Procedure

1. Identify the artifact from the `catalog.json` or remote storage.
2. Download the artifact if necessary.
3. Run the module-specific restore command:
   ```bash
   backup-cli restore <module> <path-to-artifact>
   ```
   *(Note: CLI restore is currently a stub; manual extraction is recommended for critical recovery).*

## Testing

The system includes a comprehensive test suite:

- **Unit Tests**: `tests/unit/`
- **Integration Tests**: `tests/integration/`
- **E2E Tests**: `tests/e2e/`

Run tests with:
```bash
PYTHONPATH=. pytest
```

## Failure Modes & Handling

- **Disk Full**: The engine catches exceptions during backup and reports failure without updating the catalog.
- **Network Error**: RClone retries and engine error handling ensure partial uploads do not corrupt the catalog.
- **Corrupted Backup**: Checksum validation during the backup process ensures only healthy artifacts are promoted.
