#!/bin/bash
# Rollback script for S3 URL updates
# Generated: 2025-08-27T18:00:38.495401
# Backup directory: backups/pre_s3_update_20250827_180038

echo "=== Rolling back S3 URL updates ==="

# Restore files from backup

echo "Restoring data/s3_migration_plan.json..."
cp "backups/pre_s3_update_20250827_180038/s3_migration_plan.json" "data/s3_migration_plan.json"

echo "Rollback completed"