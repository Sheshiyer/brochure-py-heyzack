#!/usr/bin/env python3

import json
from typing import Dict, List, Any, Set
from collections import defaultdict
import re

def analyze_specifications(json_file: str) -> Dict[str, Any]:
    """Analyze product specifications to identify issues and patterns."""
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    analysis = {
        'total_products': 0,
        'categories': {},
        'common_issues': {
            'missing_descriptions': [],
            'inconsistent_formats': [],
            'missing_power_source': [],
            'missing_communication_protocol': [],
            'vague_specifications': [],
            'duplicate_specifications': [],
            'non_pipe_separated': [],
            'missing_technical_details': []
        },
        'specification_patterns': defaultdict(int),
        'format_analysis': {
            'pipe_separated_count': 0,
            'non_pipe_separated_count': 0,
            'mixed_format_products': []
        }
    }
    
    for category_name, category_data in data.get('categories', {}).items():
        category_analysis = {
            'product_count': len(category_data.get('products', [])),
            'issues': []
        }
        
        for product in category_data.get('products', []):
            analysis['total_products'] += 1
            product_id = product.get('id', 'unknown')
            product_name = product.get('name', 'unknown')
            
            # Analyze specifications format
            specs = product.get('specifications', [])
            description = product.get('description', '')
            
            # Check for missing or inadequate descriptions
            if not description or len(description.strip()) < 20:
                analysis['common_issues']['missing_descriptions'].append({
                    'id': product_id,
                    'name': product_name,
                    'category': category_name,
                    'description_length': len(description) if description else 0
                })
            
            # Check for missing power source
            power_source = product.get('power_source')
            if not power_source or power_source == 'Not specified':
                analysis['common_issues']['missing_power_source'].append({
                    'id': product_id,
                    'name': product_name,
                    'category': category_name
                })
            
            # Check for missing communication protocol
            comm_protocol = product.get('communication_protocol')
            if not comm_protocol or comm_protocol == 'Not specified':
                analysis['common_issues']['missing_communication_protocol'].append({
                    'id': product_id,
                    'name': product_name,
                    'category': category_name
                })
            
            # Analyze specification formats
            pipe_separated = 0
            non_pipe_separated = 0
            vague_specs = []
            duplicate_specs = []
            
            spec_set = set()
            for spec in specs:
                # Count pipe-separated vs non-pipe-separated
                if '|' in spec:
                    pipe_separated += 1
                elif ':' in spec:
                    analysis['specification_patterns']['colon_separated'] += 1
                else:
                    non_pipe_separated += 1
                    analysis['specification_patterns']['plain_text'] += 1
                
                # Check for vague specifications
                if any(vague_word in spec.lower() for vague_word in ['support', 'yes', 'available', 'optional']):
                    vague_specs.append(spec)
                
                # Check for duplicates
                if spec in spec_set:
                    duplicate_specs.append(spec)
                spec_set.add(spec)
            
            # Update format analysis
            if pipe_separated > 0 and non_pipe_separated > 0:
                analysis['format_analysis']['mixed_format_products'].append({
                    'id': product_id,
                    'name': product_name,
                    'category': category_name,
                    'pipe_separated': pipe_separated,
                    'non_pipe_separated': non_pipe_separated
                })
            
            analysis['format_analysis']['pipe_separated_count'] += pipe_separated
            analysis['format_analysis']['non_pipe_separated_count'] += non_pipe_separated
            
            # Record issues
            if vague_specs:
                analysis['common_issues']['vague_specifications'].append({
                    'id': product_id,
                    'name': product_name,
                    'category': category_name,
                    'vague_specs': vague_specs
                })
            
            if duplicate_specs:
                analysis['common_issues']['duplicate_specifications'].append({
                    'id': product_id,
                    'name': product_name,
                    'category': category_name,
                    'duplicates': duplicate_specs
                })
            
            # Check for missing technical details based on category
            missing_details = check_missing_technical_details(product, category_name)
            if missing_details:
                analysis['common_issues']['missing_technical_details'].append({
                    'id': product_id,
                    'name': product_name,
                    'category': category_name,
                    'missing_details': missing_details
                })
        
        analysis['categories'][category_name] = category_analysis
    
    return analysis

