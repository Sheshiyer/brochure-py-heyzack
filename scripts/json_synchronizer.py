#!/usr/bin/env python3
"""
JSON Synchronization Utility

This script synchronizes products.json with products_hierarchical_enhanced.json
and ensures data consistency across different JSON formats.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JSONSynchronizer:
    """Synchronize different JSON product formats."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.enhanced_json = self.data_dir / "products_hierarchical_enhanced.json"
        self.products_json = self.data_dir / "products.json"
        self.backup_dir = self.data_dir / "backups"
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(self, file_path: Path) -> bool:
        """Create a backup of the file before modification."""
        if not file_path.exists():
            return True
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}.json"
            backup_path = self.backup_dir / backup_name
            
            with open(file_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            logger.info(f"Created backup: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup for {file_path}: {e}")
            return False
    
    def load_enhanced_data(self) -> Dict[str, Any]:
        """Load enhanced hierarchical JSON data."""
        try:
            with open(self.enhanced_json, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Error loading enhanced JSON: {e}")
            return {}
    
    def load_products_data(self) -> List[Dict[str, Any]]:
        """Load products.json data."""
        try:
            if self.products_json.exists():
                with open(self.products_json, 'r', encoding='utf-8') as file:
                    return json.load(file)
            else:
                return []
        except Exception as e:
            logger.error(f"Error loading products JSON: {e}")
            return []
    
    def convert_enhanced_to_products_format(self, enhanced_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert enhanced hierarchical format to products.json format."""
        products_list = []
        product_counter = 1
        
        for category_name, category_data in enhanced_data.get('categories', {}).items():
            for product in category_data.get('products', []):
                try:
                    # Generate unique ID for products.json format
                    timestamp_ms = int(datetime.now().timestamp() * 1000)
                    product_id = f"product-{timestamp_ms}-{product_counter}"
                    
                    # Convert specifications to string format
                    specs_list = product.get('specifications', [])
                    specifications_text = ' | '.join(specs_list) if specs_list else ''
                    
                    # Extract price information
                    price = product.get('price', 0)
                    if not isinstance(price, (int, float)):
                        price = 0
                    
                    # Create products.json entry
                    product_entry = {
                        'id': product_id,
                        'name': product.get('name', ''),
                        'model': product.get('model_number', ''),
                        'supplier': product.get('supplier', ''),
                        'category': product.get('category', ''),
                        'price': price,
                        'currency': 'USD',
                        'status': 'published',
                        'images': [],
                        'specifications': {
                            'description': product.get('description', ''),
                            'specifications': specifications_text,
                            'features': self._extract_features(specs_list),
                            'communication_protocol': product.get('communication_protocol', ''),
                            'power_source': product.get('power_source', ''),
                            'country': product.get('country', ''),
                            'moq': product.get('moq', ''),
                            'lead_time': product.get('lead_time', '')
                        },
                        'metadata': {
                            'enhanced_id': product.get('id', ''),
                            'drive_link': product.get('drive_link', ''),
                            'price_raw': product.get('price_raw', ''),
                            'ref_heyzack': product.get('ref_heyzack', ''),
                            'designation_fr': product.get('designation_fr', '')
                        },
                        'createdAt': datetime.now().isoformat() + 'Z',
                        'updatedAt': datetime.now().isoformat() + 'Z'
                    }
                    
                    products_list.append(product_entry)
                    product_counter += 1
                    
                except Exception as e:
                    logger.error(f"Error converting product {product.get('name', 'unknown')}: {e}")
                    continue
        
        logger.info(f"Converted {len(products_list)} products to products.json format")
        return products_list
    
    def _extract_features(self, specifications: List[str]) -> str:
        """Extract key features from specifications list."""
        features = []
        
        for spec in specifications:
            if isinstance(spec, str) and '|' in spec:
                # Extract feature name (before the |)
                feature = spec.split('|')[0].strip()
                if feature and feature not in features:
                    features.append(feature)
        
        return ', '.join(features[:5])  # Limit to top 5 features
    
    def generate_products_metadata(self, products_list: List[Dict]) -> Dict[str, Any]:
        """Generate metadata for products.json."""
        categories = set()
        suppliers = set()
        total_value = 0
        price_count = 0
        
        for product in products_list:
            categories.add(product.get('category', ''))
            suppliers.add(product.get('supplier', ''))
            
            price = product.get('price', 0)
            if isinstance(price, (int, float)) and price > 0:
                total_value += price
                price_count += 1
        
        return {
            'total_products': len(products_list),
            'categories_count': len(categories),
            'suppliers_count': len(suppliers),
            'categories': sorted(list(categories)),
            'suppliers': sorted(list(suppliers)),
            'average_price': total_value / price_count if price_count > 0 else 0,
            'last_synchronized': datetime.now().isoformat() + 'Z',
            'source': 'products_hierarchical_enhanced.json'
        }
    
    def save_products_json(self, products_list: List[Dict], include_metadata: bool = True) -> bool:
        """Save products list to products.json."""
        try:
            # Create backup first
            if not self.create_backup(self.products_json):
                logger.warning("Failed to create backup, proceeding anyway")
            
            # Prepare data structure
            if include_metadata:
                data = {
                    'metadata': self.generate_products_metadata(products_list),
                    'products': products_list
                }
            else:
                data = products_list
            
            # Save to file
            with open(self.products_json, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(products_list)} products to products.json")
            return True
            
        except Exception as e:
            logger.error(f"Error saving products.json: {e}")
            return False
    
    def validate_synchronization(self, enhanced_data: Dict, products_list: List[Dict]) -> Dict[str, Any]:
        """Validate that synchronization was successful."""
        validation_result = {
            'success': True,
            'issues': [],
            'statistics': {}
        }
        
        try:
            # Count products in enhanced data
            enhanced_count = 0
            for category_data in enhanced_data.get('categories', {}).values():
                enhanced_count += len(category_data.get('products', []))
            
            products_count = len(products_list)
            
            # Check counts match
            if enhanced_count != products_count:
                validation_result['issues'].append(
                    f"Product count mismatch: enhanced={enhanced_count}, products={products_count}"
                )
                validation_result['success'] = False
            
            # Check for missing required fields
            missing_fields = []
            for i, product in enumerate(products_list[:10]):  # Check first 10 products
                required_fields = ['id', 'name', 'category', 'supplier']
                for field in required_fields:
                    if not product.get(field):
                        missing_fields.append(f"Product {i}: missing {field}")
            
            if missing_fields:
                validation_result['issues'].extend(missing_fields[:5])  # Limit to 5 issues
                validation_result['success'] = False
            
            # Generate statistics
            validation_result['statistics'] = {
                'enhanced_products': enhanced_count,
                'synchronized_products': products_count,
                'categories_in_enhanced': len(enhanced_data.get('categories', {})),
                'unique_categories_in_products': len(set(p.get('category', '') for p in products_list)),
                'validation_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            validation_result['success'] = False
            validation_result['issues'].append(f"Validation error: {e}")
        
        return validation_result
    
    def synchronize(self, validate: bool = True) -> bool:
        """Main synchronization function."""
        logger.info("Starting JSON synchronization")
        
        try:
            # Load enhanced data
            enhanced_data = self.load_enhanced_data()
            if not enhanced_data:
                logger.error("No enhanced data found")
                return False
            
            # Convert to products format
            products_list = self.convert_enhanced_to_products_format(enhanced_data)
            if not products_list:
                logger.error("No products converted")
                return False
            
            # Save products.json
            if not self.save_products_json(products_list):
                return False
            
            # Validate if requested
            if validate:
                validation = self.validate_synchronization(enhanced_data, products_list)
                
                if validation['success']:
                    logger.info("Synchronization validation passed")
                else:
                    logger.warning(f"Synchronization validation issues: {validation['issues']}")
                
                # Save validation report
                validation_path = self.data_dir.parent / "reports" / "synchronization_validation.json"
                with open(validation_path, 'w', encoding='utf-8') as file:
                    json.dump(validation, file, indent=2)
                
                logger.info(f"Validation report saved to {validation_path}")
            
            logger.info("JSON synchronization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error in synchronization: {e}")
            return False
    
    def cleanup_old_backups(self, keep_days: int = 7) -> None:
        """Clean up old backup files."""
        try:
            cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 3600)
            
            for backup_file in self.backup_dir.glob("*.json"):
                if backup_file.stat().st_mtime < cutoff_time:
                    backup_file.unlink()
                    logger.info(f"Removed old backup: {backup_file.name}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")

def main():
    """Main entry point."""
    synchronizer = JSONSynchronizer()
    
    # Clean up old backups first
    synchronizer.cleanup_old_backups()
    
    # Perform synchronization
    success = synchronizer.synchronize()
    
    if success:
        print("✅ JSON synchronization completed successfully")
        sys.exit(0)
    else:
        print("❌ JSON synchronization failed")
        sys.exit(1)

if __name__ == "__main__":
    main()