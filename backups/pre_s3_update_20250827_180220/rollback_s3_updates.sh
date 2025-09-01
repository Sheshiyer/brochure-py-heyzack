#!/bin/bash
# Rollback script for S3 URL updates
# Generated: 2025-08-27T18:02:20.119474
# Backup directory: backups/pre_s3_update_20250827_180220

echo "=== Rolling back S3 URL updates ==="

# Restore files from backup

echo "Restoring data/full_catalog_strategy_analysis.json..."
cp "backups/pre_s3_update_20250827_180220/full_catalog_strategy_analysis.json" "data/full_catalog_strategy_analysis.json"

echo "Rollback completed"