#!/usr/bin/env python3

import json
import pandas as pd
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import os

def analyze_missing_products() -> Dict[str, Any]:
    """Analyze the 226 products missing from JSON files and evaluate incorporation strategies."""
    
    print("Loading CSV and JSON data...")
    
    # Load CSV data
    csv_file = 'SMART HOME FOLLOWING PROJECT - All Products.csv'
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"CSV file {csv_file} not found")
    
    df = pd.read_csv(csv_file)
    
    # Load JSON data
    json_file = 'products_hierarchical_enhanced_v2.json'
    if not os.path.exists(json_file):
        json_file = 'products_hierarchical_fixed.json'
    
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # Extract product IDs from JSON
    json_product_ids = set()
    for category_data in json_data.get('categories', {}).values():
        for product in category_data.get('products', []):
            json_product_ids.add(product.get('id', ''))
    
    # Find missing products (using Model Number as ID)
    csv_product_ids = set(df['Model Number'].astype(str))
    missing_product_ids = csv_product_ids - json_product_ids
    
    print(f"Total CSV products: {len(csv_product_ids)}")
    print(f"Total JSON products: {len(json_product_ids)}")
    print(f"Missing products: {len(missing_product_ids)}")
    
    # Analyze missing products
    missing_df = df[df['Model Number'].astype(str).isin(missing_product_ids)]
    
    analysis = {
        'total_csv_products': len(csv_product_ids),
        'total_json_products': len(json_product_ids),
        'missing_count': len(missing_product_ids),
        'missing_products': [],
        'category_distribution': {},
        'drive_link_analysis': {},
        'specification_quality': {},
        'strategies': {}
    }
    
    # Analyze missing products by category
    category_counts = defaultdict(int)
    drive_link_status = {'has_link': 0, 'no_link': 0, 'empty_link': 0}
    spec_quality = {'detailed': 0, 'basic': 0, 'minimal': 0}
    
    for _, row in missing_df.iterrows():
        product_info = {
            'id': str(row['Model Number']),
            'name': row.get('Product Name', 'Unknown'),
            'category': row.get('Category', 'Unknown'),
            'has_drive_link': bool(row.get('Drive Link') and str(row.get('Drive Link')).strip() and str(row.get('Drive Link')) != 'nan'),
            'drive_link': str(row.get('Drive Link', '')),
            'specifications': row.get('Specifications', ''),
            'spec_length': len(str(row.get('Specifications', ''))) if pd.notna(row.get('Specifications')) else 0
        }
        
        analysis['missing_products'].append(product_info)
        
        # Category distribution
        category = product_info['category']
        category_counts[category] += 1
        
        # Drive link analysis
        if product_info['has_drive_link']:
            drive_link_status['has_link'] += 1
        elif not product_info['drive_link'] or product_info['drive_link'] == 'nan':
            drive_link_status['no_link'] += 1
        else:
            drive_link_status['empty_link'] += 1
        
        # Specification quality analysis
        spec_len = product_info['spec_length']
        if spec_len > 200:
            spec_quality['detailed'] += 1
        elif spec_len > 50:
            spec_quality['basic'] += 1
        else:
            spec_quality['minimal'] += 1
    
    analysis['category_distribution'] = dict(category_counts)
    analysis['drive_link_analysis'] = drive_link_status
    analysis['specification_quality'] = spec_quality
    
    return analysis

