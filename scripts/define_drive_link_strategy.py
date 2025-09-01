#!/usr/bin/env python3

import json
import pandas as pd
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import os
from urllib.parse import urlparse

def analyze_drive_link_patterns() -> Dict[str, Any]:
    """Analyze drive link patterns and quality across all products."""
    
    print("Loading CSV data for drive link analysis...")
    
    # Load CSV data
    csv_file = 'SMART HOME FOLLOWING PROJECT - All Products.csv'
    df = pd.read_csv(csv_file)
    
    analysis = {
        'total_products': len(df),
        'drive_link_categories': {
            'valid_links': 0,
            'invalid_links': 0,
            'empty_links': 0,
            'missing_links': 0
        },
        'link_patterns': defaultdict(int),
        'products_by_link_status': {
            'with_valid_links': [],
            'with_invalid_links': [],
            'without_links': []
        },
        'category_link_distribution': defaultdict(lambda: {'with_links': 0, 'without_links': 0}),
        'supplier_link_distribution': defaultdict(lambda: {'with_links': 0, 'without_links': 0})
    }
    
    print(f"Analyzing {len(df)} products for drive link patterns...")
    
    for _, row in df.iterrows():
        product_id = str(row['Model Number'])
        product_name = row.get('Product Name', 'Unknown')
        category = row.get('Category', 'Unknown')
        supplier = row.get('Supplier', 'Unknown')
        drive_link = str(row.get('Drive Link', '')).strip()
        
        product_info = {
            'id': product_id,
            'name': product_name,
            'category': category,
            'supplier': supplier,
            'drive_link': drive_link
        }
        
        # Categorize drive link status
        if not drive_link or drive_link.lower() in ['nan', 'none', '']:
            analysis['drive_link_categories']['missing_links'] += 1
            analysis['products_by_link_status']['without_links'].append(product_info)
            analysis['category_link_distribution'][category]['without_links'] += 1
            analysis['supplier_link_distribution'][supplier]['without_links'] += 1
        elif is_valid_drive_link(drive_link):
            analysis['drive_link_categories']['valid_links'] += 1
            analysis['products_by_link_status']['with_valid_links'].append(product_info)
            analysis['category_link_distribution'][category]['with_links'] += 1
            analysis['supplier_link_distribution'][supplier]['with_links'] += 1
            
            # Extract link pattern
            pattern = extract_link_pattern(drive_link)
            analysis['link_patterns'][pattern] += 1
        else:
            analysis['drive_link_categories']['invalid_links'] += 1
            analysis['products_by_link_status']['with_invalid_links'].append(product_info)
            analysis['category_link_distribution'][category]['without_links'] += 1
            analysis['supplier_link_distribution'][supplier]['without_links'] += 1
    
    return analysis

def is_valid_drive_link(link: str) -> bool:
    """Check if a drive link appears to be valid."""
    if not link or link.lower() in ['nan', 'none', '']:
        return False
    
    # Check for common Google Drive patterns
    drive_patterns = [
        'drive.google.com',
        'docs.google.com',
        'googleapis.com'
    ]
    
    link_lower = link.lower()
    return any(pattern in link_lower for pattern in drive_patterns)

def extract_link_pattern(link: str) -> str:
    """Extract the pattern/type of the drive link."""
    try:
        parsed = urlparse(link)
        domain = parsed.netloc.lower()
        
        if 'drive.google.com' in domain:
            if '/folders/' in link:
                return 'google_drive_folder'
            elif '/file/' in link:
                return 'google_drive_file'
            else:
                return 'google_drive_other'
        elif 'docs.google.com' in domain:
            return 'google_docs'
        else:
            return 'other_link'
    except:
        return 'invalid_format'

