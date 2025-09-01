#!/bin/bash
# Rollback script for S3 URL updates
# Generated: 2025-08-27T17:56:41.347535
# Backup directory: backups/pre_s3_update_20250827_175641

echo "=== Rolling back S3 URL updates ==="

# Restore files from backup

echo "Restoring data/products.json..."
cp "backups/pre_s3_update_20250827_175641/products.json" "data/products.json"

echo "Restoring data/products_hierarchical_enhanced.json..."
cp "backups/pre_s3_update_20250827_175641/products_hierarchical_enhanced.json" "data/products_hierarchical_enhanced.json"

echo "Restoring data/SMART HOME FOLLOWING PROJECT - All Products.csv..."
cp "backups/pre_s3_update_20250827_175641/SMART HOME FOLLOWING PROJECT - All Products.csv" "data/SMART HOME FOLLOWING PROJECT - All Products.csv"

echo "Rollback completed"