#!/usr/bin/env python3
"""
Complete System Test Script

This script demonstrates the full product image generation pipeline:
1. Load product data from JSON
2. Generate contextual usage scenario prompts
3. Create images using MCP replicate-flux service
4. Save images locally with proper naming
5. Upload to S3 (optional, framework ready)

Usage:
    python3 test_complete_system.py [--enable-s3] [--bucket BUCKET_NAME]
"""

import argparse
import sys
import os
from pathlib import Path

# Add the scripts directory to Python path
sys.path.append(str(Path(__file__).parent))

from product_image_generator_with_mcp import ProductImageGeneratorMCP
from s3_uploader import create_s3_config_template

def test_image_generation_only():
    """Test image generation without S3 upload."""
    print("🧪 Testing Image Generation (Local Only)")
    print("=" * 50)
    
    # Initialize generator
    generator = ProductImageGeneratorMCP(
        products_file="../products_hierarchical_enhanced.json",
        output_dir="../generated_images"
    )
    
    # Process products (limit to 3 for testing)
    results = generator.process_products(max_products=3)
    
    print("\n📋 Test Results:")
    for model_id, file_path in results.items():
        if file_path:
            print(f"  ✅ {model_id}: {file_path}")
        else:
            print(f"  ❌ {model_id}: Failed")
    
    return results

def test_s3_framework(bucket_name: str):
    """Test S3 upload framework."""
    print(f"\n☁️  Testing S3 Framework (Bucket: {bucket_name})")
    print("=" * 50)
    
    # Initialize generator with S3 enabled
    generator = ProductImageGeneratorMCP(
        products_file="../products_hierarchical_enhanced.json",
        output_dir="../generated_images",
        enable_s3_upload=True,
        s3_bucket=bucket_name
    )
    
    # Process products
    results = generator.process_products(max_products=2)
    
    print("\n📋 S3 Test Results:")
    for model_id, file_path in results.items():
        if file_path:
            print(f"  ✅ {model_id}: Generated and uploaded")
        else:
            print(f"  ❌ {model_id}: Failed")
    
    return results

def demonstrate_s3_config():
    """Demonstrate S3 configuration setup."""
    print("\n⚙️  S3 Configuration Setup")
    print("=" * 30)
    
    # Create S3 config template
    create_s3_config_template()
    
    print("\n📝 To enable S3 upload:")
    print("1. Update s3_config.json with your AWS credentials")
    print("2. Set environment variables:")
    print("   export AWS_ACCESS_KEY_ID=your_access_key")
    print("   export AWS_SECRET_ACCESS_KEY=your_secret_key")
    print("3. Run with --enable-s3 --bucket your-bucket-name")

def analyze_generated_content():
    """Analyze the quality of generated content."""
    print("\n🔍 Content Analysis")
    print("=" * 20)
    
    output_dir = Path("../generated_images")
    
    if not output_dir.exists():
        print("❌ No generated content found. Run image generation first.")
        return
    
    # Count files by type
    json_files = list(output_dir.glob("*.json"))
    txt_files = list(output_dir.glob("*.txt"))
    image_files = list(output_dir.glob("*.webp")) + list(output_dir.glob("*.jpg")) + list(output_dir.glob("*.png"))
    
    print(f"📊 Generated Files:")
    print(f"  📄 Metadata files: {len(json_files)}")
    print(f"  📝 Text files: {len(txt_files)}")
    print(f"  🖼️  Image files: {len(image_files)}")
    
    # Analyze a sample prompt
    if json_files:
        sample_file = json_files[0]
        print(f"\n📋 Sample Prompt Analysis ({sample_file.name}):")
        
        try:
            import json
            with open(sample_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            prompt = data.get('prompt', '')
            print(f"  📝 Prompt length: {len(prompt)} characters")
            print(f"  🎯 Model ID: {data.get('model_id', 'N/A')}")
            print(f"  ⏰ Generated: {data.get('generated_at', 'N/A')}")
            print(f"  🔗 Prediction ID: {data.get('prediction_id', 'N/A')}")
            
            # Show first 200 characters of prompt
            print(f"  📖 Prompt preview: {prompt[:200]}...")
            
        except Exception as e:
            print(f"  ❌ Error reading sample file: {e}")

def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description='Test complete product image generation system')
    parser.add_argument('--enable-s3', action='store_true', help='Enable S3 upload testing')
    parser.add_argument('--bucket', type=str, help='S3 bucket name for testing')
    parser.add_argument('--config-only', action='store_true', help='Only demonstrate S3 configuration')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze existing generated content')
    
    args = parser.parse_args()
    
    print("🚀 Product Image Generation System Test")
    print("=" * 40)
    
    # Handle specific modes
    if args.config_only:
        demonstrate_s3_config()
        return
    
    if args.analyze_only:
        analyze_generated_content()
        return
    
    # Test image generation
    try:
        if args.enable_s3 and args.bucket:
            # Test with S3 upload
            results = test_s3_framework(args.bucket)
        else:
            # Test local generation only
            results = test_image_generation_only()
            
            if args.enable_s3:
                print("\n⚠️  S3 upload requested but no bucket specified.")
                print("Use --bucket BUCKET_NAME to test S3 functionality.")
        
        # Analyze generated content
        analyze_generated_content()
        
        # Show S3 configuration info
        if not args.enable_s3:
            demonstrate_s3_config()
        
        print("\n✅ System test completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()