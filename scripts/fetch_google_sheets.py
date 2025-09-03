#!/usr/bin/env python3
"""
Google Sheets to Products JSON Converter
Fetches data from Google Sheets and converts it to the products.json format
"""

import json
import requests
import pandas as pd
from datetime import datetime
import time
import re
from typing import Dict, List, Any, Optional
import logging
from io import StringIO

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GoogleSheetsToProducts:
    def __init__(self, sheet_url: str):
        self.sheet_url = sheet_url
        self.sheet_id = self._extract_sheet_id(sheet_url)
        self.csv_export_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/export?format=csv&gid=1707985453"
        
    def _extract_sheet_id(self, url: str) -> str:
        """Extract sheet ID from Google Sheets URL"""
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Could not extract sheet ID from URL")
    
    def fetch_csv_data(self) -> pd.DataFrame:
        """Fetch CSV data from Google Sheets"""
        try:
            logger.info(f"Fetching data from Google Sheets: {self.sheet_url}")
            response = requests.get(self.csv_export_url, timeout=30)
            response.raise_for_status()
            
            # Read CSV data
            csv_content = response.text
            df = pd.read_csv(StringIO(csv_content))
            
            logger.info(f"Successfully fetched {len(df)} rows from Google Sheets")
            return df
            
        except requests.RequestException as e:
            logger.error(f"Error fetching data from Google Sheets: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing CSV data: {e}")
            raise
    
    def clean_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize column names"""
        # Remove extra whitespace and special characters
        df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('\r', ' ')
        
        # Map your specific column names to JSON keys
        column_mapping = {
            'Model Number': 'model',
            'Product Name': 'name',
            'Category': 'category',
            'Specifications': 'specifications',
            'Features': 'features',
            'Hero Image': 'hero_image',
            'Secoundry Image': 'secondary_image'
        }
        
        # Rename columns
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        return df
    
    def parse_specifications(self, specs_str: str) -> Dict[str, Any]:
        """Parse specifications string into structured format"""
        if pd.isna(specs_str) or not specs_str:
            return {}
        
        specs_str = str(specs_str).strip()
        
        # Try to parse pipe-separated specifications
        if '|' in specs_str:
            specs_dict = {}
            try:
                # Split by | and process each spec
                spec_parts = specs_str.split('|')
                for i in range(0, len(spec_parts) - 1, 2):
                    if i + 1 < len(spec_parts):
                        key = spec_parts[i].strip()
                        value = spec_parts[i + 1].strip()
                        if key and value:
                            specs_dict[key] = value
                
                return {
                    "specifications": specs_dict,
                    "description": specs_str[:200] + "..." if len(specs_str) > 200 else specs_str
                }
            except Exception as e:
                logger.warning(f"Error parsing specifications '{specs_str}': {e}")
                return {
                    "specifications": specs_str,
                    "description": specs_str[:200] + "..." if len(specs_str) > 200 else specs_str
                }
        else:
            # Single specification or description
            return {
                "specifications": specs_str,
                "description": specs_str[:200] + "..." if len(specs_str) > 200 else specs_str
            }
    
    def parse_features(self, features_str: str) -> List[str]:
        """Parse features string into list"""
        if pd.isna(features_str) or not features_str:
            return []
        
        features_str = str(features_str).strip()
        
        # Split by common separators
        if ',' in features_str:
            features = [f.strip() for f in features_str.split(',') if f.strip()]
        elif ';' in features_str:
            features = [f.strip() for f in features_str.split(';') if f.strip()]
        elif '|' in features_str:
            features = [f.strip() for f in features_str.split('|') if f.strip()]
        else:
            features = [features_str] if features_str else []
        
        return features
    
    def parse_price(self, price_str: str) -> Optional[float]:
        """Parse price string to float"""
        if pd.isna(price_str) or not price_str:
            return None
        
        price_str = str(price_str).strip()
        
        # Remove currency symbols and common text
        price_str = re.sub(r'[^\d.,]', '', price_str)
        
        try:
            # Handle different decimal separators
            if ',' in price_str and '.' in price_str:
                # European format: 1.234,56 -> 1234.56
                if price_str.find(',') > price_str.find('.'):
                    price_str = price_str.replace('.', '').replace(',', '.')
                else:
                    price_str = price_str.replace(',', '')
            elif ',' in price_str:
                # Check if comma is decimal separator
                if len(price_str.split(',')[-1]) <= 2:
                    price_str = price_str.replace(',', '.')
                else:
                    price_str = price_str.replace(',', '')
            
            return float(price_str)
        except ValueError:
            logger.warning(f"Could not parse price: {price_str}")
            return None
    
    def convert_row_to_product(self, row: pd.Series, index: int) -> Dict[str, Any]:
        """Convert a DataFrame row to product format"""
        # Get image URLs
        hero_image = str(row.get('hero_image', '')).strip() if pd.notna(row.get('hero_image')) else ''
        secondary_image = str(row.get('secondary_image', '')).strip() if pd.notna(row.get('secondary_image')) else ''
        
        # Build product object with only the fields you need
        product = {
            "name": str(row.get('name', '')).strip() if pd.notna(row.get('name')) else '',
            "model": str(row.get('model', '')).strip() if pd.notna(row.get('model')) else '',
            "category": str(row.get('category', '')).strip() if pd.notna(row.get('category')) else '',
            "specifications": str(row.get('specifications', '')).strip() if pd.notna(row.get('specifications')) else '',
            "features": str(row.get('features', '')).strip() if pd.notna(row.get('features')) else '',
            "hero_image": hero_image,
            "secondary_image": secondary_image
        }
        
        return product
    
    def generate_metadata(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate metadata for the products collection"""
        # Extract unique categories
        categories = list(set(p['category'] for p in products if p['category']))
        
        return {
            "total_products": len(products),
            "categories_count": len(categories),
            "categories": sorted(categories),
            "last_synchronized": datetime.utcnow().isoformat() + "Z",
            "source": "google_sheets_import"
        }
    
    def convert_to_products_json(self) -> Dict[str, Any]:
        """Main conversion method"""
        try:
            # Fetch data from Google Sheets
            df = self.fetch_csv_data()
            
            # Clean column names
            df = self.clean_column_names(df)
            
            # Remove empty rows
            df = df.dropna(subset=['name', 'model']).reset_index(drop=True)
            
            # Convert rows to products
            products = []
            for index, row in df.iterrows():
                try:
                    product = self.convert_row_to_product(row, index)
                    products.append(product)
                except Exception as e:
                    logger.error(f"Error converting row {index}: {e}")
                    continue
            
            # Generate metadata
            metadata = self.generate_metadata(products)
            
            # Create final structure
            result = {
                "metadata": metadata,
                "products": products
            }
            
            logger.info(f"Successfully converted {len(products)} products")
            return result
            
        except Exception as e:
            logger.error(f"Error in conversion process: {e}")
            raise
    
    def save_to_file(self, data: Dict[str, Any], output_path: str = "data/products_from_sheets.json"):
        """Save data to JSON file"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Data saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving to file: {e}")
            raise

def main():
    """Main execution function"""
    # Google Sheets URL
    sheet_url = "https://docs.google.com/spreadsheets/d/17xcmTsSZkguOjXC6h6YDrNcOU27jrpU8Ah9xEONARg8/edit?gid=1707985453#gid=1707985453"
    
    try:
        # Create converter instance
        converter = GoogleSheetsToProducts(sheet_url)
        
        # Convert data
        products_data = converter.convert_to_products_json()
        
        # Save to data folder as products.json
        converter.save_to_file(products_data, "data/products.json")
        
        # Also save as backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"data/products_backup_{timestamp}.json"
        converter.save_to_file(products_data, backup_path)
        
        print(f"✅ Successfully converted {products_data['metadata']['total_products']} products")
        print(f"📁 Main file: data/products.json")
        print(f"📁 Backup file: {backup_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Main execution failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
