#!/usr/bin/env python3
"""
Product Image Generator

This script generates contextual product usage scenario images by:
1. Reading product data from JSON file
2. Generating contextual prompts based on product features
3. Creating images using AI image generation API
4. Saving images locally with specific naming convention

Usage:
    python product_image_generator.py
"""

import json
import os
import re
import requests
from typing import Dict, List, Optional
from pathlib import Path
import time
from image_generator_mcp import MCPImageGenerator

# Configuration
GOOGLE_API_KEY = "AIzaSyCwuQIIN5xseahgsliQxm7whDMTdYG5mM8"
PRODUCTS_JSON_PATH = "../data/products_hierarchical_enhanced.json"
OUTPUT_DIR = "../generated_images"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

class ProductImageGenerator:
    def __init__(self, api_key: str, products_file: str, output_dir: str):
        self.api_key = api_key
        self.products_file = products_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.mcp_generator = MCPImageGenerator(output_dir)
        
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
    
    def generate_contextual_prompt(self, product: Dict) -> str:
        """Generate a contextual prompt for product usage scenario."""
        name = product.get('name', 'Smart Device')
        category = product.get('category', 'Smart Home Device')
        features = self.extract_key_features(product)
        
        # Create contextual scenario based on product category
        scenario_templates = {
            'Video Door Bell': [
                "A modern home entrance with a {name} installed, showing a delivery person at the door while the homeowner receives a notification on their smartphone inside a contemporary living room",
                "A family home front door with {name} capturing clear footage of visitors, with the device prominently displayed and a smartphone showing the live feed",
                "A residential doorway featuring {name} with motion detection active, showing the device's sleek design and a mobile app interface displaying alerts"
            ],
            'Security Camera': [
                "A {name} mounted on a modern home exterior, monitoring the driveway and garden area with clear visibility and professional installation",
                "An indoor setting with {name} providing home security monitoring, showing the camera's design and a smartphone displaying live footage",
                "A {name} in a contemporary office or retail space, demonstrating professional security monitoring capabilities"
            ],
            'Smart Lock': [
                "A modern front door with {name} installed, showing keyless entry in action with a smartphone unlocking the door",
                "A residential entrance featuring {name} with smart access control, displaying the lock's design and mobile app interface",
                "A home security setup with {name} providing convenient and secure access control for family members"
            ]
        }
        
        # Get appropriate template based on category
        templates = scenario_templates.get(category, [
            "A modern smart home setup featuring {name} in use, showing its key functionality and user interaction",
            "A contemporary residential setting with {name} demonstrating its practical application and benefits",
            "A real-world usage scenario of {name} highlighting its main features and user experience"
        ])
        
        # Select template and add feature context
        import random
        base_prompt = random.choice(templates).format(name=name)
        
        # Add key features to the prompt
        if features:
            feature_text = ", ".join(features[:3])  # Use top 3 features
            base_prompt += f", emphasizing {feature_text}"
        
        # Add style and quality modifiers
        base_prompt += ", professional product photography, clean modern aesthetic, high quality, realistic lighting, 4K resolution"
        
        return base_prompt
    
    def generate_image(self, prompt: str, model_id: str) -> Optional[str]:
        """Generate image using MCP replicate-flux service."""
        print(f"Generating image for model {model_id}...")
        print(f"Prompt: {prompt}")
        
        try:
            # Use MCP integration to generate actual image
            image_path = self.mcp_generator.generate_image_via_mcp(prompt, model_id)
            
            if image_path and self.mcp_generator.validate_generated_image(image_path):
                print(f"✅ Image generated successfully: {image_path}")
                return image_path
            else:
                print(f"❌ Image generation failed for {model_id}")
                return None
            
        except Exception as e:
            print(f"Error generating image for {model_id}: {e}")
            return None
    
    def process_products(self) -> Dict[str, str]:
        """Process all products and generate images."""
        print("Loading product data...")
        data = self.load_products()
        
        results = {}
        processed_count = 0
        
        # Process products from each category
        if 'categories' in data:
            for category_name, category_data in data['categories'].items():
                if 'products' in category_data:
                    print(f"\nProcessing category: {category_name}")
                    
                    for product in category_data['products']:
                        model_id = product.get('id', f"unknown_{processed_count}")
                        
                        # Skip if no valid model ID
                        if not model_id or model_id == "":
                            continue
                        
                        print(f"\nProcessing product: {product.get('name', 'Unknown')} (ID: {model_id})")
                        
                        # Generate contextual prompt
                        prompt = self.generate_contextual_prompt(product)
                        
                        # Generate image
                        image_path = self.generate_image(prompt, model_id)
                        
                        if image_path:
                            results[model_id] = image_path
                            processed_count += 1
                        
                        # Add small delay to avoid overwhelming APIs
                        time.sleep(0.5)
                        
                        # Limit processing for testing (remove in production)
                        if processed_count >= 5:
                            print(f"\nProcessed {processed_count} products (limited for testing)")
                            break
                    
                    if processed_count >= 5:
                        break
        
        print(f"\nCompleted processing {processed_count} products")
        return results
    
    def generate_summary_report(self, results: Dict[str, str]):
        """Generate a summary report of processed products."""
        report_path = self.output_dir / "generation_report.json"
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_processed": len(results),
            "output_directory": str(self.output_dir),
            "generated_files": results
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\nGeneration report saved to: {report_path}")

def main():
    """Main execution function."""
    print("Product Image Generator Starting...")
    
    # Initialize generator
    generator = ProductImageGenerator(
        api_key=GOOGLE_API_KEY,
        products_file=PRODUCTS_JSON_PATH,
        output_dir=OUTPUT_DIR
    )
    
    try:
        # Process products and generate images
        results = generator.process_products()
        
        # Generate summary report
        generator.generate_summary_report(results)
        
        print("\n✅ Product image generation completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        raise

if __name__ == "__main__":
    main()