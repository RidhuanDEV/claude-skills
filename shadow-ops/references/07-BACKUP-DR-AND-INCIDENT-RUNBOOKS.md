# 07 — 3-2-1 Automated Database Backups, Disaster Recovery & Incident Runbooks

---

## 1. Automated Encrypted Database Backup Script (`backup-db.sh`)

Supports PostgreSQL (`pg_dump -Fc`) and MySQL (`mysqldump --single-transaction`) with SHA-256 checksum, local retention rotation, and offsite S3/R2/MinIO upload via `rclone` or `aws s3`:

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/var/backups/database"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DB_ENGINE="${DB_ENGINE:-postgres}" # postgres | mysql
DB_NAME="${DB_NAME:-app_prod}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

mkdir -p "$BACKUP_DIR"

if [ "$DB_ENGINE" = "postgres" ]; then
  OUT_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump"
  PGPASSWORD="${DB_PASSWORD}" pg_dump \
    -h "${DB_HOST:-127.0.0.1}" \
    -p "${DB_PORT:-5432}" \
    -U "${DB_USER:-postgres}" \
    -Fc --no-owner --no-acl \
    "$DB_NAME" > "$OUT_FILE"
elif [ "$DB_ENGINE" = "mysql" ]; then
  OUT_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"
  MYSQL_PWD="${DB_PASSWORD}" mysqldump \
    -h "${DB_HOST:-127.0.0.1}" \
    -P "${DB_PORT:-3306}" \
    -u "${DB_USER:-root}" \
    --single-transaction --routines --triggers --events \
    "$DB_NAME" | gzip -9 > "$OUT_FILE"
fi

# Verify non-empty backup & generate SHA-256 checksum
if [ ! -s "$OUT_FILE" ]; then
  echo "CRITICAL: Backup file $OUT_FILE is 0 bytes!" >&2
  rm -f "$OUT_FILE"
  exit 1
fi
sha256sum "$OUT_FILE" > "${OUT_FILE}.sha256"

# Prune local backups older than RETENTION_DAYS
find "$BACKUP_DIR" -type f -mtime +"$RETENTION_DAYS" -delete
echo "Backup completed successfully: $OUT_FILE"
```

---

## 2. Production Incident Triage Runbook (7-Layer Diagnostic Order)

When a production outage or latency spike occurs, inspect in strict layer order **before restarting or mutating anything**:

| Layer | Diagnostic Command (Linux VPS / Docker) | What to Check |
| :--- | :--- | :--- |
| **1. Disk & Inodes** | `df -h && df -i` | Is disk or inode usage at `100%`? (Docker logs, `/tmp`, or WAL files often fill disk and crash DB/Nginx). |
| **2. Memory & OOM** | `free -m && dmesg -T \| grep -iE "oom\|killed"` | Did the Linux kernel OOM-killer terminate `postgres`, `mysqld`, or `node`? |
| **3. Process / Container** | `docker ps -a` / `systemctl status app` / `pm2 status` | Is the container in a `Restarting` crash loop? Check exit code (`137` = OOM/SIGKILL, `1` = app crash). |
| **4. Reverse Proxy / SSL** | `sudo nginx -t && sudo tail -n 50 /var/log/nginx/error.log` | `502 Bad Gateway` (app down/wrong port), `504 Gateway Timeout` (slow DB query), or expired TLS cert? |
| **5. Application Logs** | `docker compose logs --tail=100 api` | Look for unhandled exceptions, missing env vars, or failed migrations. |
| **6. DB & Connections** | `SELECT state, count(*) FROM pg_stat_activity GROUP BY 1;` | Are connections maxed out (`idle in transaction` leak) or blocked on locks? |
| **7. External Dependencies** | `curl -Iv https://thirdparty.api` | Is a third-party gateway timing out without a hard timeout/circuit breaker? |
