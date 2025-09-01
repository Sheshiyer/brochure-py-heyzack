#!/usr/bin/env python3

import json
import time
from typing import Dict, List, Any
from brochure.openrouter_client import create_openrouter_client

def enhance_product_specifications(input_file: str = 'products_hierarchical.json', 
                                 output_file: str = 'products_hierarchical_enhanced.json',
                                 delay: float = 2.0,
                                 test_mode: bool = False,
                                 test_limit: int = 3) -> None:
    """Enhance product specifications using OpenRouter API."""
    
    print("Loading product data...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create OpenRouter client
    client = create_openrouter_client()
    
    # Track enhancement statistics
    stats = {
        'total_products': 0,
        'enhanced_products': 0,
        'failed_enhancements': 0,
        'categories_processed': 0,
        'start_time': time.time()
    }
    
    print(f"Starting enhancement process...")
    if test_mode:
        print(f"Running in TEST MODE - processing only {test_limit} products per category")
    
    enhanced_data = data.copy()
    
    for category_name, category_data in enhanced_data.get('categories', {}).items():
        if 'products' not in category_data:
            continue
            
        stats['categories_processed'] += 1
        products = category_data['products']
        
        print(f"\n{'='*60}")
        print(f"Processing category: {category_name} ({len(products)} products)")
        print(f"{'='*60}")
        
        # Limit products in test mode
        if test_mode:
            products = products[:test_limit]
            category_data['products'] = products
        
        for i, product in enumerate(products):
            stats['total_products'] += 1
            product_name = product.get('name', 'Unknown')
            product_id = product.get('id', 'Unknown')
            
            print(f"\n[{i+1}/{len(products)}] Enhancing: {product_name} ({product_id})")
            
            try:
                # Enhance the product
                enhanced_product = client.enhance_specifications(product)
                
                # Update the product in the data structure
                category_data['products'][i] = enhanced_product
                stats['enhanced_products'] += 1
                
                print(f"  ✓ Successfully enhanced")
                
                # Add delay to respect rate limits
                if delay > 0:
                    print(f"  ⏳ Waiting {delay}s before next request...")
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"  ✗ Failed to enhance: {e}")
                stats['failed_enhancements'] += 1
                continue
    
    # Update metadata
    enhanced_data['metadata']['enhanced_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    enhanced_data['metadata']['enhancement_stats'] = stats
    
    # Calculate final statistics
    stats['end_time'] = time.time()
    stats['total_time'] = stats['end_time'] - stats['start_time']
    
    # Save enhanced data
    print(f"\n{'='*60}")
    print("Saving enhanced data...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
    
    # Print final statistics
    print_enhancement_summary(stats, output_file)

def print_enhancement_summary(stats: Dict[str, Any], output_file: str) -> None:
    """Print enhancement process summary."""
    print(f"\n{'='*60}")
    print("ENHANCEMENT PROCESS COMPLETED")
    print(f"{'='*60}")
    
    print(f"Total products processed: {stats['total_products']}")
    print(f"Successfully enhanced: {stats['enhanced_products']}")
    print(f"Failed enhancements: {stats['failed_enhancements']}")
    print(f"Categories processed: {stats['categories_processed']}")
    print(f"Total time: {stats['total_time']:.1f} seconds")
    
    if stats['total_products'] > 0:
        success_rate = (stats['enhanced_products'] / stats['total_products']) * 100
        print(f"Success rate: {success_rate:.1f}%")
    
    print(f"\nEnhanced data saved to: {output_file}")
    
    if stats['failed_enhancements'] > 0:
        print(f"\n⚠️  {stats['failed_enhancements']} products failed to enhance.")
        print("Consider running the script again for failed products.")

def create_sample_enhancement() -> None:
    """Create a sample enhancement to test the system."""
    print("Creating sample enhancement...")
    
    # Load a single product for testing
    with open('products_hierarchical.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get first product from first category
    first_category = next(iter(data['categories'].values()))
    first_product = first_category['products'][0]
    
    print(f"Testing with product: {first_product.get('name', 'Unknown')}")
    
    # Create client and enhance
    client = create_openrouter_client()
    enhanced_product = client.enhance_specifications(first_product)
    
    # Save sample
    sample_data = {
        'original': first_product,
        'enhanced': enhanced_product,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open('sample_enhancement.json', 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
    
    print("Sample enhancement saved to 'sample_enhancement.json'")
    print("\nOriginal specifications:")
    for spec in first_product.get('specifications', []):
        print(f"  - {spec}")
    
    print("\nEnhanced specifications:")
    for spec in enhanced_product.get('specifications', []):
        print(f"  - {spec}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "sample":
            create_sample_enhancement()
        elif command == "test":
            enhance_product_specifications(test_mode=True, test_limit=2)
        elif command == "full":
            enhance_product_specifications()
        else:
            print("Usage:")
            print("  python3 enhance_specifications.py sample  # Test with one product")
            print("  python3 enhance_specifications.py test    # Test with 2 products per category")
            print("  python3 enhance_specifications.py full    # Process all products")
    else:
        print("Usage:")
        print("  python3 enhance_specifications.py sample  # Test with one product")
        print("  python3 enhance_specifications.py test    # Test with 2 products per category")
        print("  python3 enhance_specifications.py full    # Process all products")