#!/bin/bash
# Kindred offsite backup script
# Backs up the database and uploads to a remote server via rsync/scp.
#
# Usage:
#   1. Set BACKUP_REMOTE below (or pass as env var)
#   2. Add to crontab: 0 3 * * * /opt/kindred/deploy/backup-offsite.sh
#
# Requires: ssh key auth to remote server (no password prompts)

set -euo pipefail

KINDRED_DIR="${KINDRED_DIR:-/opt/kindred}"
BACKUP_DIR="${KINDRED_DIR}/backups"
BACKUP_REMOTE="${BACKUP_REMOTE:-}"  # e.g., user@backupserver:/backups/kindred/
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SNAPSHOT="${BACKUP_DIR}/kindred_${TIMESTAMP}.db"

# 1. Create a safe snapshot using SQLite backup API
sqlite3 "${KINDRED_DIR}/kindred.db" ".backup '${SNAPSHOT}'"
gzip "${SNAPSHOT}"

echo "[$(date)] Backup created: ${SNAPSHOT}.gz"

# 2. Push to remote if configured
if [ -n "${BACKUP_REMOTE}" ]; then
    rsync -az --timeout=30 "${SNAPSHOT}.gz" "${BACKUP_REMOTE}"
    echo "[$(date)] Backup pushed to ${BACKUP_REMOTE}"
fi

# 3. Clean up local backups older than 7 days
find "${BACKUP_DIR}" -name "kindred_*.db.gz" -mtime +7 -delete

echo "[$(date)] Backup complete"
