#!/usr/bin/env bash
set -euo pipefail

# Daily backup for MySQL using env from backend/.env and backend/.env.local
# - Creates gzipped dump file in ../../backups
# - Retains last N backups (configurable)
# - Logs to stdout

# Config
RETENTION_DAYS=${RETENTION_DAYS:-7}
BACKUP_ROOT_DIR="$(cd "$(dirname "$0")"/../.. && pwd)/backups"
DATE_TS=$(date +%Y%m%d-%H%M%S)

# Load env from files safely (supports spaces and special chars in values)
ENV_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
load_env_file() {
  local f="$1"
  [ -f "$f" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    # Skip comments/blank
    [[ -z "$line" || "$line" =~ ^\s*# ]] && continue
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      local key="${BASH_REMATCH[1]}"
      local val="${BASH_REMATCH[2]}"
      # Trim surrounding quotes if present
      if [[ "$val" =~ ^\".*\"$ ]]; then val="${val:1:-1}"; fi
      if [[ "$val" =~ ^\'.*\'$ ]]; then val="${val:1:-1}"; fi
      # Assign safely preserving spaces/specials
      printf -v "$key" '%s' "$val"
      export "$key"
    fi
  done < "$f"
}
# Load base (remote) first and snapshot as REMOTE_*
load_env_file "$ENV_DIR/.env"
REMOTE_MYSQL_HOST=${MYSQL_HOST:-}
REMOTE_MYSQL_PORT=${MYSQL_PORT:-3306}
REMOTE_MYSQL_USER=${MYSQL_USER:-}
REMOTE_MYSQL_PASSWORD=${MYSQL_PASSWORD:-}
REMOTE_MYSQL_DATABASE=${MYSQL_DATABASE:-aspma}
# Then load local overrides for MYSQL_*
load_env_file "$ENV_DIR/.env.local"

# Choose source: default to remote (if available), can override with BACKUP_SOURCE=local/remote
BACKUP_SOURCE=${BACKUP_SOURCE:-remote}
if [ "$BACKUP_SOURCE" = "local" ]; then
  SRC_HOST=${MYSQL_HOST:-127.0.0.1}
  SRC_PORT=${MYSQL_PORT:-3306}
  SRC_USER=${MYSQL_USER:-root}
  SRC_PASS=${MYSQL_PASSWORD:-}
  SRC_DB=${MYSQL_DATABASE:-aspma}
  BACKUP_NAME_PREFIX=${BACKUP_NAME_PREFIX:-"aspma-local"}
else
  if [ -n "${REMOTE_MYSQL_HOST:-}" ]; then
    SRC_HOST=${REMOTE_MYSQL_HOST}
    SRC_PORT=${REMOTE_MYSQL_PORT:-3306}
    SRC_USER=${REMOTE_MYSQL_USER}
    SRC_PASS=${REMOTE_MYSQL_PASSWORD:-}
    SRC_DB=${REMOTE_MYSQL_DATABASE:-aspma}
    BACKUP_NAME_PREFIX=${BACKUP_NAME_PREFIX:-"aspma-remote"}
  else
    SRC_HOST=${MYSQL_HOST:-127.0.0.1}
    SRC_PORT=${MYSQL_PORT:-3306}
    SRC_USER=${MYSQL_USER:-root}
    SRC_PASS=${MYSQL_PASSWORD:-}
    SRC_DB=${MYSQL_DATABASE:-aspma}
    BACKUP_NAME_PREFIX=${BACKUP_NAME_PREFIX:-"aspma-local"}
  fi
fi

mkdir -p "$BACKUP_ROOT_DIR"
OUT_FILE="$BACKUP_ROOT_DIR/${BACKUP_NAME_PREFIX}-${DATE_TS}.sql.gz"

echo "Backing up $SRC_DB@$SRC_HOST:$SRC_PORT to $OUT_FILE"

# Perform dump
if [ -z "${SRC_PASS:-}" ]; then
  mysqldump -h "$SRC_HOST" -P "$SRC_PORT" -u "$SRC_USER" --single-transaction --quick \
    --routines --triggers --events --set-gtid-purged=OFF --default-character-set=utf8mb4 \
    "$SRC_DB" | gzip > "$OUT_FILE"
else
  mysqldump -h "$SRC_HOST" -P "$SRC_PORT" -u "$SRC_USER" --password="$SRC_PASS" \
    --single-transaction --quick --routines --triggers --events --set-gtid-purged=OFF \
    --default-character-set=utf8mb4 "$SRC_DB" | gzip > "$OUT_FILE"
fi

# Print result
ls -lh "$OUT_FILE"

# Retention: delete files older than N days
find "$BACKUP_ROOT_DIR" -type f -name "${BACKUP_NAME_PREFIX}-*.sql.gz" -mtime +$RETENTION_DAYS -print -delete || true
