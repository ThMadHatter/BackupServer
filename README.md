# Homelab Modular Backup System (Evolution)

This is the next evolution of the backup system, transformed into a **self-describing, declarative backup orchestration platform**.

## 🏗️ Architecture

The system is now driven by a declarative engine that interprets YAML specifications. This eliminates the need for custom Python code when adding new services.

### Components

- **Engine**: The core runner that parses YAML specs, builds an execution plan, and executes primitives.
- **Primitives**: Reusable building blocks for network, filesystem, LXC, and storage operations.
- **Specs**: YAML files defining how each service should be backed up and restored.
- **Catalog**: A SQLite-based system to track all backup runs, artifacts, and checksums.

## 🚀 Why Declarative?

1.  **No Code for New Services**: Adding a new service only requires writing a YAML spec.
2.  **Consistency**: All services use the same set of well-tested primitives.
3.  **Transparency**: The backup process is explicitly defined in a human-readable format.
4.  **Flexibility**: Primitives can be composed in any order to support complex workflows.

## 🛠️ How to Add a New Service

1.  Create a new YAML file in the `specs/` directory (e.g., `specs/my_service.yaml`).
2.  Define the `backup` steps using available primitives:
    - `http_get`, `http_post`, `http_download`
    - `tar`, `copy`, `compress`, `checksum`
    - `pct_exec`
    - `rclone_upload`
3.  Use `{{ variable }}` syntax for dynamic values (context variables like `timestamp` and `run_id` are automatically provided).
4.  Optionally define `restore` and `validation` steps.

Example:
```yaml
name: simple_service
backup:
  - name: download_data
    type: http_download
    options:
      url: "http://api.example.com/export"
      dest_path: "/tmp/data.bin"
  - name: upload_to_cloud
    type: rclone_upload
    options:
      local_path: "/tmp/data.bin"
      remote_name: "gdrive"
      remote_path: "backups/simple/{{ timestamp }}.bin"
```

## 📋 Failure Modes & Safety

- **Retries**: Steps can define a `retry` count with exponential backoff.
- **Timeouts**: (Coming soon) Steps can have execution timeouts.
- **Dry-run**: Always use `--dry-run` to verify your spec without side effects.
- **Integrity**: Use the `checksum` primitive and catalog to ensure backup integrity.

## 🔄 Restore Procedure

To restore a service:
```bash
backup-cli restore <service_name> --version latest
```
This will lookup the latest artifact in the catalog, download it, and execute the `restore` steps defined in the service spec.

## 🧪 Testing

Run tests using:
```bash
export PYTHONPATH=.
pytest tests/
```
Tests include unit tests for primitives, integration tests for engine logic, and E2E tests for full spec execution.
