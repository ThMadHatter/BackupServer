# 🔄 4. Container Restore Procedures

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

[Back to Index](./README.md)
