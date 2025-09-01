#!/usr/bin/env python3
"""
Update Data Sources with S3 URLs

Updates all data sources (JSON files, CSV) to replace Google Drive links with S3 URLs
after successful migration.
"""

import json
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import shutil

class DataSourceUpdater:
    """
    Updates data sources with S3 URLs after migration.
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.update_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_dir = self.project_root / "backups" / f"pre_s3_update_{self.update_timestamp}"
        
    def load_migration_results(self) -> Optional[Dict[str, Any]]:
        """
        Load the latest S3 migration results.
        """
        reports_dir = self.project_root / "reports"
        
        # Find the latest migration results file
        migration_files = list(reports_dir.glob("s3_migration_results_*.json"))
        
        if not migration_files:
            print("❌ No S3 migration results found")
            return None
        
        # Get the most recent file
        latest_file = max(migration_files, key=lambda f: f.stat().st_mtime)
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            print(f"✅ Loaded migration results: {latest_file.name}")
            print(f"   Successful migrations: {results['successful_migrations']}")
            print(f"   Failed migrations: {results['failed_migrations']}")
            
            return results
            
        except Exception as e:
            print(f"❌ Failed to load migration results: {e}")
            return None
    
    def create_backup(self, file_path: Path) -> bool:
        """
        Create backup of file before modification.
        """
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = self.backup_dir / file_path.name
            shutil.copy2(file_path, backup_path)
            return True
        except Exception as e:
            print(f"❌ Failed to backup {file_path}: {e}")
            return False
    
    def update_json_file(self, file_path: Path, url_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Update JSON file with S3 URLs.
        Returns update statistics.
        """
        stats = {
            "file": str(file_path),
            "updates_made": 0,
            "errors": []
        }
        
        try:
            # Load JSON data
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create backup
            if not self.create_backup(file_path):
                stats["errors"].append("Failed to create backup")
                return stats
            
            # Update URLs recursively
            def update_urls_recursive(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key
                        
                        if isinstance(value, str) and value in url_mapping:
                            obj[key] = url_mapping[value]
                            stats["updates_made"] += 1
                            print(f"    Updated {current_path}: {value[:50]}... -> S3")
                        else:
                            update_urls_recursive(value, current_path)
                            
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        update_urls_recursive(item, f"{path}[{i}]")
            
            # Perform updates
            update_urls_recursive(data)
            
            # Save updated data
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"  ✅ Updated {file_path.name}: {stats['updates_made']} URLs")
            
        except Exception as e:
            error_msg = f"Failed to update {file_path}: {e}"
            stats["errors"].append(error_msg)
            print(f"  ❌ {error_msg}")
        
        return stats
    
    def update_csv_file(self, file_path: Path, url_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Update CSV file with S3 URLs.
        Returns update statistics.
        """
        stats = {
            "file": str(file_path),
            "updates_made": 0,
            "errors": []
        }
        
        try:
            # Create backup
            if not self.create_backup(file_path):
                stats["errors"].append("Failed to create backup")
                return stats
            
            # Read CSV data
            rows = []
            with open(file_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                
                for row in reader:
                    # Update Drive Link column if it exists
                    if 'Drive Link' in row and row['Drive Link'] in url_mapping:
                        old_url = row['Drive Link']
                        row['Drive Link'] = url_mapping[old_url]
                        stats["updates_made"] += 1
                        print(f"    Updated CSV row: {old_url[:50]}... -> S3")
                    
                    rows.append(row)
            
            # Write updated CSV
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                if headers:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(rows)
            
            print(f"  ✅ Updated {file_path.name}: {stats['updates_made']} URLs")
            
        except Exception as e:
            error_msg = f"Failed to update {file_path}: {e}"
            stats["errors"].append(error_msg)
            print(f"  ❌ {error_msg}")
        
        return stats
    
    def update_all_data_sources(self, migration_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update all data sources with S3 URLs.
        """
        print("\n=== Updating Data Sources with S3 URLs ===")
        
        # Extract URL mapping from migration results
        url_mapping = migration_results.get('s3_urls', {})
        
        if not url_mapping:
            print("❌ No S3 URL mappings found in migration results")
            return {"error": "No URL mappings available"}
        
        print(f"📋 Found {len(url_mapping)} URL mappings to apply")
        
        update_summary = {
            "timestamp": datetime.now().isoformat(),
            "total_mappings": len(url_mapping),
            "files_updated": [],
            "total_updates": 0,
            "errors": []
        }
        
        # Define files to update
        files_to_update = [
            # JSON files
            self.project_root / "data" / "products.json",
            self.project_root / "data" / "products_hierarchical_enhanced.json",
            self.project_root / "data" / "drive_link_strategy_analysis.json",
            self.project_root / "data" / "s3_migration_plan.json",
            self.project_root / "data" / "metadata_enhancement_analysis.json",
            self.project_root / "data" / "full_catalog_strategy_analysis.json",
            
            # CSV files
            self.project_root / "data" / "SMART HOME FOLLOWING PROJECT - All Products.csv"
        ]
        
        # Update each file
        for file_path in files_to_update:
            if not file_path.exists():
                print(f"⚠️  File not found: {file_path}")
                continue
            
            print(f"\n📝 Updating: {file_path.name}")
            
            if file_path.suffix.lower() == '.json':
                stats = self.update_json_file(file_path, url_mapping)
            elif file_path.suffix.lower() == '.csv':
                stats = self.update_csv_file(file_path, url_mapping)
            else:
                print(f"  ⚠️  Unsupported file type: {file_path.suffix}")
                continue
            
            update_summary["files_updated"].append(stats)
            update_summary["total_updates"] += stats["updates_made"]
            
            if stats["errors"]:
                update_summary["errors"].extend(stats["errors"])
        
        return update_summary
    
    def create_rollback_script(self, update_summary: Dict[str, Any]) -> str:
        """
        Create a rollback script to restore original files.
        """
        rollback_script = f"""#!/bin/bash
# Rollback script for S3 URL updates
# Generated: {datetime.now().isoformat()}
# Backup directory: {self.backup_dir}

echo "=== Rolling back S3 URL updates ==="

# Restore files from backup
"""
        
        for file_stats in update_summary.get("files_updated", []):
            if file_stats["updates_made"] > 0:
                original_file = file_stats["file"]
                backup_file = self.backup_dir / Path(original_file).name
                
                rollback_script += f"""\necho "Restoring {original_file}..."
cp "{backup_file}" "{original_file}"
"""
        
        rollback_script += "\necho \"Rollback completed\""
        
        # Save rollback script
        rollback_path = self.backup_dir / "rollback_s3_updates.sh"
        rollback_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(rollback_path, 'w') as f:
            f.write(rollback_script)
        
        # Make executable
        os.chmod(rollback_path, 0o755)
        
        return str(rollback_path)
    
    def save_update_summary(self, update_summary: Dict[str, Any]) -> str:
        """
        Save update summary to file.
        """
        summary_path = self.project_root / "reports" / f"s3_url_updates_{self.update_timestamp}.json"
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(update_summary, f, indent=2, ensure_ascii=False)
        
        return str(summary_path)

def main():
    """
    Main function to update data sources with S3 URLs.
    """
    try:
        print("=== Data Source S3 URL Updater ===")
        
        # Initialize updater
        updater = DataSourceUpdater()
        
        # Load migration results
        migration_results = updater.load_migration_results()
        if not migration_results:
            return 1
        
        # Check if migration was successful
        if migration_results.get('successful_migrations', 0) == 0:
            print("❌ No successful migrations found. Nothing to update.")
            return 1
        
        # Update all data sources
        update_summary = updater.update_all_data_sources(migration_results)
        
        if "error" in update_summary:
            print(f"❌ Update failed: {update_summary['error']}")
            return 1
        
        # Create rollback script
        rollback_script = updater.create_rollback_script(update_summary)
        
        # Save update summary
        summary_path = updater.save_update_summary(update_summary)
        
        # Final summary
        print("\n=== Update Summary ===")
        print(f"📊 Total URL mappings: {update_summary['total_mappings']}")
        print(f"✅ Total updates made: {update_summary['total_updates']}")
        print(f"📁 Files updated: {len(update_summary['files_updated'])}")
        
        if update_summary['errors']:
            print(f"⚠️  Errors encountered: {len(update_summary['errors'])}")
            for error in update_summary['errors']:
                print(f"   - {error}")
        
        print(f"\n📋 Update summary: {summary_path}")
        print(f"🔄 Rollback script: {rollback_script}")
        print(f"💾 Backups stored: {updater.backup_dir}")
        
        if update_summary['total_updates'] > 0:
            print("\n🎉 Data sources successfully updated with S3 URLs!")
            print("\n📝 Next steps:")
            print("   1. Test the application with new S3 URLs")
            print("   2. Verify images are loading correctly")
            print("   3. Update Google Sheets if needed")
        else:
            print("\n⚠️  No updates were made. Check if URLs match migration results.")
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())