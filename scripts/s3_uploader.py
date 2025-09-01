#!/usr/bin/env python3
"""
S3 Uploader Module

This module provides functionality to upload generated product images to AWS S3
with proper naming conventions and metadata.

Usage:
    from s3_uploader import S3Uploader
    
    uploader = S3Uploader(bucket_name="your-bucket")
    uploader.upload_image(local_path, model_id)
"""

import boto3
import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
import mimetypes
from botocore.exceptions import ClientError, NoCredentialsError

class S3Uploader:
    """Handle uploading generated images to AWS S3."""
    
    def __init__(self, bucket_name: str, aws_access_key_id: Optional[str] = None, 
                 aws_secret_access_key: Optional[str] = None, region: str = 'us-east-1'):
        """
        Initialize S3 uploader.
        
        Args:
            bucket_name: Name of the S3 bucket
            aws_access_key_id: AWS access key (optional, can use env vars)
            aws_secret_access_key: AWS secret key (optional, can use env vars)
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.region = region
        
        # Initialize S3 client
        try:
            if aws_access_key_id and aws_secret_access_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=region
                )
            else:
                # Use default credentials (env vars, IAM role, etc.)
                self.s3_client = boto3.client('s3', region_name=region)
                
            # Test connection
            self._test_connection()
            
        except NoCredentialsError:
            raise ValueError("AWS credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables or pass them as parameters.")
        except Exception as e:
            raise ValueError(f"Failed to initialize S3 client: {e}")
    
    def _test_connection(self):
        """Test S3 connection and bucket access."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            print(f"✅ S3 connection successful. Bucket '{self.bucket_name}' is accessible.")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise ValueError(f"Bucket '{self.bucket_name}' does not exist or is not accessible.")
            elif error_code == '403':
                raise ValueError(f"Access denied to bucket '{self.bucket_name}'. Check your permissions.")
            else:
                raise ValueError(f"Error accessing bucket '{self.bucket_name}': {e}")
    
    def upload_image(self, local_path: str, model_id: str, 
                    metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Upload image to S3 with proper naming convention.
        
        Args:
            local_path: Path to local image file
            model_id: Product model ID
            metadata: Optional metadata to include
            
        Returns:
            S3 URL of uploaded image or None if failed
        """
        local_file = Path(local_path)
        
        if not local_file.exists():
            print(f"❌ Local file not found: {local_path}")
            return None
        
        # Generate S3 key with naming convention
        s3_key = f"use-case-{model_id}{local_file.suffix}"
        
        try:
            # Prepare upload parameters
            upload_params = {
                'Bucket': self.bucket_name,
                'Key': s3_key,
                'Filename': str(local_file)
            }
            
            # Add content type
            content_type, _ = mimetypes.guess_type(str(local_file))
            if content_type:
                upload_params['ExtraArgs'] = {'ContentType': content_type}
            
            # Add metadata if provided
            if metadata:
                if 'ExtraArgs' not in upload_params:
                    upload_params['ExtraArgs'] = {}
                upload_params['ExtraArgs']['Metadata'] = {
                    k: str(v) for k, v in metadata.items()
                }
            
            # Upload file
            print(f"📤 Uploading {local_file.name} to s3://{self.bucket_name}/{s3_key}...")
            self.s3_client.upload_file(**upload_params)
            
            # Generate public URL
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            
            print(f"✅ Upload successful: {s3_url}")
            return s3_url
            
        except ClientError as e:
            print(f"❌ S3 upload failed: {e}")
            return None
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return None
    
    def upload_batch(self, file_mapping: Dict[str, str], 
                    metadata_mapping: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Optional[str]]:
        """
        Upload multiple images in batch.
        
        Args:
            file_mapping: Dict mapping model_id to local file path
            metadata_mapping: Optional dict mapping model_id to metadata
            
        Returns:
            Dict mapping model_id to S3 URL (or None if failed)
        """
        results = {}
        
        print(f"📦 Starting batch upload of {len(file_mapping)} files...")
        
        for model_id, local_path in file_mapping.items():
            metadata = metadata_mapping.get(model_id) if metadata_mapping else None
            s3_url = self.upload_image(local_path, model_id, metadata)
            results[model_id] = s3_url
        
        successful_uploads = sum(1 for url in results.values() if url is not None)
        print(f"📊 Batch upload completed: {successful_uploads}/{len(file_mapping)} successful")
        
        return results
    
    def delete_image(self, model_id: str) -> bool:
        """
        Delete image from S3.
        
        Args:
            model_id: Product model ID
            
        Returns:
            True if successful, False otherwise
        """
        s3_key = f"use-case-{model_id}.webp"  # Assume webp format
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            print(f"🗑️  Deleted s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            print(f"❌ Failed to delete {s3_key}: {e}")
            return False
    
    def list_uploaded_images(self, prefix: str = "use-case-") -> list:
        """
        List all uploaded images with the given prefix.
        
        Args:
            prefix: S3 key prefix to filter by
            
        Returns:
            List of S3 object information
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            objects = response.get('Contents', [])
            print(f"📋 Found {len(objects)} uploaded images with prefix '{prefix}'")
            
            return objects
            
        except ClientError as e:
            print(f"❌ Failed to list objects: {e}")
            return []
    
    def generate_upload_report(self, upload_results: Dict[str, Optional[str]], 
                             output_path: str = "s3_upload_report.json"):
        """
        Generate a report of upload results.
        
        Args:
            upload_results: Results from batch upload
            output_path: Path to save report
        """
        successful_uploads = {k: v for k, v in upload_results.items() if v is not None}
        failed_uploads = [k for k, v in upload_results.items() if v is None]
        
        report = {
            "timestamp": __import__('time').strftime("%Y-%m-%d %H:%M:%S"),
            "bucket_name": self.bucket_name,
            "total_files": len(upload_results),
            "successful_uploads": len(successful_uploads),
            "failed_uploads": len(failed_uploads),
            "success_rate": len(successful_uploads) / len(upload_results) * 100 if upload_results else 0,
            "uploaded_files": successful_uploads,
            "failed_files": failed_uploads
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Upload report saved to: {output_path}")

def create_s3_config_template():
    """Create a template configuration file for S3 settings."""
    config_template = {
        "aws": {
            "access_key_id": "YOUR_AWS_ACCESS_KEY_ID",
            "secret_access_key": "YOUR_AWS_SECRET_ACCESS_KEY",
            "region": "us-east-1",
            "bucket_name": "your-product-images-bucket"
        },
        "upload_settings": {
            "content_type_mapping": {
                ".webp": "image/webp",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png"
            },
            "default_metadata": {
                "source": "product-image-generator",
                "type": "use-case-image"
            }
        }
    }
    
    config_path = "s3_config.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_template, f, indent=2)
    
    print(f"📝 S3 configuration template created: {config_path}")
    print("⚠️  Please update the configuration with your actual AWS credentials.")

if __name__ == "__main__":
    # Create configuration template
    create_s3_config_template()
    
    # Example usage (commented out)
    """
    # Initialize uploader
    uploader = S3Uploader(
        bucket_name="your-bucket-name",
        aws_access_key_id="your-access-key",
        aws_secret_access_key="your-secret-key"
    )
    
    # Upload single image
    s3_url = uploader.upload_image(
        local_path="../generated_images/use-case-MODEL123.webp",
        model_id="MODEL123",
        metadata={"category": "Video Door Bell", "generated_at": "2025-01-01"}
    )
    
    # Upload batch
    file_mapping = {
        "MODEL123": "../generated_images/use-case-MODEL123.webp",
        "MODEL456": "../generated_images/use-case-MODEL456.webp"
    }
    
    results = uploader.upload_batch(file_mapping)
    uploader.generate_upload_report(results)
    """