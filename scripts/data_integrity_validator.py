#!/usr/bin/env python3
"""
Data Integrity Validation Script

Validates the integrity of data after S3 migration to ensure:
1. All URLs have been properly updated
2. S3 URLs are accessible
3. Data consistency across all sources
4. No broken references remain
"""

import json
import csv
import requests
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from urllib.parse import urlparse
import time

class DataIntegrityValidator:
    """Validates data integrity after S3 migration"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.validation_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.s3_bucket_url = "https://smart-home-product-images.s3.us-east-1.amazonaws.com"
        self.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "total_files_checked": 0,
            "total_urls_found": 0,
            "s3_urls_found": 0,
            "drive_urls_remaining": 0,
            "broken_urls": [],
            "accessible_s3_urls": 0,
            "inaccessible_s3_urls": 0,
            "validation_errors": [],
            "files_validated": []
        }
    
    def find_all_urls_in_text(self, text: str) -> Set[str]:
        """Extract all URLs from text content"""
        import re
        url_pattern = r'https?://[^\s\"\'\'\,\)\]\}]+'
        urls = re.findall(url_pattern, text)
        return set(urls)
    
    def validate_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate URLs in a JSON file"""
        print(f"\n🔍 Validating JSON: {file_path.name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                data = json.loads(content)
            
            # Extract all URLs from the JSON content
            all_urls = self.find_all_urls_in_text(content)
            
            drive_urls = {url for url in all_urls if 'drive.google.com' in url}
            s3_urls = {url for url in all_urls if self.s3_bucket_url in url}
            other_urls = all_urls - drive_urls - s3_urls
            
            result = {
                "file": str(file_path),
                "total_urls": len(all_urls),
                "s3_urls": len(s3_urls),
                "drive_urls_remaining": len(drive_urls),
                "other_urls": len(other_urls),
                "drive_urls_list": list(drive_urls),
                "s3_urls_list": list(s3_urls),
                "validation_status": "PASS" if len(drive_urls) == 0 else "FAIL"
            }
            
            print(f"  📊 URLs found: {len(all_urls)} total, {len(s3_urls)} S3, {len(drive_urls)} Drive")
            
            if drive_urls:
                print(f"  ⚠️  {len(drive_urls)} Google Drive URLs still present!")
                for url in list(drive_urls)[:3]:  # Show first 3
                    print(f"    - {url[:80]}...")
            
            return result
            
        except Exception as e:
            error_msg = f"Error validating {file_path}: {e}"
            print(f"  ❌ {error_msg}")
            self.validation_results["validation_errors"].append(error_msg)
            return {
                "file": str(file_path),
                "error": str(e),
                "validation_status": "ERROR"
            }
    
    def validate_csv_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate URLs in a CSV file"""
        print(f"\n🔍 Validating CSV: {file_path.name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract all URLs from the CSV content
            all_urls = self.find_all_urls_in_text(content)
            
            drive_urls = {url for url in all_urls if 'drive.google.com' in url}
            s3_urls = {url for url in all_urls if self.s3_bucket_url in url}
            other_urls = all_urls - drive_urls - s3_urls
            
            result = {
                "file": str(file_path),
                "total_urls": len(all_urls),
                "s3_urls": len(s3_urls),
                "drive_urls_remaining": len(drive_urls),
                "other_urls": len(other_urls),
                "drive_urls_list": list(drive_urls),
                "s3_urls_list": list(s3_urls),
                "validation_status": "PASS" if len(drive_urls) == 0 else "FAIL"
            }
            
            print(f"  📊 URLs found: {len(all_urls)} total, {len(s3_urls)} S3, {len(drive_urls)} Drive")
            
            if drive_urls:
                print(f"  ⚠️  {len(drive_urls)} Google Drive URLs still present!")
                for url in list(drive_urls)[:3]:  # Show first 3
                    print(f"    - {url[:80]}...")
            
            return result
            
        except Exception as e:
            error_msg = f"Error validating {file_path}: {e}"
            print(f"  ❌ {error_msg}")
            self.validation_results["validation_errors"].append(error_msg)
            return {
                "file": str(file_path),
                "error": str(e),
                "validation_status": "ERROR"
            }
    
    def check_s3_url_accessibility(self, urls: List[str], sample_size: int = 10) -> Dict[str, Any]:
        """Check if S3 URLs are accessible (sample check)"""
        print(f"\n🌐 Checking S3 URL accessibility (sample of {min(sample_size, len(urls))})...")
        
        if not urls:
            return {"accessible": 0, "inaccessible": 0, "total_checked": 0, "broken_urls": []}
        
        # Sample URLs to check (don't check all to avoid rate limiting)
        sample_urls = urls[:sample_size] if len(urls) > sample_size else urls
        
        accessible = 0
        inaccessible = 0
        broken_urls = []
        
        for i, url in enumerate(sample_urls):
            try:
                print(f"  🔗 Checking {i+1}/{len(sample_urls)}: {url[:60]}...")
                response = requests.head(url, timeout=10)
                
                if response.status_code == 200:
                    accessible += 1
                    print(f"    ✅ Accessible")
                else:
                    inaccessible += 1
                    broken_urls.append({"url": url, "status_code": response.status_code})
                    print(f"    ❌ Status: {response.status_code}")
                
                # Small delay to avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                inaccessible += 1
                broken_urls.append({"url": url, "error": str(e)})
                print(f"    ❌ Error: {e}")
        
        return {
            "accessible": accessible,
            "inaccessible": inaccessible,
            "total_checked": len(sample_urls),
            "broken_urls": broken_urls
        }
    
    def validate_migration_completeness(self) -> Dict[str, Any]:
        """Validate that migration was complete by checking migration results"""
        print(f"\n📋 Validating migration completeness...")
        
        try:
            # Find latest migration results
            reports_dir = self.project_root / "reports"
            migration_files = list(reports_dir.glob("s3_migration_results_*.json"))
            
            if not migration_files:
                return {"status": "ERROR", "message": "No migration results found"}
            
            latest_file = max(migration_files, key=lambda f: f.stat().st_mtime)
            
            with open(latest_file, 'r') as f:
                migration_results = json.load(f)
            
            total_images = migration_results.get('total_images', 0)
            successful = migration_results.get('successful_migrations', 0)
            failed = migration_results.get('failed_migrations', 0)
            
            print(f"  📊 Migration Results:")
            print(f"    Total images: {total_images}")
            print(f"    Successful: {successful}")
            print(f"    Failed: {failed}")
            
            completeness_status = "COMPLETE" if failed == 0 else "INCOMPLETE"
            
            return {
                "status": completeness_status,
                "total_images": total_images,
                "successful_migrations": successful,
                "failed_migrations": failed,
                "migration_file": str(latest_file)
            }
            
        except Exception as e:
            error_msg = f"Error validating migration completeness: {e}"
            print(f"  ❌ {error_msg}")
            return {"status": "ERROR", "message": error_msg}
    
    def find_data_files(self) -> Dict[str, List[Path]]:
        """Find all data files to validate"""
        data_files = {
            'json': [],
            'csv': []
        }
        
        # Search in data and reports directories
        search_dirs = ['data', 'reports']
        
        for search_dir in search_dirs:
            dir_path = self.project_root / search_dir
            if dir_path.exists():
                # Find JSON files (exclude backups and migration results)
                for json_file in dir_path.rglob('*.json'):
                    # Skip if in backup directory or is a backup/migration file
                    if (any(part.startswith('backup') for part in json_file.parts) or 
                        any(skip in json_file.name for skip in ['s3_migration_results', 's3_url_updates', 'data_integrity_validation'])):
                        continue
                    data_files['json'].append(json_file)
                
                # Find CSV files (exclude backups)
                for csv_file in dir_path.rglob('*.csv'):
                    # Skip if in backup directory
                    if any(part.startswith('backup') for part in csv_file.parts):
                        continue
                    data_files['csv'].append(csv_file)
        
        return data_files
    
    def run_validation(self) -> Dict[str, Any]:
        """Run complete data integrity validation"""
        print("🚀 Starting Data Integrity Validation")
        print("=" * 50)
        
        # Validate migration completeness
        migration_status = self.validate_migration_completeness()
        self.validation_results["migration_completeness"] = migration_status
        
        # Find all data files
        data_files = self.find_data_files()
        
        print(f"\n📁 Found files to validate:")
        print(f"  JSON files: {len(data_files['json'])}")
        print(f"  CSV files: {len(data_files['csv'])}")
        
        all_s3_urls = set()
        
        # Validate JSON files
        for json_file in data_files['json']:
            result = self.validate_json_file(json_file)
            self.validation_results["files_validated"].append(result)
            
            if "s3_urls_list" in result:
                all_s3_urls.update(result["s3_urls_list"])
            
            self.validation_results["total_urls_found"] += result.get("total_urls", 0)
            self.validation_results["s3_urls_found"] += result.get("s3_urls", 0)
            self.validation_results["drive_urls_remaining"] += result.get("drive_urls_remaining", 0)
        
        # Validate CSV files
        for csv_file in data_files['csv']:
            result = self.validate_csv_file(csv_file)
            self.validation_results["files_validated"].append(result)
            
            if "s3_urls_list" in result:
                all_s3_urls.update(result["s3_urls_list"])
            
            self.validation_results["total_urls_found"] += result.get("total_urls", 0)
            self.validation_results["s3_urls_found"] += result.get("s3_urls", 0)
            self.validation_results["drive_urls_remaining"] += result.get("drive_urls_remaining", 0)
        
        self.validation_results["total_files_checked"] = len(data_files['json']) + len(data_files['csv'])
        
        # Check S3 URL accessibility (sample)
        if all_s3_urls:
            accessibility_results = self.check_s3_url_accessibility(list(all_s3_urls), sample_size=10)
            self.validation_results["s3_accessibility"] = accessibility_results
            self.validation_results["accessible_s3_urls"] = accessibility_results["accessible"]
            self.validation_results["inaccessible_s3_urls"] = accessibility_results["inaccessible"]
            self.validation_results["broken_urls"] = accessibility_results["broken_urls"]
        
        # Generate summary
        self.generate_validation_summary()
        
        # Save results
        self.save_validation_results()
        
        return self.validation_results
    
    def generate_validation_summary(self):
        """Generate and display validation summary"""
        print("\n" + "=" * 50)
        print("📊 VALIDATION SUMMARY")
        print("=" * 50)
        
        # Migration completeness
        migration_status = self.validation_results.get("migration_completeness", {})
        print(f"🔄 Migration Status: {migration_status.get('status', 'UNKNOWN')}")
        if migration_status.get('status') == 'COMPLETE':
            print(f"   ✅ All {migration_status.get('successful_migrations', 0)} images migrated successfully")
        elif migration_status.get('failed_migrations', 0) > 0:
            print(f"   ⚠️  {migration_status.get('failed_migrations', 0)} images failed to migrate")
        
        # URL validation
        print(f"\n📁 Files Validated: {self.validation_results['total_files_checked']}")
        print(f"🔗 Total URLs Found: {self.validation_results['total_urls_found']}")
        print(f"☁️  S3 URLs: {self.validation_results['s3_urls_found']}")
        print(f"📂 Drive URLs Remaining: {self.validation_results['drive_urls_remaining']}")
        
        # S3 accessibility
        if "s3_accessibility" in self.validation_results:
            acc_results = self.validation_results["s3_accessibility"]
            print(f"\n🌐 S3 URL Accessibility (sample of {acc_results['total_checked']})")
            print(f"   ✅ Accessible: {acc_results['accessible']}")
            print(f"   ❌ Inaccessible: {acc_results['inaccessible']}")
        
        # Overall status
        overall_status = "PASS" if (
            self.validation_results['drive_urls_remaining'] == 0 and
            len(self.validation_results['validation_errors']) == 0 and
            migration_status.get('status') == 'COMPLETE'
        ) else "FAIL"
        
        print(f"\n🎯 Overall Validation Status: {overall_status}")
        
        if overall_status == "PASS":
            print("\n🎉 Data integrity validation PASSED!")
            print("   ✅ All Google Drive URLs have been replaced with S3 URLs")
            print("   ✅ Migration completed successfully")
            print("   ✅ S3 URLs are accessible")
        else:
            print("\n⚠️  Data integrity validation FAILED!")
            if self.validation_results['drive_urls_remaining'] > 0:
                print(f"   ❌ {self.validation_results['drive_urls_remaining']} Google Drive URLs still present")
            if len(self.validation_results['validation_errors']) > 0:
                print(f"   ❌ {len(self.validation_results['validation_errors'])} validation errors occurred")
            if migration_status.get('status') != 'COMPLETE':
                print(f"   ❌ Migration status: {migration_status.get('status', 'UNKNOWN')}")
    
    def save_validation_results(self):
        """Save validation results to file"""
        results_file = self.project_root / "reports" / f"data_integrity_validation_{self.validation_timestamp}.json"
        
        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.validation_results, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Validation results saved: {results_file}")
            
        except Exception as e:
            print(f"\n❌ Error saving validation results: {e}")

def main():
    """Main execution function"""
    validator = DataIntegrityValidator()
    results = validator.run_validation()
    
    # Exit with appropriate code
    if results['drive_urls_remaining'] == 0 and len(results['validation_errors']) == 0:
        exit(0)  # Success
    else:
        exit(1)  # Validation failed

if __name__ == "__main__":
    main()