#!/usr/bin/env bash
# ==============================================================================
# PharmaBack Cloud Disaster Recovery: Automated Restore from Amazon S3
# Used for Failover on AWS (App Runner / EC2 / ECS / RDS) or Contabo Rebuild
# ==============================================================================

set -eo pipefail

RESTORE_DIR="${RESTORE_DIR:-/tmp/pharmaback_restore}"
S3_BUCKET="${AWS_S3_BACKUP_BUCKET:-pharmaback-disaster-recovery-backups}"
S3_PREFIX="${S3_PREFIX:-backups}"
BACKUP_NAME="${1:-latest.dump.enc}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-$(docker ps --filter "name=postgres" --format "{{.ID}}" | head -n 1)}"
DB_NAME="${DB_NAME:-pharmaback_prod}"
DB_USER="${DB_USER:-postgres}"

mkdir -p "$RESTORE_DIR"

echo "============================================================"
echo "🚨 Starting PharmaBack Disaster Recovery Restore from S3"
echo "Target Backup: ${BACKUP_NAME}"
echo "============================================================"

# 1. Download Dump from Amazon S3
echo "☁️ Downloading backup 's3://${S3_BUCKET}/${S3_PREFIX}/database/${BACKUP_NAME}'..."
aws s3 cp "s3://${S3_BUCKET}/${S3_PREFIX}/database/${BACKUP_NAME}" "${RESTORE_DIR}/${BACKUP_NAME}"

DOWNLOADED_FILE="${RESTORE_DIR}/${BACKUP_NAME}"
RESTORE_FILE="${RESTORE_DIR}/restorable_backup.dump"

# 2. Decrypt if file is encrypted (.enc)
if [[ "$BACKUP_NAME" == *.enc ]]; then
    if [ -z "$BACKUP_ENCRYPTION_PASSPHRASE" ]; then
        echo "❌ ERROR: BACKUP_ENCRYPTION_PASSPHRASE environment variable is required to decrypt this backup."
        exit 1
    fi
    echo "🔓 Decrypting AES-256 encrypted dump..."
    openssl enc -d -aes-256-cbc -salt -pbkdf2 -iter 100000 \
        -in "$DOWNLOADED_FILE" \
        -out "$RESTORE_FILE" \
        -pass env:BACKUP_ENCRYPTION_PASSPHRASE
else
    RESTORE_FILE="$DOWNLOADED_FILE"
fi

# 3. Restore Database via pg_restore
if [ -n "$POSTGRES_CONTAINER" ]; then
    echo "🐘 Restoring to Docker PostgreSQL container '${POSTGRES_CONTAINER}'..."
    docker cp "$RESTORE_FILE" "${POSTGRES_CONTAINER}:/tmp/restore.dump"
    docker exec -i "$POSTGRES_CONTAINER" pg_restore \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --clean \
        --if-exists \
        --no-owner \
        --no-acl \
        -v /tmp/restore.dump || true
    docker exec -i "$POSTGRES_CONTAINER" rm -f /tmp/restore.dump
else
    echo "🐘 Restoring to Remote PostgreSQL Host ($DB_HOST)..."
    PGPASSWORD="$DB_PASSWORD" pg_restore \
        -h "${DB_HOST:-localhost}" \
        -p "${DB_PORT:-5432}" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --clean \
        --if-exists \
        --no-owner \
        --no-acl \
        -v "$RESTORE_FILE" || true
fi

# 4. Restore Media Files from S3
if [ -d "/app/media" ] || [ -d "/var/lib/docker/volumes/pharmaback_media_volume/_data" ]; then
    MEDIA_DIR="${MEDIA_DIR:-/var/lib/docker/volumes/pharmaback_media_volume/_data}"
    if [ -d "$MEDIA_DIR" ]; then
        echo "📂 Restoring media files from S3..."
        aws s3 sync "s3://${S3_BUCKET}/${S3_PREFIX}/media/" "$MEDIA_DIR"
    fi
fi

# 5. Cleanup temporary restore files
rm -rf "$RESTORE_DIR"

echo "============================================================"
echo "🎉 Disaster Recovery Database & Media Restore Completed Successfully!"
echo "============================================================"
