#!/usr/bin/env bash
# Backup the matrix_bridge schema from the project-001 Postgres instance.
# Writes a timestamped dump to /srv/claude-matrix/backups/.
#
# Usage:
#   ./backup.sh
#
# Environment (or set in /etc/environment / systemd unit):
#   DATABASE_URL   — postgres connection string (required)
#   BACKUP_DIR     — destination directory (default: /srv/claude-matrix/backups)
#   RETENTION_DAYS — how many days of backups to keep (default: 14)
#
# Example cron (daily at 03:00):
#   0 3 * * * /home/ppowell/project-001/infra/matrix/backup.sh >> /var/log/matrix-bridge-backup.log 2>&1

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/srv/claude-matrix/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
OUTFILE="${BACKUP_DIR}/matrix_bridge_${TIMESTAMP}.sql.gz"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL is not set" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting backup → ${OUTFILE}"

pg_dump \
  --schema=matrix_bridge \
  --no-owner \
  --no-privileges \
  "${DATABASE_URL}" \
  | gzip -9 > "${OUTFILE}"

SIZE=$(du -sh "${OUTFILE}" | cut -f1)
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Backup complete: ${OUTFILE} (${SIZE})"

# Remove backups older than RETENTION_DAYS
find "${BACKUP_DIR}" -name "matrix_bridge_*.sql.gz" -mtime +"${RETENTION_DAYS}" -delete
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Pruned backups older than ${RETENTION_DAYS} days"
