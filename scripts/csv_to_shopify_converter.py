#!/usr/bin/env python3
"""
CSV to Shopify Format Converter with AI Enhancement

This script converts product_list.csv to Shopify format CSV and uses
OpenRouter's Kimi K2 model to fill missing product data.

Usage:
    python csv_to_shopify_converter.py
"""

import csv
import json
import os
import sys
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to the Python path to import brochure modules
sys.path.append(str(Path(__file__).parent.parent))

@dataclass
class LiteLLMConfig:
    """Configuration for LiteLLM client."""
    api_key: str
    base_url: str
    model: str

class LiteLLMClient:
    """Client for LiteLLM API calls."""
    
    def __init__(self, config: LiteLLMConfig):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
    
    def _make_api_call(self, prompt: str) -> Optional[str]:
        """Make API call to LiteLLM."""
        try:
            payload = {
                "model": self.config.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            response = requests.post(
                f"{self.config.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                print(f"API call failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error making API call: {str(e)}")
            return None

@dataclass
class ConversionStats:
    """Statistics for the conversion process."""
    total_products: int = 0
    successful_conversions: int = 0
    ai_enhancements: int = 0
    failed_conversions: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class ShopifyCSVConverter:
    """Convert product list CSV to Shopify format with AI enhancement."""
    
    def __init__(self, use_ai_enhancement: bool = True):
        self.use_ai_enhancement = use_ai_enhancement
        self.stats = ConversionStats()
        
        # Initialize LiteLLM client
        if self.use_ai_enhancement:
            try:
                self.ai_client = self._create_litellm_client()
                print("✓ LiteLLM client initialized successfully")
            except Exception as e:
                print(f"⚠ Warning: Could not initialize LiteLLM client: {e}")
                self.use_ai_enhancement = False
        
        # Define column mappings from product_list.csv to Shopify format
        self.column_mappings = {
            'Product Name': 'Item Name',
            'Supplier Model Number': 'SKU',
            'Heyzack Refeance Number': 'Part Number',
            'SALES PRICE': 'Selling Price',
            'Price': 'Purchase Price',
            'Potential Supplier': 'Preferred Vendor',
            'MOQ': 'Reorder Level',
            'Main Catagory': 'Product Type',
            'Sub - Category': 'Item Type',
            'Specification': 'Purchase Description',
            'Features': 'Sales Description'
        }
        
        # Define default Shopify values
        self.shopify_defaults = {
            'Is Returnable Item': 'True',
            'Status': 'active',
            'Brand': 'HeyZack',
            'Manufacturer': 'HeyZack',
            'Sales Account': 'shopify',
            'Unit': 'g',
            'Purchase Account': '',
            'Inventory Account': '',
            'Inventory Valuation Method': 'manual',
            'Opening Stock': '1000',
            'Opening Stock Value': '',
            'Is Receivable Service': 'True',
            'Is Combo Product': 'True',
            'Package Weight': '',
            'Package Length': '',
            'Package Width': '',
            'Package Height': '',
            'Weight Unit': 'g',
            'Dimension Unit': '',
            'Tax Name': 'True',
            'Tax Type': '',
            'Tax Percentage': '',
            'Purchase Tax Name': 'True',
            'Purchase Tax Type': '',
            'Purchase Tax Percentage': '',
            'Enable Bin Tracking': ''
        }

    def _create_litellm_client(self) -> LiteLLMClient:
        """Create LiteLLM client configured for Azure model router."""
        api_key = os.getenv('LITELLM_API_KEY')
        base_url = os.getenv('LITELLM_BASE_URL', 'https://litellm-production-dba5.up.railway.app/')
        model = os.getenv('LITELLM_MODEL', 'azure/model-router')
        
        if not api_key:
            raise ValueError("LITELLM_API_KEY not found in environment variables. Please add it to your .env file.")
        
        config = LiteLLMConfig(
            api_key=api_key,
            base_url=base_url.rstrip('/'),  # Remove trailing slash
            model=model
        )
        return LiteLLMClient(config)

    def load_product_list(self, csv_path: str) -> List[Dict[str, Any]]:
        """Load products from the product list CSV."""
        products = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                # Use csv.Sniffer to detect delimiter
                sample = file.read(1024)
                file.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(file, delimiter=delimiter)
                for row in reader:
                    # Clean up column names (remove extra spaces)
                    cleaned_row = {k.strip(): v.strip() if v else '' for k, v in row.items()}
                    products.append(cleaned_row)
                    
            print(f"✓ Loaded {len(products)} products from {csv_path}")
            return products
            
        except Exception as e:
            error_msg = f"Error loading product list: {e}"
            self.stats.errors.append(error_msg)
            print(f"✗ {error_msg}")
            return []

    def enhance_product_with_ai(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to enhance product data and fill missing fields."""
        if not self.use_ai_enhancement:
            return product
            
        try:
            # Create enhancement prompt
            prompt = self._create_enhancement_prompt(product)
            
            # Call AI API
            response = self.ai_client._make_api_call(prompt)
            
            if response:
                enhanced_data = self._parse_ai_response(response)
                if enhanced_data:
                    # Merge enhanced data with original product
                    for key, value in enhanced_data.items():
                        if value and (not product.get(key) or product.get(key) == ''):
                            product[key] = value
                    
                    self.stats.ai_enhancements += 1
                    print(f"  ✓ AI enhanced: {product.get('Product Name', 'Unknown')}")
                    
            return product
            
        except Exception as e:
            print(f"  ⚠ AI enhancement failed for {product.get('Product Name', 'Unknown')}: {e}")
            return product

    def _create_enhancement_prompt(self, product: Dict[str, Any]) -> str:
        """Create AI prompt for product enhancement."""
        product_name = product.get('Product Name', '')
        category = product.get('Main Catagory', '')
        sub_category = product.get('Sub - Category', '')
        specs = product.get('Specification', '')
        features = product.get('Features', '')
        
        prompt = f"""You are a product data specialist. Enhance the following product information for Shopify e-commerce:

Product Name: {product_name}
Category: {category}
Sub-Category: {sub_category}
Current Specifications: {specs}
Current Features: {features}

Please provide enhanced data in JSON format with these fields:
1. "sales_description" - Rich HTML description for customers (include <p>, <ul>, <li> tags)
2. "purchase_description" - Technical specifications for internal use
3. "upc" - Generate a realistic UPC code
4. "ean" - Generate a realistic EAN code
5. "isbn" - Leave empty unless it's a book
6. "package_weight" - Estimated weight in grams
7. "package_length" - Estimated length in cm
8. "package_width" - Estimated width in cm  
9. "package_height" - Estimated height in cm

Focus on creating compelling sales copy while maintaining technical accuracy.

Return ONLY valid JSON in this format:
{{
  "sales_description": "<p>Enhanced HTML description...</p>",
  "purchase_description": "Technical specifications...",
  "upc": "123456789012",
  "ean": "1234567890123",
  "isbn": "",
  "package_weight": "500",
  "package_length": "15",
  "package_width": "10",
  "package_height": "8"
}}"""
        
        return prompt

    def _parse_ai_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse AI response and extract enhanced data."""
        try:
            # Find JSON in response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
                
        except json.JSONDecodeError as e:
            print(f"  ⚠ Failed to parse AI response: {e}")
        except Exception as e:
            print(f"  ⚠ Error parsing AI response: {e}")
            
        return None

    def convert_product_to_shopify(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a single product to Shopify format."""
        shopify_product = {}
        
        # Apply direct column mappings
        for source_col, target_col in self.column_mappings.items():
            if source_col in product:
                shopify_product[target_col] = product[source_col]
        
        # Apply default values
        for col, default_value in self.shopify_defaults.items():
            if col not in shopify_product:
                shopify_product[col] = default_value
        
        # Special handling for specific fields
        self._apply_special_conversions(product, shopify_product)
        
        return shopify_product

    def _apply_special_conversions(self, source: Dict[str, Any], target: Dict[str, Any]):
        """Apply special conversion logic for specific fields."""
        
        # Generate SKU if missing
        if not target.get('SKU'):
            product_name = source.get('Product Name', '')
            # Create SKU from product name
            sku = re.sub(r'[^a-zA-Z0-9]', '-', product_name.lower())
            sku = re.sub(r'-+', '-', sku).strip('-')
            target['SKU'] = f"{sku}-heyzack"
        
        # Handle price formatting
        sales_price = source.get('SALES PRICE', '')
        if sales_price:
            # Remove currency symbols and convert to number
            price_clean = re.sub(r'[^\d.,]', '', sales_price)
            price_clean = price_clean.replace(',', '.')
            try:
                target['Selling Price'] = str(float(price_clean))
            except ValueError:
                target['Selling Price'] = ''
        
        # Handle purchase price
        purchase_price = source.get('Price', '')
        if purchase_price:
            try:
                target['Purchase Price'] = str(float(purchase_price))
            except ValueError:
                target['Purchase Price'] = ''
        
        # Create product handle for Shopify
        product_name = source.get('Product Name', '')
        handle = re.sub(r'[^a-zA-Z0-9]', '-', product_name.lower())
        handle = re.sub(r'-+', '-', handle).strip('-')
        target['Handle'] = handle
        
        # Set opening stock value based on price and quantity
        if target.get('Selling Price') and target.get('Opening Stock'):
            try:
                price = float(target['Selling Price'])
                stock = float(target['Opening Stock'])
                target['Opening Stock Value'] = str(price * stock)
            except ValueError:
                pass

    def _validate_input_file(self, input_csv: str) -> bool:
        """Validate input CSV file exists and has required columns."""
        if not os.path.exists(input_csv):
            error_msg = f"Input file not found: {input_csv}"
            self.stats.errors.append(error_msg)
            print(f"✗ {error_msg}")
            return False
        
        try:
            with open(input_csv, 'r', encoding='utf-8') as file:
                sample = file.read(1024)
                file.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                reader = csv.DictReader(file, delimiter=delimiter)
                headers = reader.fieldnames
                
                # Check for at minimum product name column
                required_columns = ['Product Name']
                missing_columns = [col for col in required_columns if col not in headers]
                
                if missing_columns:
                    error_msg = f"Missing required columns: {missing_columns}"
                    self.stats.errors.append(error_msg)
                    print(f"⚠ Warning: {error_msg}")
                    return False
                
                return True
        except Exception as e:
            error_msg = f"Error validating input file: {e}"
            self.stats.errors.append(error_msg)
            print(f"✗ {error_msg}")
            return False
    
    def _validate_shopify_product(self, product: Dict[str, Any]) -> bool:
        """Validate that a Shopify product has minimum required fields."""
        required_fields = ['Item Name', 'SKU', 'Selling Price']
        missing_fields = [field for field in required_fields if not product.get(field) or str(product.get(field)).strip() == '']
        
        if missing_fields:
            print(f"  ⚠ Warning: Missing required Shopify fields: {missing_fields}")
            return False
        
        # Validate price format
        try:
            price = product.get('Selling Price', '0')
            if price and str(price) != '0':
                float(str(price).replace('$', '').replace(',', ''))
        except ValueError:
            print(f"  ⚠ Warning: Invalid price format: {product.get('Selling Price')}")
            return False
        
        return True

    def convert_csv_to_shopify(self, input_csv: str, output_csv: str) -> bool:
        """Convert entire CSV from product list format to Shopify format."""
        print(f"Starting conversion from {input_csv} to {output_csv}")
        
        # Validate input file
        if not self._validate_input_file(input_csv):
            return False
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_csv)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                print(f"✓ Created output directory: {output_dir}")
            except Exception as e:
                error_msg = f"Failed to create output directory: {e}"
                self.stats.errors.append(error_msg)
                print(f"✗ {error_msg}")
                return False
        
        # Load products
        products = self.load_product_list(input_csv)
        if not products:
            return False
        
        self.stats.total_products = len(products)
        
        # Get Shopify column headers from the sample file
        shopify_headers = self._get_shopify_headers()
        
        converted_products = []
        validation_failures = 0
        
        for i, product in enumerate(products, 1):
            print(f"\nProcessing product {i}/{len(products)}: {product.get('Product Name', 'Unknown')}")
            
            try:
                # Enhance with AI if enabled
                if self.use_ai_enhancement:
                    try:
                        product = self.enhance_product_with_ai(product)
                        # Add small delay to respect API rate limits
                        time.sleep(0.5)
                    except Exception as ai_error:
                        print(f"  ⚠ AI enhancement failed: {ai_error}")
                        # Continue with basic conversion
                
                # Convert to Shopify format
                shopify_product = self.convert_product_to_shopify(product)
                
                # Validate conversion
                if not self._validate_shopify_product(shopify_product):
                    validation_failures += 1
                    # Try to fix missing required fields
                    if not shopify_product.get('Item Name'):
                        shopify_product['Item Name'] = f"Product {i}"
                    if not shopify_product.get('SKU'):
                        shopify_product['SKU'] = f"sku-{i}-heyzack"
                    if not shopify_product.get('Selling Price'):
                        shopify_product['Selling Price'] = '0'
                
                # Ensure all required columns are present
                complete_product = {}
                for header in shopify_headers:
                    complete_product[header] = shopify_product.get(header, '')
                
                converted_products.append(complete_product)
                self.stats.successful_conversions += 1
                
            except Exception as e:
                error_msg = f"Failed to convert product {product.get('Product Name', 'Unknown')}: {e}"
                self.stats.errors.append(error_msg)
                self.stats.failed_conversions += 1
                print(f"  ✗ {error_msg}")
                
                # Try to create a minimal valid product
                try:
                    minimal_product = {
                        'Item Name': product.get('Product Name', f'Product {i}'),
                        'SKU': f'sku-{i}-heyzack',
                        'Selling Price': '0',
                        'Status': 'draft'
                    }
                    
                    complete_product = {}
                    for header in shopify_headers:
                        complete_product[header] = minimal_product.get(header, '')
                    
                    converted_products.append(complete_product)
                    validation_failures += 1
                    print(f"  ✓ Created minimal product entry")
                    
                except Exception as minimal_error:
                    print(f"  ✗ Failed to create minimal product: {minimal_error}")
        
        if validation_failures > 0:
            print(f"\n⚠ Warning: {validation_failures} products had validation issues and were fixed with default values")
        
        # Write to output CSV
        return self._write_shopify_csv(converted_products, shopify_headers, output_csv)

    def _get_shopify_headers(self) -> List[str]:
        """Get Shopify CSV headers from the sample file."""
        shopify_csv_path = Path(__file__).parent.parent / "shofify_formate.csv"
        
        try:
            with open(shopify_csv_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                headers = next(reader)
                return [h.strip() for h in headers]
        except Exception as e:
            print(f"⚠ Could not read Shopify headers from sample file: {e}")
            # Return basic headers as fallback
            return list(self.shopify_defaults.keys()) + ['Item Name', 'SKU', 'Selling Price']

    def _write_shopify_csv(self, products: List[Dict[str, Any]], headers: List[str], output_path: str) -> bool:
        """Write products to Shopify format CSV."""
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()
                writer.writerows(products)
            
            print(f"\n✓ Successfully wrote {len(products)} products to {output_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to write output CSV: {e}"
            self.stats.errors.append(error_msg)
            print(f"✗ {error_msg}")
            return False

    def print_conversion_summary(self):
        """Print conversion statistics."""
        print("\n" + "="*60)
        print("CONVERSION SUMMARY")
        print("="*60)
        print(f"Total products processed: {self.stats.total_products}")
        print(f"Successful conversions: {self.stats.successful_conversions}")
        print(f"AI enhancements applied: {self.stats.ai_enhancements}")
        print(f"Failed conversions: {self.stats.failed_conversions}")
        
        if self.stats.errors:
            print(f"\nErrors encountered: {len(self.stats.errors)}")
            for error in self.stats.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(self.stats.errors) > 5:
                print(f"  ... and {len(self.stats.errors) - 5} more errors")
        
        success_rate = (self.stats.successful_conversions / self.stats.total_products * 100) if self.stats.total_products > 0 else 0
        print(f"\nSuccess rate: {success_rate:.1f}%")
        print("="*60)

def main():
    """Main function to run the conversion."""
    # Define file paths
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    
    input_csv = project_dir / "product_list.csv"
    output_csv = project_dir / "shopify_products_converted.csv"
    
    # Check if input file exists
    if not input_csv.exists():
        print(f"✗ Input file not found: {input_csv}")
        return False
    
    # Create converter
    print("Initializing CSV to Shopify converter...")
    converter = ShopifyCSVConverter(use_ai_enhancement=True)
    
    # Run conversion
    success = converter.convert_csv_to_shopify(str(input_csv), str(output_csv))
    
    # Print summary
    converter.print_conversion_summary()
    
    if success:
        print(f"\n✓ Conversion completed successfully!")
        print(f"Output file: {output_csv}")
        return True
    else:
        print(f"\n✗ Conversion failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)