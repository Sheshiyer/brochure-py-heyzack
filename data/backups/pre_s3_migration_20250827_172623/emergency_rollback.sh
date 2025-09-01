#!/bin/bash
# Emergency Rollback Script
# Generated: 2025-08-27T17:26:23.645248
# Backup Directory: data/backups/pre_s3_migration_20250827_172623

echo "🔄 Starting emergency rollback..."

# Stop any running processes
echo "Stopping any running processes..."
pkill -f "python.*brochure" || true

# Restore critical files
echo "Restoring files from backup..."
if [ -f "data/backups/pre_s3_migration_20250827_172623/products_hierarchical_enhanced.json" ]; then
    cp "data/backups/pre_s3_migration_20250827_172623/products_hierarchical_enhanced.json" "data/products_hierarchical_enhanced.json"
    echo "✅ Restored: data/products_hierarchical_enhanced.json"
else
    echo "❌ Backup not found: data/backups/pre_s3_migration_20250827_172623/products_hierarchical_enhanced.json"
fi

if [ -f "data/backups/pre_s3_migration_20250827_172623/products.json" ]; then
    cp "data/backups/pre_s3_migration_20250827_172623/products.json" "data/products.json"
    echo "✅ Restored: data/products.json"
else
    echo "❌ Backup not found: data/backups/pre_s3_migration_20250827_172623/products.json"
fi

echo "🔄 Rollback completed!"
echo "⚠️  Please verify data integrity and regenerate brochures if needed."
