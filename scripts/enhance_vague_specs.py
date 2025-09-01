#!/usr/bin/env python3

import json
import time
from typing import Dict, List, Any, Optional
from brochure.openrouter_client import create_openrouter_client

def enhance_vague_specifications(input_file: str = 'products_hierarchical_fixed.json',
                                output_file: str = 'products_hierarchical_enhanced_v2.json',
                                delay: float = 2.0) -> None:
    """Enhance vague specifications for products with unclear technical details."""
    
    # Products with vague specifications identified from analysis
    vague_spec_products = [
        "OMNIA_IPC216-C",  # Camera - vague storage specs
        "OMNIA_IPC750",    # Camera - missing video resolution
        "TUYA_SF254-WC2",  # Pet accessories - vague specs
        "TUYA_LL05-B",     # Door lock - missing technical details
        "AVATTO_T10E",     # Control panel - vague specs
        "szsmarthome_Q4-PRO", # Control panel - missing details
        "TUYA_UX33",       # Smart gateway - vague specs
        "TUYA_GW60-Matter", # Smart gateway - missing details
        "AVATTO_TRV06",    # Smart thermostat - vague specs
        "TUYA_UFO-R1",     # Smart remote control - missing details
        "TUYA_TSW-T111",   # Smart electrical - vague specs
        "szsmarthome_A7-K", # Background music - missing details
        "szsmarthome_N86N-4", # Background music - vague specs
        "Wenhui_WHDZ12-4C" # Smart socket - missing technical details
    ]
    
    print("Loading product data...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    client = create_openrouter_client()
    
    stats = {
        'products_processed': 0,
        'specifications_enhanced': 0,
        'failed_enhancements': 0
    }
    
    print(f"Enhancing vague specifications for {len(vague_spec_products)} products...")
    
    for category_name, category_data in data.get('categories', {}).items():
        if 'products' not in category_data:
            continue
            
        for i, product in enumerate(category_data['products']):
            product_id = product.get('id', '')
            
            if product_id in vague_spec_products:
                stats['products_processed'] += 1
                product_name = product.get('name', 'Unknown')
                
                print(f"\nEnhancing specifications for: {product_name} ({product_id})")
                
                try:
                    # Create specific enhancement prompt based on product category
                    enhancement_prompt = create_enhancement_prompt(
                        product_name, 
                        category_name, 
                        product.get('specifications', []),
                        product_id
                    )
                    
                    # Get enhanced specifications from AI
                    api_response = client._make_api_call(enhancement_prompt)
                    
                    if not api_response:
                        raise Exception("No response from API")
                    
                    enhanced_specs = parse_enhanced_specifications(api_response)
                    
                    if enhanced_specs:
                        # Add enhanced specifications to existing ones
                        if 'specifications' not in product:
                            product['specifications'] = []
                        
                        # Add new specifications that don't already exist
                        existing_spec_keys = set()
                        for spec in product['specifications']:
                            if '|' in spec:
                                key = spec.split('|')[0].lower().strip()
                                existing_spec_keys.add(key)
                        
                        added_count = 0
                        for new_spec in enhanced_specs:
                            if '|' in new_spec:
                                key = new_spec.split('|')[0].lower().strip()
                                if key not in existing_spec_keys:
                                    product['specifications'].append(new_spec)
                                    added_count += 1
                        
                        if added_count > 0:
                            stats['specifications_enhanced'] += 1
                            print(f"  ✓ Added {added_count} enhanced specifications")
                        else:
                            print(f"  ⚠ No new specifications to add")
                    else:
                        print(f"  ⚠ No enhanced specifications generated")
                    
                    # Update the product in the data structure
                    category_data['products'][i] = product
                    
                    if delay > 0:
                        time.sleep(delay)
                        
                except Exception as e:
                    print(f"  ✗ Failed: {e}")
                    stats['failed_enhancements'] += 1
    
    # Update metadata
    data['metadata']['vague_specs_enhancement_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
    data['metadata']['vague_specs_enhancement_stats'] = stats
    
    # Save enhanced data
    print(f"\nSaving enhanced data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print_enhancement_summary(stats)

def create_enhancement_prompt(product_name: str, category: str, current_specs: List[str], product_id: str) -> str:
    """Create targeted enhancement prompt based on product type."""
    
    # Category-specific enhancement guidelines
    category_guidelines = {
        'Camera': {
            'focus_areas': ['video resolution', 'image sensor details', 'storage specifications', 'night vision capabilities', 'motion detection features'],
            'example_specs': ['Video Resolution|4K (3840x2160) @ 30fps', 'Image Sensor|1/2.8" CMOS, 8MP', 'Storage|Local: microSD up to 256GB, Cloud: 30-day free trial']
        },
        'Pet Accessories': {
            'focus_areas': ['feeding capacity', 'power specifications', 'app features', 'material specifications', 'safety features'],
            'example_specs': ['Feeding Capacity|6L dry food storage', 'Material|Food-grade ABS plastic, BPA-free', 'App Features|Feeding schedule, portion control, low food alerts']
        },
        'Door Lock': {
            'focus_areas': ['lock mechanism', 'security features', 'battery life', 'access methods', 'installation requirements'],
            'example_specs': ['Lock Mechanism|Deadbolt with anti-pick cylinder', 'Battery Life|12 months (4 AA batteries)', 'Access Methods|Fingerprint, PIN code, RFID card, mobile app']
        },
        'Smart Control Panel': {
            'focus_areas': ['display specifications', 'touch sensitivity', 'supported protocols', 'installation type', 'scene control'],
            'example_specs': ['Display|4.3" TFT LCD, 480x272 resolution', 'Touch|Capacitive multi-touch', 'Scene Control|Up to 20 custom scenes']
        },
        'Smart Gateway': {
            'focus_areas': ['supported protocols', 'device capacity', 'range specifications', 'network requirements', 'hub features'],
            'example_specs': ['Device Capacity|Up to 200 connected devices', 'Wireless Range|100m open space', 'Hub Features|Local automation, voice control integration']
        },
        'Smart Thermostat': {
            'focus_areas': ['temperature range', 'accuracy', 'HVAC compatibility', 'scheduling features', 'energy saving'],
            'example_specs': ['Temperature Range|5°C to 35°C (41°F to 95°F)', 'Accuracy|±0.5°C (±1°F)', 'HVAC Compatibility|Heat pump, gas, electric, dual fuel']
        },
        'Smart Remote Control': {
            'focus_areas': ['IR range', 'device compatibility', 'learning capability', 'button configuration', 'battery specifications'],
            'example_specs': ['IR Range|8-10 meters', 'Device Compatibility|TV, AC, STB, DVD, Audio systems', 'Learning|Universal IR learning capability']
        },
        'Smart Electrical Products': {
            'focus_areas': ['electrical ratings', 'load capacity', 'safety certifications', 'installation requirements', 'monitoring features'],
            'example_specs': ['Load Capacity|16A resistive, 10A inductive', 'Safety|Overload protection, surge protection', 'Monitoring|Real-time power consumption']
        },
        'Background Music': {
            'focus_areas': ['audio specifications', 'input/output options', 'amplifier power', 'zone control', 'streaming capabilities'],
            'example_specs': ['Audio Output|2 x 30W RMS', 'Frequency Response|20Hz - 20kHz', 'Streaming|Bluetooth 5.0, Wi-Fi, AirPlay 2']
        },
        'Smart Socket': {
            'focus_areas': ['electrical ratings', 'outlet configuration', 'USB specifications', 'safety features', 'smart features'],
            'example_specs': ['Electrical Rating|16A, 250V AC', 'USB Output|5V/2.4A per port', 'Safety|Child protection, surge protection']
        }
    }
    
    # Get category-specific guidelines
    guidelines = category_guidelines.get(category, {
        'focus_areas': ['technical specifications', 'performance metrics', 'connectivity options', 'power requirements', 'physical dimensions'],
        'example_specs': ['Technical Spec|Detailed specification', 'Performance|Specific performance metric']
    })
    
    prompt = f"""
    You are a technical specification expert. Enhance the vague or missing specifications for this smart home product.
    
    Product: {product_name}
    Product ID: {product_id}
    Category: {category}
    Current Specifications: {current_specs}
    
    Focus on enhancing these areas: {', '.join(guidelines['focus_areas'])}
    
    Guidelines:
    1. Research typical specifications for this product category
    2. Provide specific, measurable values rather than vague descriptions
    3. Include industry-standard specifications that would be expected
    4. Ensure specifications are realistic for the product type and price range
    5. Use the format: "Specification Name|Specific Value"
    
    Example enhanced specifications for this category:
    {chr(10).join(guidelines['example_specs'])}
    
    Provide 5-10 enhanced specifications that would typically be missing or vague for this product.
    Only return the specifications in the format "Name|Value", one per line.
    Do not include explanations or additional text.
    """
    
    return prompt

def parse_enhanced_specifications(response: str) -> List[str]:
    """Parse AI response to extract enhanced specifications."""
    specs = []
    lines = response.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if '|' in line and not line.startswith('#') and not line.startswith('*'):
            # Clean up the specification
            spec = line.replace('- ', '').replace('• ', '').strip()
            if spec:
                specs.append(spec)
    
    return specs

def print_enhancement_summary(stats: Dict[str, Any]) -> None:
    """Print enhancement process summary."""
    print(f"\n{'='*60}")
    print(f"VAGUE SPECIFICATIONS ENHANCEMENT COMPLETED")
    print(f"{'='*60}")
    
    print(f"Products processed: {stats['products_processed']}")
    print(f"Products enhanced: {stats['specifications_enhanced']}")
    print(f"Failed enhancements: {stats['failed_enhancements']}")
    
    if stats['products_processed'] > 0:
        success_rate = (stats['specifications_enhanced'] / stats['products_processed']) * 100
        print(f"Success rate: {success_rate:.1f}%")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage:")
        print("  python3 enhance_vague_specs.py                    # Enhance vague specifications")
        print("  python3 enhance_vague_specs.py --help             # Show this help")
    else:
        enhance_vague_specifications()
        print("\n🎉 Vague specifications enhancement completed!")