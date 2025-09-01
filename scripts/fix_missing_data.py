#!/usr/bin/env python3

import json
import time
from typing import Dict, List, Any, Optional
from brochure.openrouter_client import create_openrouter_client

def fix_missing_power_sources(input_file: str = 'products_hierarchical_enhanced.json',
                             output_file: str = 'products_hierarchical_fixed.json',
                             delay: float = 2.0) -> None:
    """Fix missing power source information for identified products."""
    
    # Products missing power source information
    missing_power_products = [
        "OMNIA_IPC286",  # Indoor Rotatable Camera
        "OMNIA_IPC267",  # Indoor Rotatable Camera
        "OMNIA_IPC207",  # Outdoor Camera
        "OMNIA_IPC198",  # Outdoor Camera
        "OMNIA_IPC173",  # Outdoor Wi-Fi DC Camera
        "OMNIA_IPC216-C",  # Outdoor Wi-Fi Battery Camera
        "AVATTO_T10E",  # Control Panel MAX
        "TUYA_TSW-T111",  # Stick Logger
        "TUYA_VEN5KHB-D1",  # Residential Single-Phase Hybrid inverter
        "TUYA_URA-MESS1",  # Balcony Energy Storage
        "Wenhui_OHCTF001"  # Smart Water Valve
    ]
    
    print("Loading product data...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    client = create_openrouter_client()
    
    stats = {
        'products_processed': 0,
        'power_sources_added': 0,
        'failed_fixes': 0
    }
    
    print(f"Fixing missing power source information for {len(missing_power_products)} products...")
    
    for category_name, category_data in data.get('categories', {}).items():
        if 'products' not in category_data:
            continue
            
        for i, product in enumerate(category_data['products']):
            product_id = product.get('id', '')
            
            if product_id in missing_power_products:
                stats['products_processed'] += 1
                product_name = product.get('name', 'Unknown')
                
                print(f"\nFixing power source for: {product_name} ({product_id})")
                
                try:
                    # Create specific prompt for power source research
                    power_source_prompt = f"""
                    You are a technical specification expert. Provide accurate, specific power source information for electronic devices.
                    
                    Product: {product_name}
                    Model: {product.get('model', '')}
                    Category: {category_name}
                    Current Specifications: {product.get('specifications', [])}
                    
                    Research and determine the accurate power source for this product. Consider:
                    - Product type and typical power requirements
                    - Installation environment (indoor/outdoor)
                    - Industry standards for similar devices
                    - Model specifications if available
                    
                    Provide ONLY the power source specification in this format:
                    "Power Source: [specific power requirement]"
                    
                    Examples:
                    - "Power Source: AC 100-240V, 50/60Hz"
                    - "Power Source: DC 12V/2A adapter"
                    - "Power Source: Rechargeable lithium battery (5000mAh)"
                    - "Power Source: PoE (Power over Ethernet) 802.3af"
                    """
                    
                    # Get power source from AI using OpenRouter API
                    api_response = client._make_api_call(power_source_prompt)
                    
                    if not api_response:
                        raise Exception("No response from API")
                    
                    power_source = api_response.strip()
                    
                    # Add power source to specifications
                    if 'specifications' not in product:
                        product['specifications'] = []
                    
                    # Check if power source already exists
                    has_power = any('power' in spec.lower() for spec in product['specifications'])
                    
                    if not has_power and power_source.startswith('Power Source:'):
                        product['specifications'].append(power_source)
                        stats['power_sources_added'] += 1
                        print(f"  ✓ Added: {power_source}")
                    else:
                        print(f"  ⚠ Skipped: {power_source}")
                    
                    # Update the product in the data structure
                    category_data['products'][i] = product
                    
                    if delay > 0:
                        time.sleep(delay)
                        
                except Exception as e:
                    print(f"  ✗ Failed: {e}")
                    stats['failed_fixes'] += 1
    
    # Update metadata
    data['metadata']['power_source_fix_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
    data['metadata']['power_source_fix_stats'] = stats
    
    # Save fixed data
    print(f"\nSaving fixed data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print_fix_summary(stats)

def fix_missing_communication_protocols(input_file: str = 'products_hierarchical_fixed.json',
                                      output_file: str = 'products_hierarchical_fixed.json',
                                      delay: float = 2.0) -> None:
    """Fix missing communication protocol information for identified products."""
    
    # Products missing communication protocol
    missing_protocol_products = [
        "TUYA_SC106-WL3",  # Cube camera
        "OMNIA_IPC267",   # Indoor Rotatable Camera
        "TUYA_SF254-WC2", # Smart Bird Feeder
        "TUYA_VEN5KHB-D1", # Residential Single-Phase Hybrid inverter
        "TUYA_URA-MESS1", # Balcony Energy Storage
        "Wenhui_OHCTF001" # Smart Water Valve
    ]
    
    print("\nLoading product data for protocol fixes...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    client = create_openrouter_client()
    
    stats = {
        'products_processed': 0,
        'protocols_added': 0,
        'failed_fixes': 0
    }
    
    print(f"Fixing missing communication protocols for {len(missing_protocol_products)} products...")
    
    for category_name, category_data in data.get('categories', {}).items():
        if 'products' not in category_data:
            continue
            
        for i, product in enumerate(category_data['products']):
            product_id = product.get('id', '')
            
            if product_id in missing_protocol_products:
                stats['products_processed'] += 1
                product_name = product.get('name', 'Unknown')
                
                print(f"\nFixing communication protocol for: {product_name} ({product_id})")
                
                try:
                    # Create specific prompt for communication protocol research
                    protocol_prompt = f"""
                    You are a smart home connectivity expert. Provide accurate communication protocol information for IoT devices.
                    
                    Product: {product_name}
                    Model: {product.get('model', '')}
                    Category: {category_name}
                    Supplier: {product.get('supplier', '')}
                    Current Specifications: {product.get('specifications', [])}
                    
                    Research and determine the accurate communication protocol(s) for this product. Consider:
                    - Product category and typical connectivity requirements
                    - Supplier's standard protocols (TUYA typically uses Wi-Fi/Zigbee, OMNIA uses Wi-Fi, etc.)
                    - Smart home integration standards
                    - Industry standards for this device type
                    
                    Provide ONLY the communication protocol specification in this format:
                    "Communication Protocol: [specific protocol(s)]"
                    
                    Examples:
                    - "Communication Protocol: Wi-Fi 2.4GHz IEEE 802.11 b/g/n"
                    - "Communication Protocol: Zigbee 3.0"
                    - "Communication Protocol: Wi-Fi 2.4GHz + Bluetooth 5.0"
                    - "Communication Protocol: RS485 + Wi-Fi"
                    """
                    
                    # Get protocol from AI using OpenRouter API
                    api_response = client._make_api_call(protocol_prompt)
                    
                    if not api_response:
                        raise Exception("No response from API")
                    
                    protocol = api_response.strip()
                    
                    # Add protocol to specifications
                    if 'specifications' not in product:
                        product['specifications'] = []
                    
                    # Check if communication protocol already exists
                    has_protocol = any(any(keyword in spec.lower() for keyword in ['communication', 'protocol', 'connectivity', 'wi-fi', 'wifi', 'zigbee', 'bluetooth']) for spec in product['specifications'])
                    
                    if not has_protocol and protocol.startswith('Communication Protocol:'):
                        product['specifications'].append(protocol)
                        stats['protocols_added'] += 1
                        print(f"  ✓ Added: {protocol}")
                    else:
                        print(f"  ⚠ Skipped: {protocol}")
                    
                    # Update the product in the data structure
                    category_data['products'][i] = product
                    
                    if delay > 0:
                        time.sleep(delay)
                        
                except Exception as e:
                    print(f"  ✗ Failed: {e}")
                    stats['failed_fixes'] += 1
    
    # Update metadata
    data['metadata']['protocol_fix_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
    data['metadata']['protocol_fix_stats'] = stats
    
    # Save fixed data
    print(f"\nSaving protocol-fixed data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print_fix_summary(stats, fix_type="Communication Protocol")

def fix_missing_description(input_file: str = 'products_hierarchical_fixed.json',
                          output_file: str = 'products_hierarchical_fixed.json',
                          delay: float = 2.0) -> None:
    """Fix missing description for Wenhui_OHCTF001 Smart Water Valve."""
    
    print("\nLoading product data for description fix...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    client = create_openrouter_client()
    target_product_id = "Wenhui_OHCTF001"
    
    print(f"Fixing missing description for {target_product_id}...")
    
    for category_name, category_data in data.get('categories', {}).items():
        if 'products' not in category_data:
            continue
            
        for i, product in enumerate(category_data['products']):
            product_id = product.get('id', '')
            
            if product_id == target_product_id:
                product_name = product.get('name', 'Unknown')
                
                print(f"\nCreating description for: {product_name} ({product_id})")
                
                try:
                    # Create specific prompt for product description
                    description_prompt = f"""
                    You are a technical product description writer. Create clear, professional descriptions for smart home devices.
                    
                    Product: {product_name}
                    Model: {product.get('model', '')}
                    Category: {category_name}
                    Supplier: {product.get('supplier', '')}
                    Current Specifications: {product.get('specifications', [])}
                    
                    Create a comprehensive, professional product description for this smart water valve. Include:
                    - Primary function and purpose
                    - Key features and capabilities
                    - Installation and usage context
                    - Smart home integration benefits
                    - Target applications
                    
                    Write in a professional, technical tone suitable for a product brochure.
                    Length: 2-3 sentences, approximately 50-80 words.
                    """
                    
                    # Get description from AI using OpenRouter API
                    api_response = client._make_api_call(description_prompt)
                    
                    if not api_response:
                        raise Exception("No response from API")
                    
                    description = api_response.strip()
                    
                    # Add description to product
                    product['description'] = description
                    print(f"  ✓ Added description: {description[:100]}...")
                    
                    # Update the product in the data structure
                    category_data['products'][i] = product
                    
                    if delay > 0:
                        time.sleep(delay)
                        
                except Exception as e:
                    print(f"  ✗ Failed: {e}")
                    return
    
    # Update metadata
    data['metadata']['description_fix_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # Save fixed data
    print(f"\nSaving description-fixed data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("✓ Description fix completed")

def print_fix_summary(stats: Dict[str, Any], fix_type: str = "Power Source") -> None:
    """Print fix process summary."""
    print(f"\n{'='*60}")
    print(f"{fix_type.upper()} FIX COMPLETED")
    print(f"{'='*60}")
    
    print(f"Products processed: {stats['products_processed']}")
    if fix_type == "Power Source":
        print(f"Power sources added: {stats['power_sources_added']}")
    elif fix_type == "Communication Protocol":
        print(f"Protocols added: {stats['protocols_added']}")
    print(f"Failed fixes: {stats['failed_fixes']}")
    
    if stats['products_processed'] > 0:
        if fix_type == "Power Source":
            success_rate = (stats['power_sources_added'] / stats['products_processed']) * 100
        elif fix_type == "Communication Protocol":
            success_rate = (stats['protocols_added'] / stats['products_processed']) * 100
        else:
            success_rate = 100
        print(f"Success rate: {success_rate:.1f}%")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "power":
            fix_missing_power_sources()
        elif command == "protocol":
            fix_missing_communication_protocols()
        elif command == "description":
            fix_missing_description()
        elif command == "all":
            print("Running all fixes...")
            fix_missing_power_sources()
            fix_missing_communication_protocols()
            fix_missing_description()
            print("\n🎉 All fixes completed!")
        else:
            print("Usage:")
            print("  python3 fix_missing_data.py power       # Fix missing power sources")
            print("  python3 fix_missing_data.py protocol    # Fix missing communication protocols")
            print("  python3 fix_missing_data.py description # Fix missing description")
            print("  python3 fix_missing_data.py all         # Run all fixes")
    else:
        print("Usage:")
        print("  python3 fix_missing_data.py power       # Fix missing power sources")
        print("  python3 fix_missing_data.py protocol    # Fix missing communication protocols")
        print("  python3 fix_missing_data.py description # Fix missing description")
        print("  python3 fix_missing_data.py all         # Run all fixes")