def define_strategies() -> Dict[str, Any]:
    """Define strategies for handling products without drive links."""
    
    strategies = {
        'strategy_1_exclusion': {
            'name': 'Exclusion Strategy',
            'description': 'Exclude products without valid drive links from JSON files',
            'approach': 'Quality-first approach maintaining current standards',
            'implementation': {
                'criteria': 'Only include products with valid Google Drive links',
                'validation': 'Verify link accessibility before inclusion',
                'fallback': 'None - products excluded permanently'
            },
            'pros': [
                'Maintains consistent data quality',
                'Ensures all products have supporting documentation',
                'Simple implementation and maintenance',
                'Clear quality standards'
            ],
            'cons': [
                'Reduces catalog completeness',
                'May exclude valuable products',
                'Potential loss of business opportunities',
                'Incomplete product representation'
            ],
            'use_cases': [
                'High-quality product catalogs',
                'Customer-facing applications',
                'Premium product showcases'
            ]
        },
        'strategy_2_placeholder': {
            'name': 'Placeholder Strategy',
            'description': 'Include products with placeholder drive links and enhancement flags',
            'approach': 'Completeness-first with quality indicators',
            'implementation': {
                'criteria': 'Include all products with quality flags',
                'placeholder_format': 'Standard placeholder URL or "TBD" marker',
                'enhancement_queue': 'Track products needing drive link updates'
            },
            'pros': [
                'Complete catalog representation',
                'Clear enhancement roadmap',
                'Maintains product visibility',
                'Allows for future improvements'
            ],
            'cons': [
                'May confuse users with incomplete data',
                'Requires additional metadata management',
                'Ongoing maintenance overhead',
                'Potential quality perception issues'
            ],
            'use_cases': [
                'Internal product management',
                'Comprehensive catalogs',
                'Development environments'
            ]
        },
        'strategy_3_alternative_sourcing': {
            'name': 'Alternative Sourcing Strategy',
            'description': 'Source alternative documentation for products without drive links',
            'approach': 'Active enhancement through alternative sources',
            'implementation': {
                'criteria': 'Research and source alternative documentation',
                'sources': 'Manufacturer websites, product databases, specifications sheets',
                'validation': 'Verify accuracy and completeness of sourced data'
            },
            'pros': [
                'Maintains high data quality',
                'Complete product coverage',
                'Enhanced product information',
                'Professional documentation standards'
            ],
            'cons': [
                'Significant time and resource investment',
                'Potential copyright and licensing issues',
                'Ongoing maintenance requirements',
                'Variable data quality from different sources'
            ],
            'use_cases': [
                'Professional product catalogs',
                'Sales and marketing materials',
                'Customer documentation'
            ]
        },
        'strategy_4_tiered_approach': {
            'name': 'Tiered Quality Approach',
            'description': 'Implement quality tiers based on drive link availability',
            'approach': 'Multi-tier system with clear quality indicators',
            'implementation': {
                'tier_1': 'Products with valid drive links (premium tier)',
                'tier_2': 'Products with detailed specifications but no links (standard tier)',
                'tier_3': 'Products with basic information only (basic tier)',
                'metadata': 'Clear tier indicators in product data'
            },
            'pros': [
                'Balanced approach to quality and completeness',
                'Clear quality expectations for users',
                'Flexible implementation options',
                'Scalable enhancement pathway'
            ],
            'cons': [
                'Complex metadata management',
                'Potential user confusion with tiers',
                'Requires careful tier definition',
                'Ongoing tier maintenance'
            ],
            'use_cases': [
                'Multi-purpose catalogs',
                'Flexible product databases',
                'Scalable product management'
            ]
        }
    }
    
    return strategies

