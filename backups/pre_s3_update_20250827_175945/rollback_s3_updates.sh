#!/bin/bash
# Rollback script for S3 URL updates
# Generated: 2025-08-27T17:59:45.977925
# Backup directory: backups/pre_s3_update_20250827_175945

echo "=== Rolling back S3 URL updates ==="

# Restore files from backup

echo "Restoring data/drive_link_strategy_analysis.json..."
cp "backups/pre_s3_update_20250827_175945/drive_link_strategy_analysis.json" "data/drive_link_strategy_analysis.json"

echo "Rollback completed"