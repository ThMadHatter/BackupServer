# 📊 5. Grafana Monitoring Integration

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

[Back to Index](./README.md)
