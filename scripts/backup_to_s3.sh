#!/usr/bin/env bash
# ==============================================================================
# PharmaBack Cloud Disaster Recovery: Automated Backup to Amazon S3
# Architecture: Contabo Primary -> Encrypted S3 Bucket (Zero Secret Leakage)
# ==============================================================================

set -eo pipefail

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${BACKUP_DIR:-/tmp/pharmaback_backups}"
S3_BUCKET="${AWS_S3_BACKUP_BUCKET:-pharmaback-disaster-recovery-backups}"
S3_PREFIX="${S3_PREFIX:-backups}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-$(docker ps --filter "name=postgres" --format "{{.ID}}" | head -n 1)}"
DB_NAME="${DB_NAME:-pharmaback_prod}"
DB_USER="${DB_USER:-postgres}"

mkdir -p "$BACKUP_DIR"

echo "============================================================"
echo "🕒 [${TIMESTAMP}] Starting PharmaBack Automated Backup to S3"
echo "============================================================"

if [ -z "$POSTGRES_CONTAINER" ]; then
    echo "❌ ERROR: PostgreSQL Docker container not found."
    exit 1
fi

DUMP_FILENAME="pharmaback_${TIMESTAMP}.dump"
DUMP_PATH="${BACKUP_DIR}/${DUMP_FILENAME}"
ENCRYPTED_PATH="${DUMP_PATH}.enc"

# 1. Generate Compressed PostgreSQL Custom Binary Dump
echo "🐘 Dumping PostgreSQL database '${DB_NAME}' from container '${POSTGRES_CONTAINER}'..."
docker exec -i "$POSTGRES_CONTAINER" pg_dump \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-acl \
    -F c \
    -b \
    -v > "$DUMP_PATH"

DUMP_SIZE=$(du -sh "$DUMP_PATH" | awk '{print $1}')
echo "✅ Database dump successful! Size: ${DUMP_SIZE}"

# 2. Client-Side Encryption (Zero-Knowledge / Zero-Leakage)
if [ -n "$BACKUP_ENCRYPTION_PASSPHRASE" ]; then
    echo "🔒 Encrypting backup file with AES-256..."
    openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
        -in "$DUMP_PATH" \
        -out "$ENCRYPTED_PATH" \
        -pass env:BACKUP_ENCRYPTION_PASSPHRASE
    UPLOAD_FILE="$ENCRYPTED_PATH"
    UPLOAD_FILENAME="${DUMP_FILENAME}.enc"
else
    UPLOAD_FILE="$DUMP_PATH"
    UPLOAD_FILENAME="$DUMP_FILENAME"
fi

# 3. Upload to Amazon S3 (Encrypted Storage + Glacier Lifecycle)
echo "☁️ Uploading to Amazon S3 bucket 's3://${S3_BUCKET}/${S3_PREFIX}/database/${UPLOAD_FILENAME}'..."
aws s3 cp "$UPLOAD_FILE" "s3://${S3_BUCKET}/${S3_PREFIX}/database/${UPLOAD_FILENAME}" \
    --sse AES256 \
    --storage-class STANDARD_IA

# Maintain latest pointer for fast automated recovery
aws s3 cp "$UPLOAD_FILE" "s3://${S3_BUCKET}/${S3_PREFIX}/database/latest.dump.enc" \
    --sse AES256

echo "✅ Database backup successfully uploaded to S3!"

# 4. Sync User Media / Receipts to S3
if [ -d "/app/media" ] || [ -d "/var/lib/docker/volumes/pharmaback_media_volume/_data" ]; then
    MEDIA_DIR="${MEDIA_DIR:-/var/lib/docker/volumes/pharmaback_media_volume/_data}"
    if [ -d "$MEDIA_DIR" ]; then
        echo "📂 Syncing Media files to S3..."
        aws s3 sync "$MEDIA_DIR" "s3://${S3_BUCKET}/${S3_PREFIX}/media/" \
            --sse AES256 \
            --delete
        echo "✅ Media files sync completed!"
    fi
fi

# 5. Cleanup local temp files
rm -f "$DUMP_PATH" "$ENCRYPTED_PATH"

echo "============================================================"
echo "🎉 Disaster Recovery Backup to S3 Finished Successfully!"
echo "============================================================"
