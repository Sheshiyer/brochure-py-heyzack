#!/usr/bin/env python3

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

def clean_text(text):
    """Clean and normalize text fields"""
    if not text or text.strip() == '':
        return None
    return text.strip()

def parse_price(price_str):
    """Extract numeric price from price string"""
    if not price_str:
        return None
    # Extract numbers and decimal points from price string
    price_match = re.search(r'\$?([0-9]+\.?[0-9]*)', str(price_str))
    if price_match:
        return float(price_match.group(1))
    return None

def parse_specifications(spec_str):
    """Parse specifications string into structured format"""
    if not spec_str:
        return []
    
    # Split by | and clean up each specification
    specs = []
    parts = spec_str.split('|')
    
    for part in parts:
        part = part.strip()
        if part and len(part) > 3:  # Filter out very short parts
            # Remove common prefixes
            part = re.sub(r'^(Features?:|Specifications?:)\s*', '', part, flags=re.IGNORECASE)
            specs.append(part)
    
    return specs

def transform_csv_to_hierarchical_json(csv_file_path, output_file_path):
    """Transform CSV data into hierarchical JSON structure"""
    
    # Dictionary to store hierarchical data
    categories = defaultdict(lambda: {
        'name': '',
        'products': []
    })
    
    total_products = 0
    products_with_links = 0
    
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            total_products += 1
            
            # Only include products with drive links
            drive_link = clean_text(row.get('Drive Link', ''))
            if not drive_link or 'drive.google.com' not in drive_link:
                continue
                
            products_with_links += 1
            
            # Extract and clean data
            category = clean_text(row.get('Category', 'Uncategorized'))
            supplier = clean_text(row.get('Supplier', ''))
            model_number = clean_text(row.get('Model Number', ''))
            product_name = clean_text(row.get('Product Name', ''))
            specifications = clean_text(row.get('Specifications', ''))
            communication_protocol = clean_text(row.get('Communitcation protocol', ''))
            power_source = clean_text(row.get('Power Source', ''))
            country = clean_text(row.get('Country', ''))
            image = clean_text(row.get('Image', ''))
            price_str = clean_text(row.get('Price', ''))
            moq = clean_text(row.get('MOQ', ''))
            catalogue = clean_text(row.get('Catalogue', ''))
            packing = clean_text(row.get('Packing', ''))
            status = clean_text(row.get('Status', ''))
            designation_fr = clean_text(row.get('DESIGNATION FR', ''))
            ref_heyzack = clean_text(row.get('REF HEYZACK', ''))
            lead_time = clean_text(row.get('Lead Time', ''))
            
            # Parse price
            price = parse_price(price_str)
            
            # Parse specifications into list
            spec_list = parse_specifications(specifications)
            
            # Create product object
            product = {
                'id': f"{supplier}_{model_number}".replace(' ', '_') if supplier and model_number else f"product_{products_with_links}",
                'supplier': supplier,
                'model_number': model_number,
                'name': product_name,
                'category': category,
                'specifications': spec_list,
                'description': specifications,  # Keep original for backward compatibility
                'communication_protocol': communication_protocol,
                'power_source': power_source,
                'country': country,
                'image': image,
                'price': price,
                'price_raw': price_str,
                'moq': moq,
                'catalogue': catalogue,
                'packing': packing,
                'status': status,
                'designation_fr': designation_fr,
                'ref_heyzack': ref_heyzack,
                'drive_link': drive_link,
                'lead_time': lead_time
            }
            
            # Add to category
            if category not in categories:
                categories[category]['name'] = category
            
            categories[category]['products'].append(product)
    
    # Convert to final structure
    result = {
        'metadata': {
            'total_products_in_csv': total_products,
            'products_with_drive_links': products_with_links,
            'categories_count': len(categories),
            'generated_at': '2025-01-21'
        },
        'categories': dict(categories)
    }
    
    # Write to JSON file
    with open(output_file_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(result, jsonfile, indent=2, ensure_ascii=False)
    
    print(f"Transformation complete!")
    print(f"Total products in CSV: {total_products}")
    print(f"Products with drive links: {products_with_links}")
    print(f"Categories found: {len(categories)}")
    print(f"Categories: {list(categories.keys())}")
    print(f"Output saved to: {output_file_path}")
    
    return result

if __name__ == '__main__':
    csv_path = '/Users/sheshnarayaniyer/2025/brochure-py/SMART HOME FOLLOWING PROJECT - All Products.csv'
    json_path = '/Users/sheshnarayaniyer/2025/brochure-py/products_hierarchical.json'
    
    transform_csv_to_hierarchical_json(csv_path, json_path)