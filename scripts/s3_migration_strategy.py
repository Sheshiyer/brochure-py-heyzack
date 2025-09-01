#!/usr/bin/env python3
"""
S3 Migration Strategy for Google Drive Images

This script provides a comprehensive plan for migrating Google Drive images to S3.
Includes validation, backup, and rollback procedures.
"""

import json
import os
import requests
import hashlib
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
from datetime import datetime

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("AWS SDK not installed. Run: pip install boto3")
    boto3 = None

class S3MigrationPlanner:
    """
    Plans and executes migration of Google Drive images to S3.
    """
    
    def __init__(self, s3_bucket: str, s3_region: str = "us-east-1"):
        self.s3_bucket = s3_bucket
        self.s3_region = s3_region
        self.s3_client = None
        self.migration_log = []
        
        if boto3:
            try:
                self.s3_client = boto3.client('s3', region_name=s3_region)
            except Exception as e:
                print(f"Warning: Could not initialize S3 client: {e}")
    
    def load_drive_links_analysis(self, analysis_file: str) -> List[Dict[str, Any]]:
        """
        Load the Drive links analysis from JSON file.
        """
        with open(analysis_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('drive_links', {}).get('all_links', [])
    
    def convert_drive_url_to_direct(self, drive_url: str) -> str:
        """
        Convert Google Drive view URL to direct download URL.
        """
        if "/file/d/" in drive_url:
            file_id = drive_url.split("/file/d/")[1].split("/")[0]
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        return drive_url
    
    def generate_s3_key(self, file_id: str, original_filename: str = None) -> str:
        """
        Generate S3 key for the image file.
        """
        # Use file_id as base name to ensure uniqueness
        if original_filename:
            # Extract extension from original filename
            ext = os.path.splitext(original_filename)[1].lower()
            if not ext:
                ext = '.jpg'  # Default extension
        else:
            ext = '.jpg'  # Default extension
        
        return f"product-images/{file_id}{ext}"
    
    def validate_image_accessibility(self, drive_links: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate that Drive images are accessible for download.
        """
        validation_results = {
            "total_links": len(drive_links),
            "accessible": 0,
            "inaccessible": 0,
            "errors": [],
            "accessible_links": [],
            "inaccessible_links": []
        }
        
        print(f"Validating accessibility of {len(drive_links)} Drive links...")
        
        for i, link_info in enumerate(drive_links, 1):
            file_id = link_info['file_id']
            original_url = link_info['url']
            direct_url = self.convert_drive_url_to_direct(original_url)
            
            try:
                # Test accessibility with HEAD request
                response = requests.head(direct_url, timeout=10, allow_redirects=True)
                
                if response.status_code == 200:
                    validation_results["accessible"] += 1
                    validation_results["accessible_links"].append({
                        "file_id": file_id,
                        "original_url": original_url,
                        "direct_url": direct_url,
                        "content_type": response.headers.get('content-type', 'unknown'),
                        "content_length": response.headers.get('content-length', 'unknown')
                    })
                else:
                    validation_results["inaccessible"] += 1
                    validation_results["inaccessible_links"].append({
                        "file_id": file_id,
                        "original_url": original_url,
                        "direct_url": direct_url,
                        "status_code": response.status_code,
                        "error": f"HTTP {response.status_code}"
                    })
                    
            except Exception as e:
                validation_results["inaccessible"] += 1
                validation_results["errors"].append({
                    "file_id": file_id,
                    "original_url": original_url,
                    "error": str(e)
                })
                validation_results["inaccessible_links"].append({
                    "file_id": file_id,
                    "original_url": original_url,
                    "error": str(e)
                })
            
            if i % 10 == 0:
                print(f"  Validated {i}/{len(drive_links)} links...")
        
        return validation_results
    
    def create_migration_plan(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create detailed migration plan based on validation results.
        """
        accessible_links = validation_results['accessible_links']
        
        migration_plan = {
            "timestamp": datetime.now().isoformat(),
            "s3_bucket": self.s3_bucket,
            "s3_region": self.s3_region,
            "total_images_to_migrate": len(accessible_links),
            "estimated_storage_mb": 0,  # Will be calculated
            "migration_steps": [],
            "backup_plan": {
                "create_backup_json": True,
                "backup_original_urls": True,
                "rollback_procedure": "Restore original Drive URLs from backup"
            },
            "validation_summary": {
                "total_tested": validation_results['total_links'],
                "accessible": validation_results['accessible'],
                "inaccessible": validation_results['inaccessible']
            }
        }
        
        # Calculate estimated storage
        total_size_bytes = 0
        for link in accessible_links:
            content_length = link.get('content_length', '0')
            if content_length != 'unknown' and content_length.isdigit():
                total_size_bytes += int(content_length)
        
        migration_plan['estimated_storage_mb'] = round(total_size_bytes / (1024 * 1024), 2)
        
        # Create migration steps
        for link in accessible_links:
            file_id = link['file_id']
            s3_key = self.generate_s3_key(file_id)
            s3_url = f"https://{self.s3_bucket}.s3.{self.s3_region}.amazonaws.com/{s3_key}"
            
            migration_plan['migration_steps'].append({
                "file_id": file_id,
                "original_drive_url": link['original_url'],
                "direct_download_url": link['direct_url'],
                "s3_key": s3_key,
                "s3_url": s3_url,
                "content_type": link.get('content_type', 'image/jpeg')
            })
        
        return migration_plan
    
    def save_migration_plan(self, migration_plan: Dict[str, Any], filename: str):
        """
        Save migration plan to JSON file.
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(migration_plan, f, indent=2, ensure_ascii=False)
        print(f"Migration plan saved to: {filename}")
    
    def create_backup_strategy(self) -> Dict[str, Any]:
        """
        Create comprehensive backup strategy.
        """
        return {
            "backup_files": [
                "data/products_hierarchical_enhanced.json",
                "data/products.json",
                "reports/google_sheets_analysis.json"
            ],
            "backup_directory": f"data/backups/pre_s3_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "rollback_procedure": [
                "1. Stop any running processes",
                "2. Restore original JSON files from backup",
                "3. Revert any Google Sheets changes",
                "4. Clear S3 bucket if needed",
                "5. Regenerate brochures with original URLs"
            ],
            "validation_steps": [
                "1. Verify backup files exist and are readable",
                "2. Test S3 bucket access and permissions",
                "3. Validate image download capabilities",
                "4. Confirm rollback procedure works"
            ]
        }

def main():
    """
    Main function to create S3 migration strategy.
    """
    # Configuration - these would need to be set by user
    S3_BUCKET = "smart-home-product-images"  # Example bucket name
    S3_REGION = "us-east-1"
    ANALYSIS_FILE = "reports/google_sheets_analysis.json"
    
    try:
        print("=== S3 Migration Strategy Generator ===")
        
        # Initialize planner
        planner = S3MigrationPlanner(S3_BUCKET, S3_REGION)
        
        # Load Drive links analysis
        if not os.path.exists(ANALYSIS_FILE):
            print(f"❌ Analysis file not found: {ANALYSIS_FILE}")
            print("Please run sheets_data_analyzer.py first.")
            return 1
        
        drive_links = planner.load_drive_links_analysis(ANALYSIS_FILE)
        print(f"Loaded {len(drive_links)} Drive links for migration analysis")
        
        # Validate image accessibility
        print("\n=== Validating Drive Image Accessibility ===")
        validation_results = planner.validate_image_accessibility(drive_links)
        
        print(f"\nValidation Results:")
        print(f"  ✅ Accessible: {validation_results['accessible']}")
        print(f"  ❌ Inaccessible: {validation_results['inaccessible']}")
        print(f"  📊 Success Rate: {validation_results['accessible']/validation_results['total_links']*100:.1f}%")
        
        # Create migration plan
        print("\n=== Creating Migration Plan ===")
        migration_plan = planner.create_migration_plan(validation_results)
        
        print(f"Migration Plan Summary:")
        print(f"  📦 Images to migrate: {migration_plan['total_images_to_migrate']}")
        print(f"  💾 Estimated storage: {migration_plan['estimated_storage_mb']} MB")
        print(f"  🪣 Target S3 bucket: {migration_plan['s3_bucket']}")
        
        # Save migration plan
        plan_filename = "reports/s3_migration_plan.json"
        planner.save_migration_plan(migration_plan, plan_filename)
        
        # Create backup strategy
        backup_strategy = planner.create_backup_strategy()
        backup_filename = "reports/backup_strategy.json"
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(backup_strategy, f, indent=2, ensure_ascii=False)
        print(f"Backup strategy saved to: {backup_filename}")
        
        print("\n✅ S3 Migration strategy created successfully!")
        print("\n⚠️  IMPORTANT: Review the migration plan before execution.")
        print("⚠️  IMPORTANT: Set up S3 bucket and AWS credentials before migration.")
        print("⚠️  IMPORTANT: Create backups before making any changes.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())