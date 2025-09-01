#!/usr/bin/env python3
"""
Generate short product descriptions using OpenRouter AI while preserving existing long descriptions.
Focuses on conceptual value without repeating technical specifications.
"""

import json
import sys
import os
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from brochure.openrouter_client import create_openrouter_client

def create_description_prompt(name: str, category: str, current_description: str, specs: list) -> str:
    """Create a prompt for generating concise, conceptual descriptions."""
    specs_summary = "\n".join([f"- {spec}" for spec in specs[:10]])  # First 10 specs for context
    
    prompt = f"""You are a marketing copywriter specializing in smart home products. Create a concise, compelling product description that focuses on user benefits and conceptual value.

Product: {name}
Category: {category}
Current Description: {current_description}

Key Technical Specifications (for context only - DO NOT repeat these):
{specs_summary}

Requirements:
1. Write 2-3 sentences maximum (under 150 words)
2. Focus on user benefits, use cases, and value proposition
3. Avoid repeating any technical specifications listed above
4. Use engaging, benefit-focused language
5. Highlight what makes this product unique or valuable
6. Target smart home enthusiasts and security-conscious users

Return ONLY the new description text, no JSON or formatting."""
    
    return prompt

def regenerate_product_description(client, product_data: dict) -> dict:
    """Generate short description while preserving existing long description."""
    try:
        name = product_data.get('name', '')
        category = product_data.get('category', '')
        current_description = product_data.get('description', '')
        specs = product_data.get('specifications', [])
        
        # Skip if short_description already exists
        if 'short_description' in product_data and product_data['short_description']:
            print(f"  ⏭ Skipping {name} - short description already exists")
            return product_data
        
        print(f"Generating short description for: {name}")
        
        # Create specialized prompt for concise descriptions
        prompt = create_description_prompt(name, category, current_description, specs)
        
        # Make API call
        response = client._make_api_call(prompt)
        
        if response:
            # Clean up the response
            new_short_description = response.strip()
            # Remove any quotes or formatting artifacts
            new_short_description = new_short_description.strip('"').strip("'")
            
            # Update product data - preserve existing description, add short_description
            updated_product = product_data.copy()
            # Preserve original description as long_description if not already set
            if 'long_description' not in updated_product:
                updated_product['long_description'] = current_description
            # Add new short description
            updated_product['short_description'] = new_short_description
            
            print(f"  ✓ Added short description: {new_short_description[:50]}...")
            return updated_product
        else:
            print(f"  ✗ Failed to generate short description")
            return product_data
            
    except Exception as e:
        print(f"Error generating short description for {product_data.get('name', 'unknown')}: {e}")
        return product_data

def regenerate_all_descriptions(input_file: str, output_file: str):
    """Regenerate descriptions for all products."""
    try:
        # Load product data
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create OpenRouter client with updated model
        client = create_openrouter_client(model_id="deepseek/deepseek-chat-v3.1")
        
        # Process all products
        total_products = 0
        updated_products = 0
        
        if 'categories' in data:
            for category_name, category_data in data['categories'].items():
                if 'products' in category_data:
                    print(f"\nProcessing category: {category_name}")
                    
                    for i, product in enumerate(category_data['products']):
                        total_products += 1
                        
                        # Regenerate description
                        updated_product = regenerate_product_description(client, product)
                        
                        # Check if short description was added
                        if 'short_description' in updated_product and updated_product['short_description']:
                            updated_products += 1
                        
                        category_data['products'][i] = updated_product
                        
                        # Rate limiting
                        import time
                        time.sleep(1.5)  # Respect API limits
        
        # Save updated data
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Short description generation complete!")
        print(f"  Total products processed: {total_products}")
        print(f"  Short descriptions added: {updated_products}")
        print(f"  Output saved to: {output_file}")
        
    except Exception as e:
        print(f"Error during regeneration: {e}")
        sys.exit(1)

def main():
    """Main execution function."""
    # File paths
    input_file = "data/products_hierarchical_enhanced.json"
    output_file = "data/products_hierarchical_enhanced.json"  # Overwrite original
    backup_file = f"data/backups/products_pre_short_desc_gen_{int(time.time())}.json"
    
    # Create backup
    os.makedirs("data/backups", exist_ok=True)
    import shutil
    shutil.copy2(input_file, backup_file)
    print(f"Backup created: {backup_file}")
    
    # Generate short descriptions
    regenerate_all_descriptions(input_file, output_file)
    
    print(f"\nNext steps:")
    print(f"1. Update brochure template to use short_description field")
    print(f"2. Run 'python3 main.py build' to regenerate brochure")
    print(f"3. Check the updated layout with concise descriptions")

if __name__ == "__main__":
    main()