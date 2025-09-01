"""Product data parser for the HeyZack brochure generator."""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NormalizedProduct:
    """Normalized product data structure."""
    id: str
    name: str
    model: str
    supplier: str
    category: str
    price: float
    status: str
    images: List[str]
    description: str
    short_description: Optional[str]
    specifications: Dict[str, Any]
    features: List[str]
    
    @property
    def is_active(self) -> bool:
        """Check if product is active/available."""
        return self.status.lower() in ['active', 'available', 'in_stock']
    
    @property
    def primary_image(self) -> Optional[str]:
        """Get the primary product image."""
        return self.images[0] if self.images else None


class ProductParser:
    """Parser for products.json files."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def parse_products(self, products_data: List[Dict[str, Any]], 
                      include_models: Optional[List[str]] = None) -> List[NormalizedProduct]:
        """Parse and normalize product data.
        
        Args:
            products_data: Raw product data from JSON
            include_models: Optional list of models to include
            
        Returns:
            List of normalized products
        """
        normalized_products = []
        
        for product_data in products_data:
            try:
                # Apply model filter if specified
                if include_models and product_data.get('model') not in include_models:
                    continue
                
                normalized_product = self._normalize_product(product_data)
                if normalized_product:
                    normalized_products.append(normalized_product)
                    
            except Exception as e:
                self.logger.warning(f"Failed to parse product {product_data.get('id', 'unknown')}: {e}")
                continue
        
        self.logger.info(f"Successfully parsed {len(normalized_products)} products")
        return normalized_products
    
    def _normalize_product(self, product_data: Dict[str, Any]) -> Optional[NormalizedProduct]:
        """Normalize a single product.
        
        Args:
            product_data: Raw product data
            
        Returns:
            Normalized product or None if invalid
        """
        try:
            # Extract basic fields
            product_id = str(product_data.get('id', ''))
            name = product_data.get('name', '').strip()
            model = product_data.get('model', '').strip()
            supplier = product_data.get('supplier', '').strip()
            category = product_data.get('category', '').strip()
            status = product_data.get('status', 'unknown').strip()
            
            # Validate required fields
            if not all([product_id, name, model]):
                self.logger.warning(f"Product missing required fields: {product_data}")
                return None
            
            # Parse price
            price = 0.0
            try:
                price_value = product_data.get('price', 0)
                if isinstance(price_value, str):
                    # Remove currency symbols and convert
                    price_clean = price_value.replace('$', '').replace(',', '').strip()
                    price = float(price_clean)
                else:
                    price = float(price_value)
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid price for product {product_id}: {product_data.get('price')}")
            
            # Parse images
            images = []
            images_data = product_data.get('images', [])
            if isinstance(images_data, list):
                images = [img for img in images_data if isinstance(img, str) and img.strip()]
            elif isinstance(images_data, str):
                images = [images_data.strip()] if images_data.strip() else []
            
            # Parse specifications
            specs_data = product_data.get('specifications', {})
            description = ''
            specifications = {}
            features = []
            
            if isinstance(specs_data, dict):
                description = specs_data.get('description', '').strip()
                specifications = specs_data.get('specifications', {})
                features_data = specs_data.get('features', [])
                
                if isinstance(features_data, list):
                    features = [f for f in features_data if isinstance(f, str) and f.strip()]
                elif isinstance(features_data, str):
                    features = [features_data.strip()] if features_data.strip() else []
                
                # If no features found but description exists, extract from description
                if not features and description:
                    # Split by pipe separator and clean up
                    raw_features = description.split('|')
                    for feature in raw_features:
                        feature = feature.strip()
                        if feature and len(feature) > 10:  # Filter out very short items
                            # Clean up common prefixes
                            if feature.startswith('Features:'):
                                feature = feature[9:].strip()
                            elif feature.startswith('Specifications:'):
                                feature = feature[14:].strip()
                            
                            # Split multiple features in one line
                            if ' | ' in feature:
                                sub_features = feature.split(' | ')
                                for sub_feature in sub_features:
                                    sub_feature = sub_feature.strip()
                                    if sub_feature and len(sub_feature) > 5:
                                        features.append(sub_feature)
                            else:
                                features.append(feature)
            
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
                specifications=specifications,
                features=features
            )
            
        except Exception as e:
            self.logger.error(f"Error normalizing product {product_data.get('id', 'unknown')}: {e}")
            return None
    
    def group_by_category(self, products: List[NormalizedProduct]) -> Dict[str, List[NormalizedProduct]]:
        """Group products by category.
        
        Args:
            products: List of normalized products
            
        Returns:
            Dictionary mapping categories to product lists
        """
        grouped = {}
        for product in products:
            category = product.category or 'Uncategorized'
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(product)
        
        return grouped
    
    def filter_active_products(self, products: List[NormalizedProduct]) -> List[NormalizedProduct]:
        """Filter to only active/available products.
        
        Args:
            products: List of normalized products
            
        Returns:
            List of active products
        """
        return [p for p in products if p.is_active]