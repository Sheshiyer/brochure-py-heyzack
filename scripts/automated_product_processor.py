#!/usr/bin/env python3
"""
Automated Product Processing Pipeline

This script provides a comprehensive pipeline for:
1. Reading products from CSV
2. Detecting new products not in enhanced JSON
3. Applying OpenRouter enhancement to new products
4. Updating hierarchical enhanced JSON
5. Synchronizing with products.json
6. Cleaning up redundant files
"""

import json
import csv
import os
import sys
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
import hashlib
import logging
from pathlib import Path

# Add the project root to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brochure.openrouter_client import create_openrouter_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('product_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProductProcessor:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.csv_file = self.data_dir / "SMART HOME FOLLOWING PROJECT - All Products.csv"
        self.enhanced_json = self.data_dir / "products_hierarchical_enhanced.json"
        self.products_json = self.data_dir / "products.json"
        self.openrouter_client = create_openrouter_client()
        
    def load_csv_products(self) -> List[Dict[str, Any]]:
        """Load all products from CSV file."""
        products = []
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row.get('Drive Link'):  # Only process products with drive links
                        products.append(row)
            logger.info(f"Loaded {len(products)} products from CSV")
            return products
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            return []
    
    def load_enhanced_json(self) -> Dict[str, Any]:
        """Load existing enhanced JSON data."""
        try:
            if self.enhanced_json.exists():
                with open(self.enhanced_json, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                logger.info(f"Loaded enhanced JSON with {data.get('metadata', {}).get('total_products', 0)} products")
                return data
            else:
                logger.info("Enhanced JSON not found, creating new structure")
                return self._create_empty_enhanced_structure()
        except Exception as e:
            logger.error(f"Error loading enhanced JSON: {e}")
            return self._create_empty_enhanced_structure()
    
    def _create_empty_enhanced_structure(self) -> Dict[str, Any]:
        """Create empty enhanced JSON structure."""
        return {
            "metadata": {
                "total_products_in_csv": 0,
                "products_with_drive_links": 0,
                "categories_count": 0,
                "generated_at": datetime.now().strftime("%Y-%m-%d"),
                "enhanced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "enhancement_stats": {
                    "total_products": 0,
                    "enhanced_products": 0,
                    "failed_enhancements": 0,
                    "categories_processed": 0
                }
            },
            "categories": {}
        }
    
    def get_existing_product_ids(self, enhanced_data: Dict[str, Any]) -> Set[str]:
        """Extract all existing product IDs from enhanced JSON."""
        existing_ids = set()
        for category_data in enhanced_data.get("categories", {}).values():
            for product in category_data.get("products", []):
                existing_ids.add(product.get("id", ""))
        return existing_ids
    
    def create_product_id(self, supplier: str, model: str) -> str:
        """Create consistent product ID from supplier and model."""
        return f"{supplier}_{model}".replace(" ", "_").replace("/", "_")
    
    def detect_new_products(self, csv_products: List[Dict], existing_ids: Set[str]) -> List[Dict]:
        """Detect products in CSV that are not in enhanced JSON."""
        new_products = []
        for product in csv_products:
            product_id = self.create_product_id(
                product.get('Supplier', ''),
                product.get('Model', '')
            )
            if product_id not in existing_ids:
                new_products.append(product)
        
        logger.info(f"Found {len(new_products)} new products to process")
        return new_products
    
    def enhance_product_description(self, product: Dict[str, Any]) -> str:
        """Generate enhanced description using OpenRouter."""
        try:
            # Prepare product data for enhancement
            product_data = {
                'name': product.get('Product Name', ''),
                'category': product.get('Category', ''),
                'description': f"Smart home {product.get('Category', '').lower()} device",
                'specifications': self.parse_specifications(product.get('Specifications', ''))
            }
            
            # Use existing OpenRouter client to enhance
            enhanced_data = self.openrouter_client.enhance_specifications(product_data)
            
            # Extract enhanced description
            return enhanced_data.get('enhanced_description', 
                f"High-quality {product.get('Category', '').lower()} device with advanced features and reliable performance.")
            
        except Exception as e:
            logger.error(f"Error enhancing product description: {e}")
            return f"High-quality {product.get('Category', '').lower()} device with advanced features and reliable performance."
    
    def parse_specifications(self, specs_text: str) -> List[str]:
        """Parse specification text into structured list."""
        if not specs_text:
            return []
        
        # Split by common delimiters and clean up
        specs = []
        for line in specs_text.split('|'):
            line = line.strip()
            if line and ':' in line:
                specs.append(line)
            elif line:
                # Handle specs without colons
                specs.append(f"Feature|{line}")
        
        return specs
    
    def convert_csv_to_enhanced_format(self, csv_product: Dict[str, Any]) -> Dict[str, Any]:
        """Convert CSV product to enhanced JSON format."""
        product_id = self.create_product_id(
            csv_product.get('Supplier', ''),
            csv_product.get('Model', '')
        )
        
        # Generate enhanced description
        enhanced_description = self.enhance_product_description(csv_product)
        
        # Parse specifications
        specifications = self.parse_specifications(csv_product.get('Specifications', ''))
        
        # Extract price information
        price_raw = csv_product.get('Price', '')
        price = self._extract_numeric_price(price_raw)
        
        return {
            "id": product_id,
            "supplier": csv_product.get('Supplier', ''),
            "model_number": csv_product.get('Model', ''),
            "name": csv_product.get('Product Name', ''),
            "category": csv_product.get('Category', ''),
            "specifications": specifications,
            "description": enhanced_description,
            "communication_protocol": self._extract_communication_protocol(specifications),
            "power_source": self._extract_power_source(specifications),
            "country": csv_product.get('Country', None),
            "image": None,
            "price": price,
            "price_raw": price_raw,
            "moq": csv_product.get('MOQ', ''),
            "catalogue": csv_product.get('Catalogue', None),
            "packing": csv_product.get('Packing', None),
            "status": csv_product.get('Status', ''),
            "designation_fr": csv_product.get('Designation FR', None),
            "ref_heyzack": csv_product.get('Ref HeyZack', None),
            "drive_link": csv_product.get('Drive Link', ''),
            "lead_time": csv_product.get('Lead Time', None)
        }
    
    def _extract_numeric_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from price text."""
        if not price_text:
            return None
        
        import re
        # Extract first number found in the text
        match = re.search(r'([0-9]+\.?[0-9]*)', price_text.replace(',', ''))
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None
    
    def _extract_communication_protocol(self, specifications: List[str]) -> str:
        """Extract communication protocol from specifications."""
        protocols = []
        for spec in specifications:
            spec_lower = spec.lower()
            if 'wi-fi' in spec_lower or 'wifi' in spec_lower:
                protocols.append('Wi-Fi')
            if 'bluetooth' in spec_lower:
                protocols.append('Bluetooth')
            if 'zigbee' in spec_lower:
                protocols.append('Zigbee')
            if 'z-wave' in spec_lower:
                protocols.append('Z-Wave')
        
        return ', '.join(list(set(protocols))) if protocols else 'Not specified'
    
    def _extract_power_source(self, specifications: List[str]) -> str:
        """Extract power source from specifications."""
        for spec in specifications:
            spec_lower = spec.lower()
            if 'battery' in spec_lower:
                return 'Battery powered'
            if 'ac' in spec_lower or 'hardwire' in spec_lower:
                return 'AC powered'
            if 'usb' in spec_lower:
                return 'USB powered'
            if 'solar' in spec_lower:
                return 'Solar powered'
        
        return 'Not specified'
    
    def add_products_to_enhanced_json(self, enhanced_data: Dict[str, Any], new_products: List[Dict]) -> Dict[str, Any]:
        """Add new products to enhanced JSON structure."""
        enhanced_count = 0
        failed_count = 0
        categories_updated = set()
        
        for csv_product in new_products:
            try:
                enhanced_product = self.convert_csv_to_enhanced_format(csv_product)
                category = enhanced_product['category']
                
                # Initialize category if it doesn't exist
                if category not in enhanced_data['categories']:
                    enhanced_data['categories'][category] = {
                        'name': category,
                        'products': []
                    }
                
                # Add product to category
                enhanced_data['categories'][category]['products'].append(enhanced_product)
                enhanced_count += 1
                categories_updated.add(category)
                
                logger.info(f"Enhanced product: {enhanced_product['name']} ({enhanced_product['id']})")
                
            except Exception as e:
                logger.error(f"Failed to enhance product {csv_product.get('Product Name', 'Unknown')}: {e}")
                failed_count += 1
        
        # Update metadata
        enhanced_data['metadata'].update({
            'enhanced_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'categories_count': len(enhanced_data['categories']),
            'enhancement_stats': {
                'total_products': sum(len(cat['products']) for cat in enhanced_data['categories'].values()),
                'enhanced_products': enhanced_count,
                'failed_enhancements': failed_count,
                'categories_processed': len(categories_updated)
            }
        })
        
        return enhanced_data
    
    def save_enhanced_json(self, enhanced_data: Dict[str, Any]) -> bool:
        """Save enhanced JSON data to file."""
        try:
            with open(self.enhanced_json, 'w', encoding='utf-8') as file:
                json.dump(enhanced_data, file, indent=2, ensure_ascii=False)
            logger.info(f"Saved enhanced JSON with {enhanced_data['metadata']['enhancement_stats']['total_products']} products")
            return True
        except Exception as e:
            logger.error(f"Error saving enhanced JSON: {e}")
            return False
    
    def sync_products_json(self, enhanced_data: Dict[str, Any]) -> bool:
        """Synchronize products.json with enhanced data."""
        try:
            products_list = []
            product_id_counter = 1
            
            for category_data in enhanced_data.get('categories', {}).values():
                for product in category_data.get('products', []):
                    # Convert to products.json format
                    product_entry = {
                        'id': f"product-{int(datetime.now().timestamp() * 1000)}-{product_id_counter}",
                        'name': product.get('name', ''),
                        'model': product.get('model_number', ''),
                        'supplier': product.get('supplier', ''),
                        'category': product.get('category', ''),
                        'price': product.get('price', 0) or 0,
                        'currency': 'USD',
                        'status': 'published',
                        'images': [],
                        'specifications': {
                            'description': product.get('description', ''),
                            'specifications': ' | '.join(product.get('specifications', [])),
                            'features': ''
                        },
                        'createdAt': datetime.now().isoformat() + 'Z',
                        'updatedAt': datetime.now().isoformat() + 'Z'
                    }
                    products_list.append(product_entry)
                    product_id_counter += 1
            
            # Save products.json
            with open(self.products_json, 'w', encoding='utf-8') as file:
                json.dump(products_list, file, indent=2, ensure_ascii=False)
            
            logger.info(f"Synchronized products.json with {len(products_list)} products")
            return True
            
        except Exception as e:
            logger.error(f"Error synchronizing products.json: {e}")
            return False
    
    def cleanup_redundant_files(self) -> None:
        """Clean up redundant and outdated JSON files."""
        redundant_files = [
            'products_hierarchical.json',
            'products_hierarchical_enhanced_v2.json',
            'products_hierarchical_fixed.json',
            'sample_enhancement.json'
        ]
        
        for filename in redundant_files:
            file_path = self.data_dir / filename
            if file_path.exists():
                try:
                    file_path.unlink()
                    logger.info(f"Removed redundant file: {filename}")
                except Exception as e:
                    logger.error(f"Error removing {filename}: {e}")
    
    def process_new_products(self) -> bool:
        """Main processing pipeline."""
        logger.info("Starting automated product processing pipeline")
        
        try:
            # Step 1: Load data
            csv_products = self.load_csv_products()
            if not csv_products:
                logger.warning("No products found in CSV")
                return False
            
            enhanced_data = self.load_enhanced_json()
            existing_ids = self.get_existing_product_ids(enhanced_data)
            
            # Step 2: Detect new products
            new_products = self.detect_new_products(csv_products, existing_ids)
            if not new_products:
                logger.info("No new products to process")
                return True
            
            # Step 3: Enhance new products
            enhanced_data = self.add_products_to_enhanced_json(enhanced_data, new_products)
            
            # Step 4: Save enhanced JSON
            if not self.save_enhanced_json(enhanced_data):
                return False
            
            # Step 5: Sync products.json
            if not self.sync_products_json(enhanced_data):
                return False
            
            # Step 6: Cleanup redundant files
            self.cleanup_redundant_files()
            
            logger.info("Product processing pipeline completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error in processing pipeline: {e}")
            return False

def main():
    """Main entry point."""
    processor = ProductProcessor()
    success = processor.process_new_products()
    
    if success:
        print("✅ Product processing completed successfully")
        sys.exit(0)
    else:
        print("❌ Product processing failed")
        sys.exit(1)

if __name__ == "__main__":
    main()