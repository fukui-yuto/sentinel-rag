#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Sentinel RAG - Backup Script
# =============================================================================
# Usage: ./scripts/backup.sh [--full|--incremental]
# Runs daily via cron. Creates encrypted backups of all data stores.

BACKUP_DIR="${BACKUP_NAS_PATH:-/opt/sentinel-rag/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/${TIMESTAMP}"
ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"

mkdir -p "${BACKUP_PATH}"

echo "[$(date)] Starting backup..."

# --- PostgreSQL ---
echo "[$(date)] Backing up PostgreSQL..."
docker exec sentinel-postgres pg_dumpall \
    -U "${POSTGRES_USER:-sentinel}" \
    --clean --if-exists \
    | gzip > "${BACKUP_PATH}/postgres_full.sql.gz"

# --- Qdrant ---
echo "[$(date)] Backing up Qdrant snapshots..."
docker exec sentinel-qdrant curl -s -X POST http://localhost:6333/snapshots
sleep 5
docker cp sentinel-qdrant:/qdrant/storage/snapshots/ "${BACKUP_PATH}/qdrant_snapshots/" 2>/dev/null || true

# --- MinIO ---
echo "[$(date)] Backing up MinIO..."
docker run --rm --network sentinel-data \
    -v "${BACKUP_PATH}/minio:/backup" \
    minio/mc:latest \
    mirror --overwrite "http://minio:9000" /backup/ 2>/dev/null || {
    echo "[$(date)] MinIO backup via mc failed, falling back to volume copy"
    docker cp sentinel-minio:/data/ "${BACKUP_PATH}/minio/" 2>/dev/null || true
}

# --- Redis ---
echo "[$(date)] Backing up Redis..."
docker exec sentinel-redis redis-cli -a "${REDIS_PASSWORD:-}" BGSAVE
sleep 3
docker cp sentinel-redis:/data/dump.rdb "${BACKUP_PATH}/redis_dump.rdb" 2>/dev/null || true

# --- Config ---
echo "[$(date)] Backing up config..."
cp -r /opt/sentinel-rag/config/ "${BACKUP_PATH}/config/" 2>/dev/null || true

# --- Encrypt ---
if [ -n "${ENCRYPTION_KEY}" ]; then
    echo "[$(date)] Encrypting backup..."
    tar czf - -C "${BACKUP_DIR}" "${TIMESTAMP}" \
        | openssl enc -aes-256-cbc -salt -pbkdf2 -pass "pass:${ENCRYPTION_KEY}" \
        > "${BACKUP_DIR}/${TIMESTAMP}.tar.gz.enc"
    rm -rf "${BACKUP_PATH}"
    echo "[$(date)] Encrypted backup: ${BACKUP_DIR}/${TIMESTAMP}.tar.gz.enc"
fi

# --- Cleanup old backups (keep 90 days) ---
find "${BACKUP_DIR}" -maxdepth 1 -mtime +90 -exec rm -rf {} \;

echo "[$(date)] Backup completed."
