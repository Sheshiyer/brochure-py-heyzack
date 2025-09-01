#!/usr/bin/env python3
"""
Google Nano Banana Image Generator

This script generates contextual product usage scenario images by:
1. Reading product data from JSON file
2. Generating contextual prompts based on product features
3. Creating images using Google Nano Banana model API
4. Saving images locally with specific naming convention

Usage:
    python google_nano_image_generator.py
"""

import json
import os
import re
import requests
from typing import Dict, List, Optional
from pathlib import Path
import time
import base64
from datetime import datetime
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import tempfile

# Configuration
PRODUCTS_JSON_PATH = "../data/products_hierarchical_enhanced.json"
OUTPUT_DIR = "../generated_images"
GOOGLE_API_KEY = "AIzaSyCwuQIIN5xseahgsliQxm7whDMTdYG5mM8"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# S3 Configuration (disabled by default)
ENABLE_S3_UPLOAD = False
S3_BUCKET_NAME = "smart-home-generated-images"
S3_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = None  # Set when enabling S3
AWS_SECRET_ACCESS_KEY = None  # Set when enabling S3

class GoogleNanoImageGenerator:
    def __init__(self, products_file: str, output_dir: str):
        self.products_file = Path(products_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Google Gemini client will be initialized in call_google_api method
        # No global configuration needed for the new google.genai library
        
        # S3 client (initialized only if S3 upload is enabled)
        self.s3_client = None
        if ENABLE_S3_UPLOAD:
            self._initialize_s3_client()
        
    def load_products(self) -> Dict:
        """Load product data from JSON file."""
        try:
            with open(self.products_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Products file not found: {self.products_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in products file: {e}")
    
    def extract_key_features(self, product: Dict) -> List[str]:
        """Extract key features from product specifications and description."""
        features = []
        
        # Extract from specifications
        if 'specifications' in product and product['specifications']:
            for spec in product['specifications']:
                if isinstance(spec, str):
                    # Clean up specification text
                    clean_spec = re.sub(r'^(Feature\||Specifications?:?\s*)', '', spec)
                    if clean_spec and len(clean_spec) > 5:
                        features.append(clean_spec.strip())
        
        # Extract from description
        if 'description' in product and product['description']:
            desc = product['description']
            # Extract key phrases from description
            key_phrases = self._extract_key_phrases(desc)
            features.extend(key_phrases)
        
        return features[:5]  # Limit to top 5 features
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from product description."""
        # Simple keyword extraction - can be enhanced with NLP
        keywords = [
            'HD', '4K', '2K', 'wireless', 'Wi-Fi', 'Bluetooth', 'motion detection',
            'night vision', 'two-way audio', 'weatherproof', 'battery', 'solar',
            'smart', 'AI', 'cloud storage', 'mobile app', 'remote control',
            'security', 'monitoring', 'alert', 'notification'
        ]
        
        found_features = []
        text_lower = text.lower()
        
        for keyword in keywords:
            if keyword.lower() in text_lower:
                found_features.append(keyword)
        
        return found_features
    
    def generate_contextual_prompt(self, product: Dict, has_reference_image: bool = False) -> str:
        """Generate a contextual usage scenario prompt for the product."""
        model_id = product.get('model_id', 'Unknown')
        category = product.get('category', 'Smart Device')
        subcategory = product.get('subcategory', '')
        name = product.get('name', model_id)
        
        # Extract key features
        features = self.extract_key_features(product)
        features_text = ', '.join(features) if features else 'advanced smart features'
        
        # Generate contextual scenarios based on category
        scenarios = {
            'Video Doorbell': f"A family home front door with {name} capturing clear footage of visitors, with the device prominently displayed and a smartphone showing the live feed",
            'Security Camera': f"A modern home security setup with {name} monitoring the entrance, showing clear video quality and smart detection capabilities",
            'Smart Lock': f"A contemporary front door featuring {name} with a person using smartphone app to unlock, demonstrating convenience and security",
            'Motion Sensor': f"A well-lit home interior with {name} detecting movement, showing the device and connected smart home responses",
            'Smart Switch': f"A modern living room with {name} controlling lighting, person using mobile app, showing convenience and smart home integration",
            'Default': f"A modern smart home setup showcasing {name} in use, demonstrating its key features and benefits"
        }
        
        # Select appropriate scenario
        scenario = scenarios.get(subcategory, scenarios.get(category, scenarios['Default']))
        
        # Create comprehensive prompt
        if has_reference_image:
            prompt = f"Using the product shown in the reference image, create a realistic usage scenario: {scenario}. Show this exact product being used in its intended environment. Key features to highlight: {features_text}. Style: Clean, modern, well-lit, professional product photography with real-world usage context. Keep the product design and appearance consistent with the reference image. Avoid text, logos, or branding. Focus on the product in its intended environment."
        else:
            prompt = f"{scenario}, emphasizing Features: {features_text}, professional product photography, clean modern aesthetic, high quality, realistic lighting, 4K resolution"
        
        return prompt
    
    def download_product_image(self, image_url: str) -> Optional[Image.Image]:
        """Download product image from S3 URL."""
        try:
            print(f"📥 Downloading product image from: {image_url}")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Open image with PIL
            image = Image.open(BytesIO(response.content))
            print(f"✅ Product image downloaded successfully")
            return image
            
        except Exception as e:
            print(f"❌ Error downloading product image: {e}")
            return None
    
    def _initialize_s3_client(self):
        """Initialize S3 client for uploading generated images."""
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError, ClientError
            
            if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
                print("⚠️ S3 upload enabled but AWS credentials not configured")
                return
            
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=S3_REGION
            )
            print(f"✅ S3 client initialized for bucket: {S3_BUCKET_NAME}")
            
        except ImportError:
            print("⚠️ boto3 not installed. Install with: pip install boto3")
            self.s3_client = None
        except Exception as e:
            print(f"❌ Failed to initialize S3 client: {e}")
            self.s3_client = None
    
    def upload_to_s3(self, local_file_path: str, s3_key: str) -> bool:
        """Upload generated image to S3 bucket."""
        if not ENABLE_S3_UPLOAD or not self.s3_client:
            return False
        
        try:
            from botocore.exceptions import ClientError
            
            # Upload file to S3
            self.s3_client.upload_file(
                local_file_path,
                S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={
                    'ContentType': 'image/png',
                    'ACL': 'public-read'  # Make images publicly accessible
                }
            )
            
            # Generate public URL
            s3_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
            print(f"☁️ Uploaded to S3: {s3_url}")
            return True
            
        except ClientError as e:
            print(f"❌ S3 upload failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected S3 upload error: {e}")
            return False
    
    def call_google_api(self, prompt: str, product_image: Optional[Image.Image] = None) -> Optional[Dict]:
        """Generate image using Google Gemini 2.5 Flash Image Preview model."""
        try:
            print(f"🤖 Generating AI image with Google Gemini...")
            
            # Initialize Google Gemini client
            client = genai.Client(api_key=GOOGLE_API_KEY)
            
            # Prepare content for the API call
            contents = [prompt]
            
            # Add product image as reference if available
            if product_image:
                print(f"📸 Including product reference image")
                contents.append(product_image)
            
            # Generate content using Gemini 2.5 Flash Image Preview
            response = client.models.generate_content(
                model="gemini-2.5-flash-image-preview",
                contents=contents,
            )
            
            # Process the response
            for part in response.candidates[0].content.parts:
                if part.text is not None:
                    print(f"📝 Generated text: {part.text[:100]}...")
                elif part.inline_data is not None:
                    print(f"🖼️ Generated image data: {len(part.inline_data.data)} bytes")
                    
                    # Convert image data to base64
                    image_data = base64.b64encode(part.inline_data.data).decode('utf-8')
                    
                    return {
                        "success": True,
                        "image_data": image_data,
                        "mime_type": part.inline_data.mime_type or 'image/jpeg'
                    }
            
            print(f"⚠️ No image data found in response")
            return None
            
        except Exception as e:
            print(f"❌ Error calling Google Gemini API: {e}")
            print(f"🔄 Falling back to template generation...")
            return self._generate_fallback_template(prompt, product_image)
    
    def _generate_fallback_template(self, prompt: str, product_image: Optional[Image.Image] = None) -> Optional[Dict]:
        """Fallback template generation when API fails."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import textwrap
            import random
            
            # Create a high-resolution image
            img = Image.new('RGB', (1024, 768), color='#f8f9fa')
            draw = ImageDraw.Draw(img)
            
            # Create gradient background
            for y in range(768):
                gradient_color = int(248 - (y * 20 / 768))
                draw.line([(0, y), (1024, y)], fill=(gradient_color, gradient_color + 5, gradient_color + 10))
            
            # Add main content area
            draw.rectangle([40, 40, 984, 728], fill='#ffffff', outline='#ff6b6b', width=3)
            
            # Try to load fonts
            try:
                title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
                subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
                text_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
            except:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                text_font = ImageFont.load_default()
            
            # Add header with fallback indicator
            draw.rectangle([50, 50, 974, 120], fill='#ff6b6b', outline='#ff5252', width=2)
            draw.text((60, 70), "FALLBACK: Template Product Use Case", fill='white', font=title_font)
            
            # Add scenario area
            draw.rectangle([60, 140, 964, 400], fill='#ffe3e3', outline='#ff6b6b', width=2)
            draw.text((80, 160), "Product Usage Scenario (Template)", fill='#d32f2f', font=subtitle_font)
            
            # Add wrapped prompt text
            wrapped_text = textwrap.fill(prompt[:300] + "..." if len(prompt) > 300 else prompt, width=90)
            y_offset = 190
            for line in wrapped_text.split('\n')[:8]:
                draw.text((80, y_offset), line, fill='#424242', font=text_font)
                y_offset += 22
            
            # Add product mockup area
            draw.rectangle([60, 420, 964, 680], fill='#f5f5f5', outline='#757575', width=2)
            
            # Add product representation
            if product_image:
                draw.text((80, 440), "Product Reference Image Available", fill='#2e7d32', font=subtitle_font)
                draw.rectangle([400, 480, 600, 640], fill='#c8e6c9', outline='#4caf50', width=3)
                draw.text((450, 550), "Product\nImage", fill='#1b5e20', font=subtitle_font)
            else:
                colors = ['#ff9800', '#e91e63', '#9c27b0', '#3f51b5', '#009688']
                product_color = random.choice(colors)
                draw.rectangle([400, 480, 600, 640], fill=product_color, outline='#424242', width=3)
                draw.text((450, 550), "Smart\nDevice", fill='white', font=subtitle_font)
            
            # Add footer
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            draw.text((60, 700), f"Generated: {timestamp} | Fallback Template", fill='#666666', font=text_font)
            
            # Convert to base64 JPEG
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=95, optimize=True)
            img_data = buffered.getvalue()
            
            print(f"📋 Generated fallback template: {len(img_data)} bytes")
            
            return {
                "success": True,
                "image_data": base64.b64encode(img_data).decode('utf-8'),
                "mime_type": 'image/jpeg'
            }
            
        except Exception as e:
            print(f"❌ Error generating fallback template: {e}")
            return None
    

    
    def save_image_from_base64(self, image_data: str, model_id: str, mime_type: str) -> Optional[str]:
        """Save base64 image data to file with enhanced debugging."""
        try:
            print(f"🔍 Debug - Image data length: {len(image_data)} characters")
            print(f"🔍 Debug - MIME type: {mime_type}")
            
            # Determine file extension from mime type
            extension_map = {
                'image/jpeg': 'jpg',
                'image/jpg': 'jpg', 
                'image/png': 'png',
                'image/webp': 'webp'
            }
            
            extension = extension_map.get(mime_type, 'jpg')
            print(f"🔍 Debug - File extension: {extension}")
            
            filename = f"use-case-{model_id}.{extension}"
            filepath = self.output_dir / filename
            print(f"🔍 Debug - Full filepath: {filepath}")
            
            # Decode base64 and save
            image_bytes = base64.b64decode(image_data)
            print(f"🔍 Debug - Decoded bytes length: {len(image_bytes)}")
            
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            # Verify file was created and has content
            if filepath.exists():
                file_size = filepath.stat().st_size
                print(f"✅ Image saved: {filepath} (Size: {file_size} bytes)")
                
                # Try to verify it's a valid image using PIL
                try:
                    with Image.open(filepath) as img:
                        print(f"🔍 Debug - Image format: {img.format}, Size: {img.size}, Mode: {img.mode}")
                except Exception as img_error:
                    print(f"⚠️ Warning - Image verification failed: {str(img_error)}")
                
                return str(filepath)
            else:
                print(f"❌ Error - File was not created: {filepath}")
                return None
            
        except Exception as e:
            print(f"❌ Error saving image for {model_id}: {e}")
            import traceback
            print(f"🔍 Debug - Full traceback: {traceback.format_exc()}")
            return None
    
    def generate_image(self, prompt: str, model_id: str, product_image: Optional[Image.Image] = None) -> Optional[str]:
        """Generate and save image for a product."""
        print(f"\n🎨 Generating image for {model_id}...")
        print(f"📝 Prompt: {prompt[:100]}...")
        
        for attempt in range(MAX_RETRIES):
            try:
                # Call Google API with optional product image
                api_response = self.call_google_api(prompt, product_image)
                
                if api_response and api_response.get('success'):
                    # Save image from base64 data
                    image_path = self.save_image_from_base64(
                        api_response['image_data'], 
                        model_id, 
                        api_response['mime_type']
                    )
                    
                    if image_path:
                         # Save metadata
                         self._save_image_metadata(model_id, prompt, api_response, image_path)
                         
                         # Upload to S3 if enabled
                         if ENABLE_S3_UPLOAD:
                             s3_key = f"generated-images/use-case-{model_id}.{file_extension}"
                             upload_success = self.upload_to_s3(image_path, s3_key)
                             if upload_success:
                                 # Update metadata with S3 URL
                                 s3_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
                                 self._update_metadata_with_s3_url(model_id, s3_url)
                         
                         return image_path
                    
                print(f"⚠️  Attempt {attempt + 1} failed, retrying...")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    
            except Exception as e:
                print(f"❌ Error in attempt {attempt + 1}: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
        
        print(f"❌ Failed to generate image for {model_id} after {MAX_RETRIES} attempts")
        return None
    
    def _save_image_metadata(self, model_id: str, prompt: str, api_response: Dict, image_path: str):
        """Save metadata about the generated image."""
        metadata = {
            "model_id": model_id,
            "prompt": prompt,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "image_path": image_path,
            "api_response": {
                "success": api_response.get('success'),
                "mime_type": api_response.get('mime_type')
            },
            "generator": "Google Nano Banana API"
        }
        
        metadata_path = self.output_dir / f"use-case-{model_id}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def _update_metadata_with_s3_url(self, model_id: str, s3_url: str):
        """Update image metadata with S3 URL."""
        try:
            metadata_path = self.output_dir / f"use-case-{model_id}.json"
            
            # Read existing metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Add S3 URL
            metadata['s3_url'] = s3_url
            metadata['s3_uploaded_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Write updated metadata
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"⚠️ Failed to update metadata with S3 URL: {e}")
    
    def process_products(self, limit: int = 1) -> Dict[str, str]:
        """Process products and generate images."""
        print(f"🚀 Starting Google Nano Banana image generation...")
        print(f"📁 Output directory: {self.output_dir}")
        print(f"🔢 Processing limit: {limit} products\n")
        
        # Load products
        try:
            data = self.load_products()
            # Extract products from categories structure
            products = []
            if 'categories' in data:
                for category_name, category_data in data['categories'].items():
                    if 'products' in category_data:
                        for product in category_data['products']:
                            # Add category info to product
                            product['category'] = category_name
                            # Use 'id' as 'model_id' if model_id doesn't exist
                            if 'model_id' not in product and 'id' in product:
                                product['model_id'] = product['id']
                            products.append(product)
            else:
                products = data.get('products', [])
        except Exception as e:
            print(f"❌ Error loading products: {e}")
            return {}
        
        if not products:
            print("❌ No products found in the data file")
            return {}
        
        print(f"📊 Found {len(products)} products in total")
        
        # Process products
        results = {}
        processed_count = 0
        
        for product in products:
            if processed_count >= limit:
                break
                
            model_id = product.get('model_id')
            if not model_id:
                print("⚠️  Skipping product without model_id")
                continue
            
            print(f"\n{'='*60}")
            print(f"🔄 Processing product {processed_count + 1}/{limit}: {model_id}")
            
            # Download product image if available
            product_image = None
            image_url = product.get('drive_link')
            if image_url:
                product_image = self.download_product_image(image_url)
            
            # Generate contextual prompt
            try:
                prompt = self.generate_contextual_prompt(product, has_reference_image=product_image is not None)
                print(f"📝 Generated prompt: {prompt[:100]}...")
            except Exception as e:
                print(f"❌ Error generating prompt for {model_id}: {e}")
                results[model_id] = "error_prompt_generation"
                processed_count += 1
                continue
            
            # Generate image
            try:
                image_path = self.generate_image(prompt, model_id, product_image)
                if image_path:
                    results[model_id] = image_path
                    print(f"✅ Successfully generated image for {model_id}")
                else:
                    results[model_id] = "error_image_generation"
                    print(f"❌ Failed to generate image for {model_id}")
            except Exception as e:
                print(f"❌ Error processing {model_id}: {e}")
                results[model_id] = "error_processing"
            
            processed_count += 1
            
            # Small delay between requests to be respectful to the API
            if processed_count < limit:
                time.sleep(1)
        
        # Generate summary report
        self.generate_summary_report(results)
        
        return results
    
    def generate_summary_report(self, results: Dict[str, str]):
        """Generate a summary report of the image generation process."""
        report = {
            "generation_summary": {
                "total_processed": len(results),
                "successful": len([r for r in results.values() if r.startswith('/') or r.startswith('../')]),
                "failed": len([r for r in results.values() if r.startswith('error_')]),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "generator": "Google Nano Banana API"
            },
            "results": results
        }
        
        report_path = self.output_dir / "generation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 Generation Summary:")
        print(f"   Total processed: {report['generation_summary']['total_processed']}")
        print(f"   Successful: {report['generation_summary']['successful']}")
        print(f"   Failed: {report['generation_summary']['failed']}")
        print(f"   Report saved: {report_path}")

def main():
    """Main function to run the image generator."""
    try:
        # Initialize generator
        generator = GoogleNanoImageGenerator(
            products_file=PRODUCTS_JSON_PATH,
            output_dir=OUTPUT_DIR
        )
        
        # Process products (limit to 3 for testing)
        results = generator.process_products(limit=3)
        
        print(f"\n🎉 Image generation completed!")
        print(f"📁 Check the '{OUTPUT_DIR}' directory for generated images")
        
        # Print results summary
        successful = [k for k, v in results.items() if not v.startswith('error_')]
        failed = [k for k, v in results.items() if v.startswith('error_')]
        
        if successful:
            print(f"\n✅ Successfully generated images for: {', '.join(successful)}")
        if failed:
            print(f"\n❌ Failed to generate images for: {', '.join(failed)}")
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())