def check_missing_technical_details(product: Dict[str, Any], category: str) -> List[str]:
    """Check for missing technical details based on product category."""
    missing = []
    specs_text = ' '.join(product.get('specifications', [])).lower()
    
    # Common technical details for all categories
    if 'resolution' not in specs_text and 'mp' not in specs_text:
        missing.append('Video resolution/quality')
    
    if 'storage' not in specs_text and 'sd' not in specs_text and 'memory' not in specs_text:
        missing.append('Storage specifications')
    
    # Category-specific checks
    if category.lower() in ['camera', 'video door bell']:
        if 'sensor' not in specs_text:
            missing.append('Image sensor details')
        if 'lens' not in specs_text and 'focal' not in specs_text:
            missing.append('Lens specifications')
        if 'night vision' not in specs_text and 'ir' not in specs_text:
            missing.append('Night vision capabilities')
    
    if category.lower() in ['smart lock', 'lock']:
        if 'battery' not in specs_text and 'power' not in specs_text:
            missing.append('Power/battery specifications')
        if 'unlock' not in specs_text and 'access' not in specs_text:
            missing.append('Unlock methods')
    
    return missing

def print_analysis_report(analysis: Dict[str, Any]):
    """Print a comprehensive analysis report."""
    print("\n" + "="*80)
    print("PRODUCT SPECIFICATIONS ANALYSIS REPORT")
    print("="*80)
    
    print(f"\nTotal Products Analyzed: {analysis['total_products']}")
    print(f"Categories: {len(analysis['categories'])}")
    
    print("\n" + "-"*50)
    print("FORMAT ANALYSIS")
    print("-"*50)
    print(f"Pipe-separated specifications: {analysis['format_analysis']['pipe_separated_count']}")
    print(f"Non-pipe-separated specifications: {analysis['format_analysis']['non_pipe_separated_count']}")
    print(f"Products with mixed formats: {len(analysis['format_analysis']['mixed_format_products'])}")
    
    print("\n" + "-"*50)
    print("COMMON ISSUES SUMMARY")
    print("-"*50)
    
    for issue_type, issues in analysis['common_issues'].items():
        if issues:
            print(f"\n{issue_type.replace('_', ' ').title()}: {len(issues)} products")
            for issue in issues[:3]:  # Show first 3 examples
                print(f"  - {issue['name']} ({issue['category']})")
            if len(issues) > 3:
                print(f"  ... and {len(issues) - 3} more")
    
    print("\n" + "-"*50)
    print("CATEGORY BREAKDOWN")
    print("-"*50)
    
    for category, data in analysis['categories'].items():
        print(f"\n{category}: {data['product_count']} products")
    
    print("\n" + "-"*50)
    print("RECOMMENDATIONS")
    print("-"*50)
    
    recommendations = []
    
    if analysis['common_issues']['missing_descriptions']:
        recommendations.append("1. Enhance product descriptions for better clarity")
    
    if analysis['format_analysis']['mixed_format_products']:
        recommendations.append("2. Standardize specification format to pipe-separated (Feature|Value)")
    
    if analysis['common_issues']['vague_specifications']:
        recommendations.append("3. Replace vague specifications with specific technical details")
    
    if analysis['common_issues']['missing_technical_details']:
        recommendations.append("4. Add missing technical specifications based on product category")
    
    if analysis['common_issues']['missing_power_source']:
        recommendations.append("5. Specify power source/requirements for all products")
    
    if analysis['common_issues']['missing_communication_protocol']:
        recommendations.append("6. Clarify communication protocols and connectivity options")
    
    for i, rec in enumerate(recommendations, 1):
        print(f"{rec}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    analysis = analyze_specifications('products_hierarchical.json')
    print_analysis_report(analysis)
    
    # Save detailed analysis to file
    with open('specification_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    print("\nDetailed analysis saved to 'specification_analysis.json'")