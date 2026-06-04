# 📦 3. Container Backup Guide

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

[Back to Index](./README.md)
