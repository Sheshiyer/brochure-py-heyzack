#!/usr/bin/env python3
"""
Data Validation and Backup System

Provides comprehensive backup and validation before any data modifications.
Ensures data integrity and provides rollback capabilities.
"""

import json
import os
import shutil
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

class DataValidationBackup:
    """
    Handles data validation, backup creation, and integrity verification.
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_dir = self.project_root / "data" / "backups" / f"pre_s3_migration_{self.backup_timestamp}"
        
    def calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of a file for integrity verification.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def create_backup_directory(self) -> bool:
        """
        Create backup directory structure.
        """
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created backup directory: {self.backup_dir}")
            return True
        except Exception as e:
            print(f"❌ Failed to create backup directory: {e}")
            return False
    
    def backup_critical_files(self) -> Dict[str, Any]:
        """
        Backup all critical data files with integrity verification.
        """
        critical_files = [
            "data/products_hierarchical_enhanced.json",
            "data/products.json",
            "data/SMART HOME FOLLOWING PROJECT - All Products.csv",
            "reports/google_sheets_analysis.json",
            "reports/s3_migration_plan.json"
        ]
        
        backup_manifest = {
            "timestamp": self.backup_timestamp,
            "backup_directory": str(self.backup_dir),
            "files_backed_up": [],
            "integrity_hashes": {},
            "backup_success": True,
            "errors": []
        }
        
        print("\n=== Creating Backups ===")
        
        for file_path in critical_files:
            source_path = self.project_root / file_path
            
            if not source_path.exists():
                print(f"⚠️  File not found: {file_path}")
                backup_manifest["errors"].append(f"File not found: {file_path}")
                continue
            
            try:
                # Calculate original file hash
                original_hash = self.calculate_file_hash(source_path)
                
                # Create backup
                backup_file_path = self.backup_dir / source_path.name
                shutil.copy2(source_path, backup_file_path)
                
                # Verify backup integrity
                backup_hash = self.calculate_file_hash(backup_file_path)
                
                if original_hash == backup_hash:
                    print(f"✅ Backed up: {file_path}")
                    backup_manifest["files_backed_up"].append(file_path)
                    backup_manifest["integrity_hashes"][file_path] = original_hash
                else:
                    print(f"❌ Backup integrity failed: {file_path}")
                    backup_manifest["backup_success"] = False
                    backup_manifest["errors"].append(f"Integrity check failed: {file_path}")
                    
            except Exception as e:
                print(f"❌ Failed to backup {file_path}: {e}")
                backup_manifest["backup_success"] = False
                backup_manifest["errors"].append(f"Backup failed for {file_path}: {str(e)}")
        
        # Save backup manifest
        manifest_path = self.backup_dir / "backup_manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(backup_manifest, f, indent=2, ensure_ascii=False)
        
        return backup_manifest
    
    def validate_data_consistency(self) -> Dict[str, Any]:
        """
        Validate consistency between different data sources.
        """
        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "validations": {},
            "overall_status": "PASS",
            "warnings": [],
            "errors": []
        }
        
        print("\n=== Data Consistency Validation ===")
        
        # Validate JSON files exist and are readable
        json_files = [
            "data/products_hierarchical_enhanced.json",
            "data/products.json",
            "reports/google_sheets_analysis.json"
        ]
        
        for json_file in json_files:
            file_path = self.project_root / json_file
            validation_name = f"json_validity_{Path(json_file).stem}"
            
            try:
                if not file_path.exists():
                    validation_results["validations"][validation_name] = "FAIL"
                    validation_results["errors"].append(f"File not found: {json_file}")
                    validation_results["overall_status"] = "FAIL"
                    continue
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                validation_results["validations"][validation_name] = "PASS"
                print(f"✅ Valid JSON: {json_file}")
                
            except json.JSONDecodeError as e:
                validation_results["validations"][validation_name] = "FAIL"
                validation_results["errors"].append(f"Invalid JSON in {json_file}: {str(e)}")
                validation_results["overall_status"] = "FAIL"
                print(f"❌ Invalid JSON: {json_file}")
            except Exception as e:
                validation_results["validations"][validation_name] = "FAIL"
                validation_results["errors"].append(f"Error reading {json_file}: {str(e)}")
                validation_results["overall_status"] = "FAIL"
                print(f"❌ Error reading: {json_file}")
        
        # Validate Drive links count consistency
        try:
            # Load Google Sheets analysis
            sheets_analysis_path = self.project_root / "reports/google_sheets_analysis.json"
            if sheets_analysis_path.exists():
                with open(sheets_analysis_path, 'r', encoding='utf-8') as f:
                    sheets_data = json.load(f)
                
                sheets_drive_count = sheets_data.get('drive_links', {}).get('total_drive_links', 0)
                
                # Load hierarchical enhanced data
                hierarchical_path = self.project_root / "data/products_hierarchical_enhanced.json"
                if hierarchical_path.exists():
                    with open(hierarchical_path, 'r', encoding='utf-8') as f:
                        hierarchical_data = json.load(f)
                    
                    # Count drive links in hierarchical data
                    hierarchical_drive_count = 0
                    for product in hierarchical_data.get('products', []):
                        if product.get('drive_link'):
                            hierarchical_drive_count += 1
                    
                    if sheets_drive_count == hierarchical_drive_count:
                        validation_results["validations"]["drive_links_consistency"] = "PASS"
                        print(f"✅ Drive links consistent: {sheets_drive_count} links")
                    else:
                        validation_results["validations"]["drive_links_consistency"] = "WARN"
                        validation_results["warnings"].append(
                            f"Drive link count mismatch: Sheets={sheets_drive_count}, Hierarchical={hierarchical_drive_count}"
                        )
                        print(f"⚠️  Drive link count mismatch: Sheets={sheets_drive_count}, Hierarchical={hierarchical_drive_count}")
                
        except Exception as e:
            validation_results["validations"]["drive_links_consistency"] = "FAIL"
            validation_results["errors"].append(f"Drive links validation failed: {str(e)}")
            validation_results["overall_status"] = "FAIL"
        
        return validation_results
    
    def create_rollback_script(self) -> str:
        """
        Create a rollback script for emergency restoration.
        """
        rollback_script = f'''#!/bin/bash
# Emergency Rollback Script
# Generated: {datetime.now().isoformat()}
# Backup Directory: {self.backup_dir}

echo "🔄 Starting emergency rollback..."

# Stop any running processes
echo "Stopping any running processes..."
pkill -f "python.*brochure" || true

# Restore critical files
echo "Restoring files from backup..."
'''
        
        critical_files = [
            "data/products_hierarchical_enhanced.json",
            "data/products.json"
        ]
        
        for file_path in critical_files:
            source_path = self.project_root / file_path
            backup_file_path = self.backup_dir / Path(file_path).name
            
            rollback_script += f'''if [ -f "{backup_file_path}" ]; then
    cp "{backup_file_path}" "{source_path}"
    echo "✅ Restored: {file_path}"
else
    echo "❌ Backup not found: {backup_file_path}"
fi

'''
        
        rollback_script += '''echo "🔄 Rollback completed!"
echo "⚠️  Please verify data integrity and regenerate brochures if needed."
'''
        
        rollback_script_path = self.backup_dir / "emergency_rollback.sh"
        with open(rollback_script_path, 'w', encoding='utf-8') as f:
            f.write(rollback_script)
        
        # Make script executable
        os.chmod(rollback_script_path, 0o755)
        
        return str(rollback_script_path)
    
    def generate_validation_report(self, backup_manifest: Dict[str, Any], validation_results: Dict[str, Any]) -> str:
        """
        Generate comprehensive validation and backup report.
        """
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "backup_summary": {
                "backup_directory": str(self.backup_dir),
                "backup_success": backup_manifest["backup_success"],
                "files_backed_up": len(backup_manifest["files_backed_up"]),
                "backup_errors": len(backup_manifest["errors"])
            },
            "validation_summary": {
                "overall_status": validation_results["overall_status"],
                "total_validations": len(validation_results["validations"]),
                "passed_validations": len([v for v in validation_results["validations"].values() if v == "PASS"]),
                "warnings": len(validation_results["warnings"]),
                "errors": len(validation_results["errors"])
            },
            "detailed_backup_manifest": backup_manifest,
            "detailed_validation_results": validation_results,
            "next_steps": [
                "Review this validation report",
                "Ensure all backups completed successfully",
                "Set up S3 bucket and AWS credentials",
                "Test S3 migration on a small subset first",
                "Keep rollback script ready for emergency use"
            ]
        }
        
        report_path = self.project_root / "reports" / f"validation_backup_report_{self.backup_timestamp}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return str(report_path)

def main():
    """
    Main function to perform validation and backup.
    """
    try:
        print("=== Data Validation and Backup System ===")
        
        # Initialize backup system
        backup_system = DataValidationBackup()
        
        # Create backup directory
        if not backup_system.create_backup_directory():
            return 1
        
        # Create backups
        backup_manifest = backup_system.backup_critical_files()
        
        # Validate data consistency
        validation_results = backup_system.validate_data_consistency()
        
        # Create rollback script
        rollback_script_path = backup_system.create_rollback_script()
        print(f"\n✅ Rollback script created: {rollback_script_path}")
        
        # Generate comprehensive report
        report_path = backup_system.generate_validation_report(backup_manifest, validation_results)
        print(f"\n📊 Validation report saved: {report_path}")
        
        # Summary
        print("\n=== Summary ===")
        if backup_manifest["backup_success"] and validation_results["overall_status"] in ["PASS", "WARN"]:
            print("✅ Backup and validation completed successfully!")
            print("✅ System is ready for S3 migration.")
            if validation_results["warnings"]:
                print(f"⚠️  {len(validation_results['warnings'])} warnings found - review report.")
        else:
            print("❌ Backup or validation failed!")
            print("❌ Do NOT proceed with S3 migration until issues are resolved.")
            return 1
        
        print("\n🔒 Emergency rollback available if needed:")
        print(f"   bash {rollback_script_path}")
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())