def generate_recommendations(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Generate specific recommendations based on drive link analysis."""
    
    total_products = analysis['total_products']
    valid_links = analysis['drive_link_categories']['valid_links']
    missing_links = analysis['drive_link_categories']['missing_links']
    
    # Calculate percentages
    valid_percentage = (valid_links / total_products) * 100
    missing_percentage = (missing_links / total_products) * 100
    
    recommendations = {
        'primary_recommendation': '',
        'rationale': '',
        'implementation_plan': [],
        'immediate_actions': [],
        'quality_thresholds': {},
        'enhancement_priorities': [],
        'resource_requirements': {}
    }
    
    # Determine primary recommendation based on link availability
    if valid_percentage >= 60:
        recommendations['primary_recommendation'] = 'strategy_1_exclusion'
        recommendations['rationale'] = f"With {valid_percentage:.1f}% of products having valid drive links, exclusion strategy maintains high quality standards."
    elif valid_percentage >= 30:
        recommendations['primary_recommendation'] = 'strategy_4_tiered_approach'
        recommendations['rationale'] = f"With {valid_percentage:.1f}% valid links, a tiered approach balances quality and completeness."
    elif missing_percentage <= 50:
        recommendations['primary_recommendation'] = 'strategy_3_alternative_sourcing'
        recommendations['rationale'] = f"With {missing_percentage:.1f}% missing links, alternative sourcing can achieve comprehensive coverage."
    else:
        recommendations['primary_recommendation'] = 'strategy_2_placeholder'
        recommendations['rationale'] = f"With {missing_percentage:.1f}% missing links, placeholder strategy ensures catalog completeness."
    
    # Implementation plan
    recommendations['implementation_plan'] = [
        {
            'phase': 1,
            'name': 'Link Validation and Cleanup',
            'description': 'Validate existing drive links and fix broken ones',
            'timeline': '1 week',
            'deliverables': ['Validated link inventory', 'Broken link report']
        },
        {
            'phase': 2,
            'name': 'Strategy Implementation',
            'description': 'Implement chosen strategy for products without links',
            'timeline': '2-3 weeks',
            'deliverables': ['Updated product data', 'Quality tier assignments']
        },
        {
            'phase': 3,
            'name': 'Enhancement Pipeline',
            'description': 'Establish ongoing process for link enhancement',
            'timeline': '1 week',
            'deliverables': ['Enhancement workflow', 'Quality monitoring system']
        }
    ]
    
    # Immediate actions
    recommendations['immediate_actions'] = [
        'Audit all existing drive links for accessibility',
        'Categorize products by link quality and availability',
        'Identify high-priority products for alternative sourcing',
        'Establish quality standards for different product tiers',
        'Create enhancement workflow for ongoing improvements'
    ]
    
    # Quality thresholds
    recommendations['quality_thresholds'] = {
        'tier_1_premium': 'Valid drive link + detailed specifications',
        'tier_2_standard': 'Detailed specifications without drive link',
        'tier_3_basic': 'Basic product information only',
        'exclusion_criteria': 'Insufficient product information'
    }
    
    return recommendations

def save_strategy_report(analysis: Dict[str, Any], strategies: Dict[str, Any], recommendations: Dict[str, Any]) -> None:
    """Save comprehensive drive link strategy report."""
    
    report = {
        'analysis_timestamp': pd.Timestamp.now().isoformat(),
        'executive_summary': {
            'total_products': analysis['total_products'],
            'valid_drive_links': analysis['drive_link_categories']['valid_links'],
            'missing_drive_links': analysis['drive_link_categories']['missing_links'],
            'primary_recommendation': recommendations['primary_recommendation'],
            'rationale': recommendations['rationale']
        },
        'detailed_analysis': analysis,
        'strategy_options': strategies,
        'recommendations': recommendations
    }
    
    # Save detailed report
    with open('drive_link_strategy_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Create summary markdown report
    create_strategy_summary(report)

def create_strategy_summary(report: Dict[str, Any]) -> None:
    """Create a markdown summary of the drive link strategy."""
    
    analysis = report['detailed_analysis']
    strategies = report['strategy_options']
    recommendations = report['recommendations']
    
    markdown_content = f"""# Drive Link Strategy Analysis

## Executive Summary

- **Total Products**: {analysis['total_products']}
- **Valid Drive Links**: {analysis['drive_link_categories']['valid_links']} ({analysis['drive_link_categories']['valid_links']/analysis['total_products']*100:.1f}%)
- **Missing Drive Links**: {analysis['drive_link_categories']['missing_links']} ({analysis['drive_link_categories']['missing_links']/analysis['total_products']*100:.1f}%)
- **Invalid Drive Links**: {analysis['drive_link_categories']['invalid_links']}
- **Recommended Strategy**: {recommendations['primary_recommendation'].replace('_', ' ').title()}
- **Rationale**: {recommendations['rationale']}

## Drive Link Analysis

### Link Status Distribution
- Valid links: {analysis['drive_link_categories']['valid_links']}
- Invalid links: {analysis['drive_link_categories']['invalid_links']}
- Missing links: {analysis['drive_link_categories']['missing_links']}

### Link Patterns
"""
    
    for pattern, count in analysis['link_patterns'].items():
        markdown_content += f"- {pattern.replace('_', ' ').title()}: {count}\n"
    
    markdown_content += "\n### Category Distribution (Top 10)\n\n"
    
    # Sort categories by total products
    sorted_categories = sorted(
        analysis['category_link_distribution'].items(),
        key=lambda x: x[1]['with_links'] + x[1]['without_links'],
        reverse=True
    )[:10]
    
    for category, stats in sorted_categories:
        total = stats['with_links'] + stats['without_links']
        with_links_pct = (stats['with_links'] / total * 100) if total > 0 else 0
        markdown_content += f"- **{category}**: {total} products ({stats['with_links']} with links, {with_links_pct:.1f}%)\n"
    
    markdown_content += "\n## Strategy Options\n\n"
    
    for strategy_id, strategy in strategies.items():
        markdown_content += f"### {strategy['name']}\n\n"
        markdown_content += f"**Description**: {strategy['description']}\n\n"
        markdown_content += f"**Approach**: {strategy['approach']}\n\n"
        
        markdown_content += "**Pros**:\n"
        for pro in strategy['pros']:
            markdown_content += f"- {pro}\n"
        
        markdown_content += "\n**Cons**:\n"
        for con in strategy['cons']:
            markdown_content += f"- {con}\n"
        
        markdown_content += "\n**Use Cases**:\n"
        for use_case in strategy['use_cases']:
            markdown_content += f"- {use_case}\n"
        
        markdown_content += "\n"
    
    markdown_content += "## Implementation Recommendations\n\n"
    
    for phase in recommendations['implementation_plan']:
        markdown_content += f"### Phase {phase['phase']}: {phase['name']}\n\n"
        markdown_content += f"- **Description**: {phase['description']}\n"
        markdown_content += f"- **Timeline**: {phase['timeline']}\n"
        markdown_content += f"- **Deliverables**: {', '.join(phase['deliverables'])}\n\n"
    
    markdown_content += "## Quality Thresholds\n\n"
    for tier, criteria in recommendations['quality_thresholds'].items():
        markdown_content += f"- **{tier.replace('_', ' ').title()}**: {criteria}\n"
    
    markdown_content += "\n## Immediate Actions\n\n"
    for action in recommendations['immediate_actions']:
        markdown_content += f"- {action}\n"
    
    with open('drive_link_strategy_summary.md', 'w', encoding='utf-8') as f:
        f.write(markdown_content)

def main():
    """Main execution function."""
    try:
        print("🔗 Analyzing drive link patterns and defining strategies...\n")
        
        # Analyze drive link patterns
        analysis = analyze_drive_link_patterns()
        
        print(f"\n📊 Drive Link Analysis Results:")
        print(f"   Total products: {analysis['total_products']}")
        print(f"   Valid drive links: {analysis['drive_link_categories']['valid_links']}")
        print(f"   Missing drive links: {analysis['drive_link_categories']['missing_links']}")
        print(f"   Invalid drive links: {analysis['drive_link_categories']['invalid_links']}")
        
        # Define strategies
        print("\n🎯 Defining drive link strategies...")
        strategies = define_strategies()
        
        # Generate recommendations
        print("\n💡 Generating recommendations...")
        recommendations = generate_recommendations(analysis)
        
        print(f"\n✅ Primary Recommendation: {recommendations['primary_recommendation'].replace('_', ' ').title()}")
        print(f"   Rationale: {recommendations['rationale']}")
        
        # Save reports
        print("\n📄 Saving strategy reports...")
        save_strategy_report(analysis, strategies, recommendations)
        
        print("\n🎉 Drive link strategy analysis completed!")
        print("   📋 Detailed report: drive_link_strategy_analysis.json")
        print("   📝 Summary report: drive_link_strategy_summary.md")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        raise

if __name__ == "__main__":
    main()