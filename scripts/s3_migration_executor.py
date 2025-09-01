#!/usr/bin/env python3
"""
S3 Migration Executor

Executes the migration of Google Drive images to AWS S3 bucket.
Handles S3 setup, image download, upload, and URL updates.
"""

import json
import os
import requests
import hashlib
import boto3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
import time

class S3MigrationExecutor:
    """
    Handles the complete S3 migration process for Google Drive images.
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.migration_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.temp_dir = self.project_root / "temp" / f"s3_migration_{self.migration_timestamp}"
        self.s3_client = None
        self.bucket_name = "smart-home-product-images"
        
    def setup_aws_credentials(self) -> bool:
        """
        Setup AWS credentials and S3 client.
        """
        print("=== AWS S3 Setup ===")
        
        # Check for AWS credentials
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        if not aws_access_key or not aws_secret_key:
            print("❌ AWS credentials not found in environment variables.")
            print("\n📋 Please set the following environment variables:")
            print("   export AWS_ACCESS_KEY_ID='your_access_key'")
            print("   export AWS_SECRET_ACCESS_KEY='your_secret_key'")
            print("   export AWS_DEFAULT_REGION='us-east-1'  # optional")
            print("\n💡 Or run: aws configure")
            return False
        
        try:
            # Initialize S3 client
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )
            
            # Test connection
            self.s3_client.list_buckets()
            print(f"✅ AWS S3 client initialized successfully (Region: {aws_region})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize AWS S3 client: {e}")
            return False
    
    def create_s3_bucket(self) -> bool:
        """
        Create S3 bucket if it doesn't exist.
        """
        try:
            # Check if bucket exists
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                print(f"✅ S3 bucket '{self.bucket_name}' already exists")
                return True
            except Exception as e:
                # Bucket doesn't exist, continue with creation
                print(f"📋 Bucket doesn't exist, creating new bucket...")
                pass
            
            # Create bucket
            region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            
            if region == 'us-east-1':
                # us-east-1 doesn't need LocationConstraint
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
            
            # Try to set bucket policy for public read access to images
            try:
                bucket_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "PublicReadGetObject",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": "s3:GetObject",
                            "Resource": f"arn:aws:s3:::{self.bucket_name}/*"
                        }
                    ]
                }
                
                self.s3_client.put_bucket_policy(
                    Bucket=self.bucket_name,
                    Policy=json.dumps(bucket_policy)
                )
                print(f"✅ Public read access configured for images")
            except Exception as policy_error:
                print(f"⚠️  Warning: Could not set public policy: {policy_error}")
                print(f"💡 You may need to manually configure bucket permissions in AWS Console")
            
            print(f"✅ S3 bucket '{self.bucket_name}' created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create S3 bucket: {e}")
            return False
    
    def load_migration_plan(self) -> Optional[Dict[str, Any]]:
        """
        Load the S3 migration plan.
        """
        plan_path = self.project_root / "data" / "s3_migration_plan.json"
        
        if not plan_path.exists():
            print(f"❌ Migration plan not found: {plan_path}")
            return None
        
        try:
            with open(plan_path, 'r', encoding='utf-8') as f:
                plan = json.load(f)
            
            print(f"✅ Loaded migration plan: {len(plan['migration_steps'])} images to migrate")
            return plan
            
        except Exception as e:
            print(f"❌ Failed to load migration plan: {e}")
            return None
    
    def download_image(self, url: str, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Download image from Google Drive URL.
        Returns (success, error_message)
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def upload_to_s3(self, local_path: Path, s3_key: str) -> Tuple[bool, Optional[str]]:
        """
        Upload file to S3.
        Returns (success, error_message)
        """
        try:
            # Determine content type based on file extension
            content_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            
            file_ext = local_path.suffix.lower()
            content_type = content_type_map.get(file_ext, 'application/octet-stream')
            
            # Upload file
            self.s3_client.upload_file(
                str(local_path),
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'CacheControl': 'max-age=31536000'  # 1 year cache
                }
            )
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def execute_migration(self, migration_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the complete migration process.
        """
        migration_results = {
            "timestamp": datetime.now().isoformat(),
            "total_images": len(migration_plan['migration_steps']),
            "successful_migrations": 0,
            "failed_migrations": 0,
            "migration_details": [],
            "s3_urls": {},
            "errors": []
        }
        
        print(f"\n=== Migrating {len(migration_plan['migration_steps'])} Images ===")
        
        # Create temp directory
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        for i, image_info in enumerate(migration_plan['migration_steps'], 1):
            print(f"\n[{i}/{len(migration_plan['migration_steps'])}] Processing: {image_info['original_drive_url']}")
            
            # Download image
            local_filename = f"image_{i}_{image_info['file_id']}.jpg"
            local_path = self.temp_dir / local_filename
            
            print(f"  📥 Downloading...")
            download_success, download_error = self.download_image(
                image_info['direct_download_url'], 
                local_path
            )
            
            if not download_success:
                print(f"  ❌ Download failed: {download_error}")
                migration_results["failed_migrations"] += 1
                migration_results["errors"].append({
                    "image_url": image_info['original_drive_url'],
                    "error": f"Download failed: {download_error}"
                })
                continue
            
            # Upload to S3
            print(f"  📤 Uploading to S3...")
            upload_success, upload_error = self.upload_to_s3(
                local_path, 
                image_info['s3_key']
            )
            
            if not upload_success:
                print(f"  ❌ Upload failed: {upload_error}")
                migration_results["failed_migrations"] += 1
                migration_results["errors"].append({
                    "image_url": image_info['original_drive_url'],
                    "error": f"Upload failed: {upload_error}"
                })
                # Clean up downloaded file
                if local_path.exists():
                    local_path.unlink()
                continue
            
            # Success
            print(f"  ✅ Migrated successfully")
            migration_results["successful_migrations"] += 1
            migration_results["s3_urls"][image_info['original_drive_url']] = image_info['s3_url']
            migration_results["migration_details"].append({
                "original_url": image_info['original_drive_url'],
                "s3_url": image_info['s3_url'],
                "s3_key": image_info['s3_key'],
                "file_id": image_info['file_id']
            })
            
            # Clean up downloaded file
            if local_path.exists():
                local_path.unlink()
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        return migration_results
    
    def save_migration_results(self, results: Dict[str, Any]) -> str:
        """
        Save migration results to file.
        """
        results_path = self.project_root / "reports" / f"s3_migration_results_{self.migration_timestamp}.json"
        
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        return str(results_path)
    
    def cleanup_temp_files(self):
        """
        Clean up temporary files.
        """
        try:
            if self.temp_dir.exists():
                import shutil
                shutil.rmtree(self.temp_dir)
                print(f"✅ Cleaned up temporary files: {self.temp_dir}")
        except Exception as e:
            print(f"⚠️  Failed to clean up temp files: {e}")