def evaluate_incorporation_strategies(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate different strategies for incorporating missing products."""
    
    strategies = {
        'strategy_1_selective_inclusion': {
            'name': 'Selective Inclusion Based on Data Quality',
            'description': 'Include only products with drive links and detailed specifications',
            'criteria': {
                'has_drive_link': True,
                'min_spec_length': 100
            },
            'estimated_products': 0,
            'pros': [
                'Maintains data quality standards',
                'Consistent with current JSON structure',
                'Easier to implement and maintain'
            ],
            'cons': [
                'Excludes potentially valuable products',
                'May create incomplete catalog representation'
            ]
        },
        'strategy_2_tiered_inclusion': {
            'name': 'Tiered Inclusion with Quality Flags',
            'description': 'Include all products but mark data quality levels',
            'criteria': {
                'tier_1': 'Products with drive links and detailed specs',
                'tier_2': 'Products with basic specifications',
                'tier_3': 'Products with minimal data (placeholders)'
            },
            'estimated_products': analysis['missing_count'],
            'pros': [
                'Complete catalog representation',
                'Transparent data quality indicators',
                'Allows for future enhancement'
            ],
            'cons': [
                'Requires additional metadata fields',
                'May confuse users with incomplete data',
                'Increases maintenance complexity'
            ]
        },
        'strategy_3_placeholder_approach': {
            'name': 'Placeholder with Enhancement Pipeline',
            'description': 'Create placeholders for all missing products with enhancement workflow',
            'criteria': {
                'placeholder_fields': ['id', 'name', 'category', 'status'],
                'enhancement_queue': 'Products marked for future data collection'
            },
            'estimated_products': analysis['missing_count'],
            'pros': [
                'Complete product catalog',
                'Clear enhancement roadmap',
                'Maintains catalog completeness'
            ],
            'cons': [
                'Requires significant additional work',
                'May provide limited immediate value',
                'Complex workflow management'
            ]
        },
        'strategy_4_hybrid_approach': {
            'name': 'Hybrid Quality-Based Inclusion',
            'description': 'Combine selective inclusion with targeted enhancement',
            'criteria': {
                'immediate_inclusion': 'Products with drive links',
                'enhancement_targets': 'High-value products without links',
                'exclusion': 'Low-value or duplicate products'
            },
            'estimated_products': 0,
            'pros': [
                'Balanced approach to quality and completeness',
                'Prioritizes high-value additions',
                'Manageable implementation scope'
            ],
            'cons': [
                'Requires manual product evaluation',
                'Subjective quality decisions',
                'Phased implementation complexity'
            ]
        }
    }
    
    # Calculate estimated products for strategies
    products_with_links = analysis['drive_link_analysis']['has_link']
    detailed_specs = analysis['specification_quality']['detailed']
    
    strategies['strategy_1_selective_inclusion']['estimated_products'] = min(products_with_links, detailed_specs)
    strategies['strategy_4_hybrid_approach']['estimated_products'] = products_with_links + (detailed_specs // 2)
    
    return strategies

def generate_recommendations(analysis: Dict[str, Any], strategies: Dict[str, Any]) -> Dict[str, Any]:
    """Generate specific recommendations based on analysis."""
    
    missing_count = analysis['missing_count']
    has_links = analysis['drive_link_analysis']['has_link']
    detailed_specs = analysis['specification_quality']['detailed']
    
    recommendations = {
        'primary_recommendation': '',
        'implementation_phases': [],
        'immediate_actions': [],
        'long_term_goals': [],
        'resource_requirements': {},
        'risk_assessment': {}
    }
    
    # Determine primary recommendation based on data quality
    if has_links > missing_count * 0.3:  # If >30% have drive links
        recommendations['primary_recommendation'] = 'strategy_2_tiered_inclusion'
        recommendations['rationale'] = f"With {has_links} products having drive links ({has_links/missing_count*100:.1f}%), a tiered approach provides the best balance of completeness and quality."
    elif detailed_specs > missing_count * 0.2:  # If >20% have detailed specs
        recommendations['primary_recommendation'] = 'strategy_4_hybrid_approach'
        recommendations['rationale'] = f"With {detailed_specs} products having detailed specifications, a hybrid approach allows selective quality inclusion."
    else:
        recommendations['primary_recommendation'] = 'strategy_1_selective_inclusion'
        recommendations['rationale'] = "Given limited high-quality data, selective inclusion maintains current quality standards."
    
    # Implementation phases
    recommendations['implementation_phases'] = [
        {
            'phase': 1,
            'name': 'High-Quality Product Integration',
            'description': 'Include products with drive links and detailed specifications',
            'estimated_products': min(has_links, detailed_specs),
            'timeline': '1-2 weeks'
        },
        {
            'phase': 2,
            'name': 'Specification Enhancement',
            'description': 'Enhance specifications for products with basic data',
            'estimated_products': analysis['specification_quality']['basic'],
            'timeline': '2-3 weeks'
        },
        {
            'phase': 3,
            'name': 'Placeholder Creation',
            'description': 'Create placeholders for remaining products',
            'estimated_products': analysis['specification_quality']['minimal'],
            'timeline': '1 week'
        }
    ]
    
    # Immediate actions
    recommendations['immediate_actions'] = [
        'Analyze drive link accessibility and validity',
        'Categorize missing products by business priority',
        'Implement data quality flags in JSON structure',
        'Create enhancement workflow for low-quality products'
    ]
    
    # Long-term goals
    recommendations['long_term_goals'] = [
        'Achieve 100% product catalog coverage',
        'Standardize specification formats across all products',
        'Implement automated data quality monitoring',
        'Establish continuous product data enhancement pipeline'
    ]
    
    return recommendations

def save_analysis_report(analysis: Dict[str, Any], strategies: Dict[str, Any], recommendations: Dict[str, Any]) -> None:
    """Save comprehensive analysis report."""
    
    report = {
        'analysis_timestamp': pd.Timestamp.now().isoformat(),
        'executive_summary': {
            'total_missing_products': analysis['missing_count'],
            'primary_recommendation': recommendations['primary_recommendation'],
            'rationale': recommendations.get('rationale', ''),
            'immediate_impact': f"Can immediately include {recommendations['implementation_phases'][0]['estimated_products']} high-quality products"
        },
        'detailed_analysis': analysis,
        'strategy_evaluation': strategies,
        'recommendations': recommendations
    }
    
    # Save detailed report
    with open('full_catalog_strategy_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Create summary markdown report
    create_summary_report(report)

def create_summary_report(report: Dict[str, Any]) -> None:
    """Create a markdown summary report."""
    
    analysis = report['detailed_analysis']
    strategies = report['strategy_evaluation']
    recommendations = report['recommendations']
    
    markdown_content = f"""# Full Product Catalog Integration Strategy

## Executive Summary

- **Missing Products**: {analysis['missing_count']} out of {analysis['total_csv_products']} total products
- **Current JSON Coverage**: {analysis['total_json_products']} products ({analysis['total_json_products']/analysis['total_csv_products']*100:.1f}%)
- **Recommended Strategy**: {recommendations['primary_recommendation'].replace('_', ' ').title()}
- **Rationale**: {recommendations.get('rationale', '')}

## Missing Products Analysis

### Drive Link Status
- Products with drive links: {analysis['drive_link_analysis']['has_link']}
- Products without drive links: {analysis['drive_link_analysis']['no_link']}
- Products with empty links: {analysis['drive_link_analysis']['empty_link']}

### Specification Quality
- Detailed specifications (>200 chars): {analysis['specification_quality']['detailed']}
- Basic specifications (50-200 chars): {analysis['specification_quality']['basic']}
- Minimal specifications (<50 chars): {analysis['specification_quality']['minimal']}

### Category Distribution
"""
    
    for category, count in sorted(analysis['category_distribution'].items(), key=lambda x: x[1], reverse=True):
        markdown_content += f"- {category}: {count} products\n"
    
    markdown_content += "\n## Strategy Evaluation\n\n"
    
    for strategy_id, strategy in strategies.items():
        markdown_content += f"### {strategy['name']}\n\n"
        markdown_content += f"**Description**: {strategy['description']}\n\n"
        markdown_content += f"**Estimated Products**: {strategy['estimated_products']}\n\n"
        
        markdown_content += "**Pros**:\n"
        for pro in strategy['pros']:
            markdown_content += f"- {pro}\n"
        
        markdown_content += "\n**Cons**:\n"
        for con in strategy['cons']:
            markdown_content += f"- {con}\n"
        
        markdown_content += "\n"
    
    markdown_content += "## Implementation Recommendations\n\n"
    
    for i, phase in enumerate(recommendations['implementation_phases'], 1):
        markdown_content += f"### Phase {phase['phase']}: {phase['name']}\n\n"
        markdown_content += f"- **Description**: {phase['description']}\n"
        markdown_content += f"- **Estimated Products**: {phase['estimated_products']}\n"
        markdown_content += f"- **Timeline**: {phase['timeline']}\n\n"
    
    markdown_content += "## Immediate Actions\n\n"
    for action in recommendations['immediate_actions']:
        markdown_content += f"- {action}\n"
    
    markdown_content += "\n## Long-term Goals\n\n"
    for goal in recommendations['long_term_goals']:
        markdown_content += f"- {goal}\n"
    
    with open('full_catalog_strategy_summary.md', 'w', encoding='utf-8') as f:
        f.write(markdown_content)

def main():
    """Main execution function."""
    try:
        print("🔍 Analyzing missing products and evaluation strategies...\n")
        
        # Analyze missing products
        analysis = analyze_missing_products()
        
        print(f"\n📊 Analysis Results:")
        print(f"   Missing products: {analysis['missing_count']}")
        print(f"   Products with drive links: {analysis['drive_link_analysis']['has_link']}")
        print(f"   Products with detailed specs: {analysis['specification_quality']['detailed']}")
        
        # Evaluate strategies
        print("\n🎯 Evaluating incorporation strategies...")
        strategies = evaluate_incorporation_strategies(analysis)
        
        # Generate recommendations
        print("\n💡 Generating recommendations...")
        recommendations = generate_recommendations(analysis, strategies)
        
        print(f"\n✅ Primary Recommendation: {recommendations['primary_recommendation'].replace('_', ' ').title()}")
        print(f"   Rationale: {recommendations.get('rationale', '')}")
        
        # Save reports
        print("\n📄 Saving analysis reports...")
        save_analysis_report(analysis, strategies, recommendations)
        
        print("\n🎉 Full catalog strategy analysis completed!")
        print("   📋 Detailed report: full_catalog_strategy_analysis.json")
        print("   📝 Summary report: full_catalog_strategy_summary.md")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        raise

if __name__ == "__main__":
    main()