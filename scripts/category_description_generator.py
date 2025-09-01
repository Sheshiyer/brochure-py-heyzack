#!/usr/bin/env python3
"""
Category Description Generator

This script generates category-wise descriptions for product groupings
and updates the hierarchical JSON structure with category metadata.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any
import logging
from pathlib import Path
from collections import Counter

# Add the project root to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brochure.openrouter_client import create_openrouter_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CategoryDescriptionGenerator:
    """Generate descriptions for product categories."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.enhanced_json = self.data_dir / "products_hierarchical_enhanced.json"
        self.openrouter_client = create_openrouter_client()
        
    def load_enhanced_data(self) -> Dict[str, Any]:
        """Load enhanced JSON data."""
        try:
            with open(self.enhanced_json, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Error loading enhanced JSON: {e}")
            return {}
    
    def analyze_category(self, category_name: str, products: List[Dict]) -> Dict[str, Any]:
        """Analyze a category to extract insights for description generation."""
        analysis = {
            'name': category_name,
            'product_count': len(products),
            'suppliers': [],
            'price_range': {'min': None, 'max': None, 'average': None},
            'common_features': [],
            'communication_protocols': [],
            'power_sources': [],
            'sample_products': []
        }
        
        # Extract suppliers
        suppliers = [p.get('supplier', '') for p in products if p.get('supplier')]
        analysis['suppliers'] = list(set(suppliers))
        
        # Extract price information
        prices = [p.get('price') for p in products if p.get('price') and isinstance(p.get('price'), (int, float))]
        if prices:
            analysis['price_range'] = {
                'min': min(prices),
                'max': max(prices),
                'average': sum(prices) / len(prices)
            }
        
        # Extract communication protocols
        protocols = []
        for product in products:
            protocol = product.get('communication_protocol', '')
            if protocol and protocol != 'Not specified':
                protocols.extend([p.strip() for p in protocol.split(',')])
        analysis['communication_protocols'] = list(set(protocols))
        
        # Extract power sources
        power_sources = [p.get('power_source', '') for p in products if p.get('power_source') and p.get('power_source') != 'Not specified']
        analysis['power_sources'] = list(set(power_sources))
        
        # Extract common features from specifications
        all_specs = []
        for product in products:
            specs = product.get('specifications', [])
            for spec in specs:
                if isinstance(spec, str) and '|' in spec:
                    feature = spec.split('|')[0].strip().lower()
                    all_specs.append(feature)
        
        # Get most common features
        feature_counts = Counter(all_specs)
        analysis['common_features'] = [feature for feature, count in feature_counts.most_common(10)]
        
        # Sample products for reference
        analysis['sample_products'] = [
            {
                'name': p.get('name', ''),
                'supplier': p.get('supplier', ''),
                'model': p.get('model_number', '')
            }
            for p in products[:5]  # First 5 products
        ]
        
        return analysis
    
    def generate_category_description(self, analysis: Dict[str, Any]) -> str:
        """Generate a comprehensive category description using AI."""
        try:
            # Prepare context for AI generation
            category_name = analysis['name']
            product_count = analysis['product_count']
            suppliers = ', '.join(analysis['suppliers'][:5])  # Top 5 suppliers
            protocols = ', '.join(analysis['communication_protocols'][:3])  # Top 3 protocols
            sample_products = [p['name'] for p in analysis['sample_products']]
            
            # Create product data for enhancement
            product_data = {
                'name': f"{category_name} Category Overview",
                'category': category_name,
                'description': f"Smart home {category_name.lower()} devices and solutions",
                'specifications': [
                    f"Product Count|{product_count} products available",
                    f"Suppliers|{suppliers}",
                    f"Communication|{protocols}" if protocols else "Communication|Various protocols",
                    f"Examples|{', '.join(sample_products[:3])}"
                ]
            }
            
            # Use OpenRouter client to generate enhanced description
            enhanced_data = self.openrouter_client.enhance_specifications(product_data)
            
            # Extract the enhanced description
            description = enhanced_data.get('enhanced_description', '')
            
            if description:
                return description
            else:
                return self._generate_fallback_description(analysis)
                
        except Exception as e:
            logger.error(f"Error generating AI description for {analysis['name']}: {e}")
            return self._generate_fallback_description(analysis)
    
    def _generate_fallback_description(self, analysis: Dict[str, Any]) -> str:
        """Generate a fallback description when AI is unavailable."""
        category_name = analysis['name']
        product_count = analysis['product_count']
        
        description = f"Our {category_name} category features {product_count} high-quality smart home devices "
        
        if analysis['suppliers']:
            description += f"from trusted suppliers including {', '.join(analysis['suppliers'][:3])}. "
        
        if analysis['communication_protocols']:
            description += f"These devices support {', '.join(analysis['communication_protocols'][:3])} connectivity "
            description += "for seamless integration with your smart home ecosystem. "
        
        description += f"Perfect for modern homes seeking reliable {category_name.lower()} solutions "
        description += "with advanced features and professional-grade performance."
        
        return description
    
    def generate_category_summary(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a comprehensive category summary."""
        return {
            'name': analysis['name'],
            'description': self.generate_category_description(analysis),
            'product_count': analysis['product_count'],
            'key_suppliers': analysis['suppliers'][:5],
            'supported_protocols': analysis['communication_protocols'],
            'power_options': analysis['power_sources'],
            'price_range': analysis['price_range'],
            'featured_products': analysis['sample_products'][:3],
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def update_enhanced_json_with_categories(self, enhanced_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update enhanced JSON with category descriptions and metadata."""
        logger.info("Generating category descriptions...")
        
        categories_processed = 0
        
        for category_name, category_data in enhanced_data.get('categories', {}).items():
            try:
                products = category_data.get('products', [])
                if not products:
                    continue
                
                # Analyze category
                analysis = self.analyze_category(category_name, products)
                
                # Generate category summary
                category_summary = self.generate_category_summary(analysis)
                
                # Update category data
                category_data.update({
                    'description': category_summary['description'],
                    'metadata': {
                        'product_count': category_summary['product_count'],
                        'key_suppliers': category_summary['key_suppliers'],
                        'supported_protocols': category_summary['supported_protocols'],
                        'power_options': category_summary['power_options'],
                        'price_range': category_summary['price_range'],
                        'featured_products': category_summary['featured_products'],
                        'last_updated': category_summary['last_updated']
                    }
                })
                
                categories_processed += 1
                logger.info(f"Generated description for category: {category_name}")
                
            except Exception as e:
                logger.error(f"Error processing category {category_name}: {e}")
        
        # Update global metadata
        if 'metadata' not in enhanced_data:
            enhanced_data['metadata'] = {}
        
        enhanced_data['metadata'].update({
            'categories_with_descriptions': categories_processed,
            'category_descriptions_generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        logger.info(f"Generated descriptions for {categories_processed} categories")
        return enhanced_data
    
    def save_enhanced_data(self, enhanced_data: Dict[str, Any]) -> bool:
        """Save updated enhanced data to file."""
        try:
            with open(self.enhanced_json, 'w', encoding='utf-8') as file:
                json.dump(enhanced_data, file, indent=2, ensure_ascii=False)
            logger.info("Saved enhanced data with category descriptions")
            return True
        except Exception as e:
            logger.error(f"Error saving enhanced data: {e}")
            return False
    
    def generate_category_report(self, enhanced_data: Dict[str, Any]) -> str:
        """Generate a summary report of all categories."""
        report_lines = [
            "# Category Description Report",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        total_products = 0
        total_categories = len(enhanced_data.get('categories', {}))
        
        for category_name, category_data in enhanced_data.get('categories', {}).items():
            products = category_data.get('products', [])
            product_count = len(products)
            total_products += product_count
            
            report_lines.extend([
                f"## {category_name}",
                f"- **Products**: {product_count}",
                f"- **Description**: {category_data.get('description', 'No description available')[:100]}...",
                ""
            ])
        
        # Add summary
        report_lines.extend([
            "## Summary",
            f"- **Total Categories**: {total_categories}",
            f"- **Total Products**: {total_products}",
            f"- **Average Products per Category**: {total_products / total_categories if total_categories > 0 else 0:.1f}",
            ""
        ])
        
        return "\n".join(report_lines)
    
    def process_categories(self) -> bool:
        """Main processing function."""
        logger.info("Starting category description generation")
        
        try:
            # Load enhanced data
            enhanced_data = self.load_enhanced_data()
            if not enhanced_data:
                logger.error("No enhanced data found")
                return False
            
            # Generate category descriptions
            enhanced_data = self.update_enhanced_json_with_categories(enhanced_data)
            
            # Save updated data
            if not self.save_enhanced_data(enhanced_data):
                return False
            
            # Generate report
            report = self.generate_category_report(enhanced_data)
            report_path = self.data_dir.parent / "reports" / "category_descriptions_report.md"
            
            with open(report_path, 'w', encoding='utf-8') as file:
                file.write(report)
            
            logger.info(f"Category description generation completed. Report saved to {report_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error in category processing: {e}")
            return False

def main():
    """Main entry point."""
    generator = CategoryDescriptionGenerator()
    success = generator.process_categories()
    
    if success:
        print("✅ Category description generation completed successfully")
        sys.exit(0)
    else:
        print("❌ Category description generation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()