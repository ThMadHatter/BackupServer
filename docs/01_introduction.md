# 🚀 1. Introduction & Prerequisites

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

[Back to Index](./README.md)
