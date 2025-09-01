#!/usr/bin/env python3
"""Hierarchical product data loader for the HeyZack brochure generator."""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .parser import NormalizedProduct

logger = logging.getLogger(__name__)


class HierarchicalProductLoader:
    """Loader for hierarchical product data structure."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def load_products(self, file_path: str, 
                     include_categories: Optional[List[str]] = None,
                     include_models: Optional[List[str]] = None) -> List[NormalizedProduct]:
        """Load products from hierarchical JSON structure.
        
        Args:
            file_path: Path to hierarchical JSON file
            include_categories: Optional list of categories to include
            include_models: Optional list of models to include
            
        Returns:
            List of normalized products
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.logger.info(f"Loaded hierarchical data with {data['metadata']['products_with_drive_links']} products")
            
            normalized_products = []
            categories = data.get('categories', {})
            
            for category_name, category_data in categories.items():
                # Apply category filter if specified
                if include_categories and category_name not in include_categories:
                    continue
                
                products = category_data.get('products', [])
                
                for product_data in products:
                    # Apply model filter if specified
                    if include_models and product_data.get('model_number') not in include_models:
                        continue
                    
                    normalized_product = self._convert_to_normalized_product(product_data)
                    if normalized_product:
                        normalized_products.append(normalized_product)
            
            self.logger.info(f"Successfully loaded {len(normalized_products)} products")
            return normalized_products
            
        except Exception as e:
            self.logger.error(f"Failed to load hierarchical products from {file_path}: {e}")
            raise
    
    def _convert_to_normalized_product(self, product_data: Dict[str, Any]) -> Optional[NormalizedProduct]:
        """Convert hierarchical product data to NormalizedProduct.
        
        Args:
            product_data: Product data from hierarchical structure
            
        Returns:
            NormalizedProduct instance or None if invalid
        """
        try:
            # Map hierarchical fields to normalized structure
            product_id = product_data.get('id', '')
            name = (product_data.get('name') or '').strip()
            model = (product_data.get('model_number') or '').strip()
            supplier = (product_data.get('supplier') or '').strip()
            category = (product_data.get('category') or '').strip()
            status = (product_data.get('status') or 'unknown').strip()
            
            # Validate required fields
            if not all([product_id, name]):
                self.logger.warning(f"Product missing required fields: {product_data}")
                return None
            
            # Parse price
            price = 0.0
            if product_data.get('price') is not None:
                price = float(product_data['price'])
            
            # Handle images - check multiple possible fields
            images = []
            if product_data.get('image'):
                images.append(product_data['image'])
            if product_data.get('drive_link'):
                # Convert Google Drive view URL to direct image URL
                drive_url = self._convert_drive_url_to_direct(product_data['drive_link'])
                images.append(drive_url)
            
            # Get description and specifications
            description = (product_data.get('description') or '').strip()
            specifications = product_data.get('specifications', [])
            
            # Convert specifications list to features
            features = []
            if isinstance(specifications, list):
                for spec in specifications:
                    if isinstance(spec, str) and spec.strip():
                        # Split pipe-separated specifications into individual features
                        if '|' in spec:
                            # Parse pipe-separated key|value pairs
                            parts = [part.strip() for part in spec.split('|') if part.strip()]
                            for i in range(0, len(parts), 2):
                                if i + 1 < len(parts):
                                    key = parts[i]
                                    value = parts[i + 1]
                                    features.append(f"{key}: {value}")
                                else:
                                    # Single value without pair
                                    features.append(parts[i])
                        else:
                            # Regular specification without pipes
                            features.append(spec.strip())
            elif isinstance(specifications, str):
                # Split by common separators and format properly
                if '|' in specifications:
                    parts = [part.strip() for part in specifications.split('|') if part.strip()]
                    for i in range(0, len(parts), 2):
                        if i + 1 < len(parts):
                            key = parts[i]
                            value = parts[i + 1]
                            features.append(f"{key}: {value}")
                        else:
                            features.append(parts[i])
                else:
                    features = [specifications.strip()]
            
            # Create specifications dict for compatibility
            specs_dict = {
                'communication_protocol': product_data.get('communication_protocol', ''),
                'power_source': product_data.get('power_source', ''),
                'country': product_data.get('country', ''),
                'moq': product_data.get('moq', ''),
                'lead_time': product_data.get('lead_time', ''),
                'ref_heyzack': product_data.get('ref_heyzack', ''),
                'designation_fr': product_data.get('designation_fr', '')
            }
            
            # Extract short description
            short_description = product_data.get('short_description', '').strip() or None
            
            return NormalizedProduct(
                id=product_id,
                name=name,
                model=model,
                supplier=supplier,
                category=category,
                price=price,
                status=status,
                images=images,
                description=description,
                short_description=short_description,
                specifications=specs_dict,
                features=features
            )
            
        except Exception as e:
            self.logger.error(f"Error converting product {product_data.get('id', 'unknown')}: {e}")
            return None
    
    def _convert_drive_url_to_direct(self, drive_url: str) -> str:
        """Convert Google Drive view URL to direct image URL.
        
        Args:
            drive_url: Google Drive URL in view format
            
        Returns:
            Direct image URL or original URL if conversion fails
        """
        try:
            # Extract file ID from Google Drive URL
            # Format: https://drive.google.com/file/d/FILE_ID/view?usp=...
            if 'drive.google.com/file/d/' in drive_url and '/view' in drive_url:
                # Extract file ID
                start = drive_url.find('/file/d/') + 8
                end = drive_url.find('/view')
                if start > 7 and end > start:
                    file_id = drive_url[start:end]
                    # Convert to direct image URL
                    direct_url = f"https://drive.google.com/uc?export=view&id={file_id}"
                    self.logger.debug(f"Converted Drive URL: {drive_url} -> {direct_url}")
                    return direct_url
            
            # Return original URL if conversion not possible
            return drive_url
            
        except Exception as e:
            self.logger.warning(f"Failed to convert Drive URL {drive_url}: {e}")
            return drive_url
    
    def get_available_categories(self, file_path: str) -> List[str]:
        """Get list of available categories from hierarchical data.
        
        Args:
            file_path: Path to hierarchical JSON file
            
        Returns:
            List of category names
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            categories = list(data.get('categories', {}).keys())
            self.logger.info(f"Found {len(categories)} categories: {categories}")
            return categories
            
        except Exception as e:
            self.logger.error(f"Failed to get categories from {file_path}: {e}")
            return []
    
    def get_products_by_category(self, file_path: str, category: str) -> List[Dict[str, Any]]:
        """Get products for a specific category.
        
        Args:
            file_path: Path to hierarchical JSON file
            category: Category name
            
        Returns:
            List of product data for the category
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            categories = data.get('categories', {})
            if category not in categories:
                self.logger.warning(f"Category '{category}' not found")
                return []
            
            products = categories[category].get('products', [])
            self.logger.info(f"Found {len(products)} products in category '{category}'")
            return products
            
        except Exception as e:
            self.logger.error(f"Failed to get products for category '{category}': {e}")
            return []