def main():
    """
    Main function to execute S3 migration.
    """
    try:
        print("=== S3 Migration Executor ===")
        
        # Initialize migration executor
        executor = S3MigrationExecutor()
        
        # Setup AWS credentials
        if not executor.setup_aws_credentials():
            return 1
        
        # Create S3 bucket
        if not executor.create_s3_bucket():
            return 1
        
        # Load migration plan
        migration_plan = executor.load_migration_plan()
        if not migration_plan:
            return 1
        
        # Execute migration
        print(f"\n🚀 Starting migration of {len(migration_plan['migration_steps'])} images...")
        results = executor.execute_migration(migration_plan)
        
        # Save results
        results_path = executor.save_migration_results(results)
        
        # Clean up
        executor.cleanup_temp_files()
        
        # Summary
        print("\n=== Migration Summary ===")
        print(f"✅ Successfully migrated: {results['successful_migrations']} images")
        print(f"❌ Failed migrations: {results['failed_migrations']} images")
        print(f"📊 Results saved: {results_path}")
        
        if results['failed_migrations'] > 0:
            print(f"\n⚠️  {results['failed_migrations']} images failed to migrate.")
            print("Check the results file for detailed error information.")
        
        if results['successful_migrations'] > 0:
            print(f"\n🎉 Migration completed! S3 bucket: {executor.bucket_name}")
            print("Next step: Update data sources to use S3 URLs.")
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())