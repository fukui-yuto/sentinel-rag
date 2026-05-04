#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Sentinel RAG - Restore Script
# =============================================================================
# Usage: ./scripts/restore.sh <backup_path>
# Restores from a backup created by backup.sh

BACKUP_PATH="${1:?Usage: restore.sh <backup_path>}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"

# If encrypted, decrypt first
if [[ "${BACKUP_PATH}" == *.enc ]]; then
    if [ -z "${ENCRYPTION_KEY}" ]; then
        echo "ERROR: BACKUP_ENCRYPTION_KEY required for encrypted backups"
        exit 1
    fi
    DECRYPTED="/tmp/sentinel_restore_$(date +%s)"
    mkdir -p "${DECRYPTED}"
    openssl enc -d -aes-256-cbc -pbkdf2 -pass "pass:${ENCRYPTION_KEY}" \
        -in "${BACKUP_PATH}" | tar xzf - -C "${DECRYPTED}"
    BACKUP_PATH="${DECRYPTED}/$(ls "${DECRYPTED}" | head -1)"
fi

echo "[$(date)] Restoring from: ${BACKUP_PATH}"

# --- Stop services ---
echo "[$(date)] Stopping application services..."
docker compose stop api worker beat

# --- PostgreSQL ---
if [ -f "${BACKUP_PATH}/postgres_full.sql.gz" ]; then
    echo "[$(date)] Restoring PostgreSQL..."
    gunzip -c "${BACKUP_PATH}/postgres_full.sql.gz" \
        | docker exec -i sentinel-postgres psql -U "${POSTGRES_USER:-sentinel}"
fi

# --- Redis ---
if [ -f "${BACKUP_PATH}/redis_dump.rdb" ]; then
    echo "[$(date)] Restoring Redis..."
    docker exec sentinel-redis redis-cli -a "${REDIS_PASSWORD:-}" SHUTDOWN NOSAVE || true
    docker cp "${BACKUP_PATH}/redis_dump.rdb" sentinel-redis:/data/dump.rdb
    docker compose restart redis
fi

# --- Start services ---
echo "[$(date)] Starting services..."
docker compose up -d api worker beat

echo "[$(date)] Restore completed. Please verify system health."
echo "  curl https://localhost/api/v1/health/ready"
