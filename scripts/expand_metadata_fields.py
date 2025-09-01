#!/usr/bin/env python3

import json
import pandas as pd
from typing import Dict, List, Any, Set
from collections import defaultdict, Counter
import re
from datetime import datetime

def analyze_current_metadata() -> Dict[str, Any]:
    """Analyze current metadata structure and identify enhancement opportunities."""
    
    print("Loading current product data for metadata analysis...")
    
    # Load enhanced product data
    with open('products_hierarchical_enhanced_v2.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    analysis = {
        'current_structure': {},
        'field_coverage': {},
        'value_patterns': {},
        'missing_fields': [],
        'enhancement_opportunities': [],
        'standardization_needs': []
    }
    
    # Analyze current structure
    sample_product = None
    total_products = 0
    
    # Process categories structure
    categories_processed = 0
    if 'categories' in data:
        for category_name, category_data in data['categories'].items():
            if 'products' in category_data:
                categories_processed += 1
                for product in category_data['products']:
                    total_products += 1
                    if sample_product is None:
                        sample_product = product
                        analysis['current_structure'] = extract_structure(product)
    
    print(f"Analyzing {total_products} products across {categories_processed} categories...")
    
    # Analyze field coverage and patterns
    field_stats = defaultdict(lambda: {'present': 0, 'missing': 0, 'values': set()})
    
    if 'categories' in data:
        for category_name, category_data in data['categories'].items():
            if 'products' in category_data:
                for product in category_data['products']:
                    analyze_product_fields(product, field_stats)
    
    # Convert to analysis format
    for field, stats in field_stats.items():
        coverage_pct = (stats['present'] / total_products) * 100
        analysis['field_coverage'][field] = {
            'present': stats['present'],
            'missing': stats['missing'],
            'coverage_percentage': coverage_pct,
            'unique_values': len(stats['values']),
            'sample_values': list(stats['values'])[:10]  # First 10 unique values
        }
    
    # Identify enhancement opportunities
    analysis['enhancement_opportunities'] = identify_enhancement_opportunities(analysis['field_coverage'])
    analysis['missing_fields'] = identify_missing_fields()
    analysis['standardization_needs'] = identify_standardization_needs(field_stats)
    
    return analysis

def extract_structure(product: Dict[str, Any], prefix: str = '') -> Dict[str, str]:
    """Extract the structure of a product object."""
    structure = {}
    
    for key, value in product.items():
        full_key = f"{prefix}.{key}" if prefix else key
        
        if isinstance(value, dict):
            structure.update(extract_structure(value, full_key))
        elif isinstance(value, list):
            if value and isinstance(value[0], dict):
                structure[full_key] = f"list[dict] (sample: {list(value[0].keys())[:3]})"
            else:
                structure[full_key] = f"list[{type(value[0]).__name__ if value else 'unknown'}]"
        else:
            structure[full_key] = type(value).__name__
    
    return structure

def analyze_product_fields(product: Dict[str, Any], field_stats: Dict, prefix: str = '') -> None:
    """Analyze fields in a product for coverage and patterns."""
    
    for key, value in product.items():
        full_key = f"{prefix}.{key}" if prefix else key
        
        if value is not None and value != '' and value != []:
            field_stats[full_key]['present'] += 1
            if isinstance(value, (str, int, float, bool)):
                field_stats[full_key]['values'].add(str(value)[:100])  # Limit value length
            elif isinstance(value, dict):
                analyze_product_fields(value, field_stats, full_key)
            elif isinstance(value, list) and value:
                field_stats[full_key]['values'].add(f"list_length_{len(value)}")
        else:
            field_stats[full_key]['missing'] += 1

def identify_enhancement_opportunities(field_coverage: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Identify opportunities for metadata enhancement."""
    
    opportunities = []
    
    for field, stats in field_coverage.items():
        coverage = stats['coverage_percentage']
        
        if coverage < 50:
            opportunities.append({
                'field': field,
                'type': 'low_coverage',
                'coverage': coverage,
                'priority': 'high' if coverage < 25 else 'medium',
                'recommendation': f"Enhance {field} coverage from {coverage:.1f}% to >80%"
            })
        
        if stats['unique_values'] < 5 and stats['present'] > 10:
            opportunities.append({
                'field': field,
                'type': 'limited_diversity',
                'unique_values': stats['unique_values'],
                'priority': 'medium',
                'recommendation': f"Expand {field} value diversity (currently {stats['unique_values']} unique values)"
            })
    
    return opportunities

def identify_missing_fields() -> List[Dict[str, Any]]:
    """Identify missing metadata fields that should be added."""
    
    missing_fields = [
        {
            'field': 'metadata.tags',
            'description': 'Searchable tags for product discovery',
            'type': 'list[string]',
            'priority': 'high',
            'examples': ['smart-home', 'security', 'energy-efficient', 'voice-control']
        },
        {
            'field': 'metadata.search_keywords',
            'description': 'SEO and search optimization keywords',
            'type': 'list[string]',
            'priority': 'high',
            'examples': ['smart doorbell', 'wireless camera', 'home automation']
        },
        {
            'field': 'metadata.compatibility_ecosystem',
            'description': 'Compatible smart home ecosystems',
            'type': 'list[string]',
            'priority': 'high',
            'examples': ['Google Home', 'Amazon Alexa', 'Apple HomeKit', 'Samsung SmartThings']
        },
        {
            'field': 'metadata.installation_complexity',
            'description': 'Installation difficulty level',
            'type': 'string',
            'priority': 'medium',
            'examples': ['Easy', 'Moderate', 'Professional Required']
        },
        {
            'field': 'metadata.energy_rating',
            'description': 'Energy efficiency rating',
            'type': 'string',
            'priority': 'medium',
            'examples': ['A+++', 'A++', 'A+', 'A', 'B']
        },
        {
            'field': 'metadata.warranty_period',
            'description': 'Product warranty duration',
            'type': 'string',
            'priority': 'medium',
            'examples': ['1 year', '2 years', '3 years', 'Lifetime']
        },
        {
            'field': 'metadata.price_range',
            'description': 'Product price category',
            'type': 'string',
            'priority': 'medium',
            'examples': ['Budget', 'Mid-range', 'Premium', 'Luxury']
        },
        {
            'field': 'metadata.target_audience',
            'description': 'Primary target user group',
            'type': 'list[string]',
            'priority': 'medium',
            'examples': ['Homeowners', 'Renters', 'Tech Enthusiasts', 'Seniors']
        },
        {
            'field': 'metadata.use_cases',
            'description': 'Primary use case scenarios',
            'type': 'list[string]',
            'priority': 'high',
            'examples': ['Home Security', 'Energy Management', 'Entertainment', 'Convenience']
        },
        {
            'field': 'metadata.certification_standards',
            'description': 'Industry certifications and standards',
            'type': 'list[string]',
            'priority': 'medium',
            'examples': ['FCC', 'CE', 'UL', 'Energy Star', 'Matter']
        },
        {
            'field': 'metadata.last_updated',
            'description': 'Last metadata update timestamp',
            'type': 'string',
            'priority': 'low',
            'examples': ['2024-01-15T10:30:00Z']
        },
        {
            'field': 'metadata.data_quality_score',
            'description': 'Completeness and quality score (0-100)',
            'type': 'number',
            'priority': 'low',
            'examples': [85, 92, 78]
        }
    ]
    
    return missing_fields

def identify_standardization_needs(field_stats: Dict) -> List[Dict[str, Any]]:
    """Identify fields that need value standardization."""
    
    standardization_needs = []
    
    # Check for fields with inconsistent formatting
    for field, stats in field_stats.items():
        if stats['present'] > 5:  # Only check fields with sufficient data
            values = list(stats['values'])
            
            # Check for case inconsistencies
            if has_case_inconsistencies(values):
                standardization_needs.append({
                    'field': field,
                    'issue': 'case_inconsistency',
                    'priority': 'medium',
                    'recommendation': f"Standardize case formatting for {field}",
                    'examples': values[:5]
                })
            
            # Check for unit inconsistencies
            if has_unit_inconsistencies(values):
                standardization_needs.append({
                    'field': field,
                    'issue': 'unit_inconsistency',
                    'priority': 'high',
                    'recommendation': f"Standardize units for {field}",
                    'examples': values[:5]
                })
    
    return standardization_needs

def has_case_inconsistencies(values: List[str]) -> bool:
    """Check if values have case inconsistencies."""
    if len(values) < 2:
        return False
    
    normalized = set(v.lower() for v in values if isinstance(v, str))
    return len(normalized) < len(set(v for v in values if isinstance(v, str)))

def has_unit_inconsistencies(values: List[str]) -> bool:
    """Check if values have unit inconsistencies."""
    unit_patterns = [
        r'\d+\s*(mm|cm|m|inch|in|ft)',  # Length units
        r'\d+\s*(g|kg|lb|oz)',          # Weight units
        r'\d+\s*(v|volt|volts)',        # Voltage units
        r'\d+\s*(w|watt|watts)',        # Power units
        r'\d+\s*(mah|ah)',              # Battery units
    ]
    
    for pattern in unit_patterns:
        matches = [v for v in values if isinstance(v, str) and re.search(pattern, v.lower())]
        if len(matches) > 1:
            # Check if units are consistent
            units = [re.search(pattern, v.lower()).group(1) for v in matches]
            if len(set(units)) > 1:
                return True
    
    return False

def generate_enhancement_plan(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a comprehensive metadata enhancement plan."""
    
    plan = {
        'overview': {
            'current_fields': len(analysis['current_structure']),
            'proposed_new_fields': len(analysis['missing_fields']),
            'enhancement_opportunities': len(analysis['enhancement_opportunities']),
            'standardization_needs': len(analysis['standardization_needs'])
        },
        'implementation_phases': [],
        'field_additions': analysis['missing_fields'],
        'field_enhancements': analysis['enhancement_opportunities'],
        'standardization_tasks': analysis['standardization_needs'],
        'automation_opportunities': [],
        'quality_metrics': {}
    }
    
    # Define implementation phases
    plan['implementation_phases'] = [
        {
            'phase': 1,
            'name': 'Critical Metadata Addition',
            'duration': '1 week',
            'description': 'Add high-priority metadata fields for searchability',
            'tasks': [
                'Add tags field for product categorization',
                'Add search_keywords for SEO optimization',
                'Add compatibility_ecosystem for smart home integration',
                'Add use_cases for application scenarios'
            ],
            'deliverables': ['Enhanced product schema', 'Metadata population scripts']
        },
        {
            'phase': 2,
            'name': 'Data Quality Enhancement',
            'duration': '2 weeks',
            'description': 'Improve existing field coverage and standardization',
            'tasks': [
                'Enhance low-coverage fields to >80%',
                'Standardize unit formats across specifications',
                'Normalize case formatting for categorical fields',
                'Validate and clean existing metadata'
            ],
            'deliverables': ['Data quality report', 'Standardization guidelines']
        },
        {
            'phase': 3,
            'name': 'Advanced Metadata Features',
            'duration': '1 week',
            'description': 'Add advanced metadata for enhanced functionality',
            'tasks': [
                'Add installation_complexity ratings',
                'Add energy_rating classifications',
                'Add warranty_period information',
                'Add price_range categories'
            ],
            'deliverables': ['Complete metadata schema', 'Population workflows']
        },
        {
            'phase': 4,
            'name': 'Automation and Monitoring',
            'duration': '1 week',
            'description': 'Implement automated metadata management',
            'tasks': [
                'Create data quality scoring system',
                'Implement automated metadata validation',
                'Set up metadata update tracking',
                'Create enhancement monitoring dashboard'
            ],
            'deliverables': ['Automation scripts', 'Quality monitoring system']
        }
    ]
    
    # Identify automation opportunities
    plan['automation_opportunities'] = [
        {
            'task': 'Tag Generation',
            'description': 'Auto-generate tags from product names and categories',
            'complexity': 'Low',
            'impact': 'High'
        },
        {
            'task': 'Keyword Extraction',
            'description': 'Extract search keywords from descriptions and specifications',
            'complexity': 'Medium',
            'impact': 'High'
        },
        {
            'task': 'Compatibility Detection',
            'description': 'Detect ecosystem compatibility from specifications',
            'complexity': 'Medium',
            'impact': 'Medium'
        },
        {
            'task': 'Use Case Classification',
            'description': 'Classify use cases based on product category and features',
            'complexity': 'High',
            'impact': 'Medium'
        }
    ]
    
    # Define quality metrics
    plan['quality_metrics'] = {
        'completeness_score': 'Percentage of fields populated per product',
        'consistency_score': 'Standardization level across similar fields',
        'accuracy_score': 'Validation success rate for metadata values',
        'searchability_score': 'Effectiveness of tags and keywords for discovery',
        'overall_quality_score': 'Weighted average of all quality metrics'
    }
    
    return plan

def create_enhanced_schema() -> Dict[str, Any]:
    """Create an enhanced product schema with new metadata fields."""
    
    schema = {
        'product_schema_v2': {
            'id': {'type': 'string', 'required': True, 'description': 'Unique product identifier'},
            'name': {'type': 'string', 'required': True, 'description': 'Product name'},
            'category': {'type': 'string', 'required': True, 'description': 'Product category'},
            'supplier': {'type': 'string', 'required': True, 'description': 'Product supplier/manufacturer'},
            'description': {'type': 'string', 'required': False, 'description': 'Detailed product description'},
            'specifications': {
                'type': 'object',
                'required': False,
                'description': 'Technical specifications',
                'properties': {
                    'power_source': {'type': 'string', 'standardized_values': ['Battery', 'AC Power', 'DC Power', 'Solar', 'Hybrid']},
                    'communication_protocol': {'type': 'array', 'items': {'type': 'string'}},
                    'dimensions': {'type': 'object', 'standardized_units': ['mm', 'cm', 'inch']},
                    'weight': {'type': 'string', 'standardized_units': ['g', 'kg', 'lb']},
                    'operating_voltage': {'type': 'string', 'standardized_units': ['V', 'VDC', 'VAC']},
                    'power_consumption': {'type': 'string', 'standardized_units': ['W', 'mW']}
                }
            },
            'metadata': {
                'type': 'object',
                'required': True,
                'description': 'Enhanced metadata for searchability and categorization',
                'properties': {
                    'tags': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Searchable tags for product discovery',
                        'examples': ['smart-home', 'security', 'wireless', 'voice-control']
                    },
                    'search_keywords': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'SEO and search optimization keywords',
                        'examples': ['smart doorbell', 'wireless camera', 'home automation']
                    },
                    'compatibility_ecosystem': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Compatible smart home ecosystems',
                        'standardized_values': ['Google Home', 'Amazon Alexa', 'Apple HomeKit', 'Samsung SmartThings', 'Tuya Smart', 'Matter']
                    },
                    'use_cases': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Primary use case scenarios',
                        'standardized_values': ['Home Security', 'Energy Management', 'Entertainment', 'Convenience', 'Health & Safety', 'Lighting Control']
                    },
                    'installation_complexity': {
                        'type': 'string',
                        'description': 'Installation difficulty level',
                        'standardized_values': ['Easy', 'Moderate', 'Professional Required']
                    },
                    'energy_rating': {
                        'type': 'string',
                        'description': 'Energy efficiency rating',
                        'standardized_values': ['A+++', 'A++', 'A+', 'A', 'B', 'C', 'D']
                    },
                    'warranty_period': {
                        'type': 'string',
                        'description': 'Product warranty duration',
                        'examples': ['1 year', '2 years', '3 years', 'Lifetime']
                    },
                    'price_range': {
                        'type': 'string',
                        'description': 'Product price category',
                        'standardized_values': ['Budget', 'Mid-range', 'Premium', 'Luxury']
                    },
                    'target_audience': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Primary target user group',
                        'standardized_values': ['Homeowners', 'Renters', 'Tech Enthusiasts', 'Seniors', 'Families', 'Professionals']
                    },
                    'certification_standards': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'Industry certifications and standards',
                        'examples': ['FCC', 'CE', 'UL', 'Energy Star', 'Matter', 'Thread', 'Zigbee']
                    },
                    'last_updated': {
                        'type': 'string',
                        'format': 'datetime',
                        'description': 'Last metadata update timestamp'
                    },
                    'data_quality_score': {
                        'type': 'number',
                        'minimum': 0,
                        'maximum': 100,
                        'description': 'Completeness and quality score (0-100)'
                    }
                }
            },
            'drive_link': {'type': 'string', 'required': False, 'description': 'Google Drive link to product documentation'},
            'enhancement_history': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'timestamp': {'type': 'string', 'format': 'datetime'},
                        'enhancement_type': {'type': 'string'},
                        'fields_modified': {'type': 'array', 'items': {'type': 'string'}},
                        'source': {'type': 'string'}
                    }
                },
                'description': 'History of metadata enhancements'
            }
        }
    }
    
    return schema

def save_metadata_analysis(analysis: Dict[str, Any], plan: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """Save comprehensive metadata analysis and enhancement plan."""
    
    report = {
        'analysis_timestamp': datetime.now().isoformat(),
        'executive_summary': {
            'current_fields': len(analysis['current_structure']),
            'proposed_new_fields': len(analysis['missing_fields']),
            'enhancement_opportunities': len(analysis['enhancement_opportunities']),
            'standardization_needs': len(analysis['standardization_needs']),
            'implementation_phases': len(plan['implementation_phases'])
        },
        'current_analysis': analysis,
        'enhancement_plan': plan,
        'enhanced_schema': schema
    }
    
    # Save detailed report
    with open('metadata_enhancement_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Create summary markdown
    create_metadata_summary(report)

def create_metadata_summary(report: Dict[str, Any]) -> None:
    """Create a markdown summary of the metadata enhancement plan."""
    
    analysis = report['current_analysis']
    plan = report['enhancement_plan']
    
    markdown_content = f"""# Metadata Enhancement Analysis

## Executive Summary

- **Current Metadata Fields**: {len(analysis['current_structure'])}
- **Proposed New Fields**: {len(analysis['missing_fields'])}
- **Enhancement Opportunities**: {len(analysis['enhancement_opportunities'])}
- **Standardization Needs**: {len(analysis['standardization_needs'])}
- **Implementation Phases**: {len(plan['implementation_phases'])}

## Current Metadata Coverage

### Field Coverage Analysis
"""
    
    # Sort fields by coverage percentage
    sorted_coverage = sorted(
        analysis['field_coverage'].items(),
        key=lambda x: x[1]['coverage_percentage'],
        reverse=True
    )
    
    for field, stats in sorted_coverage[:15]:  # Top 15 fields
        markdown_content += f"- **{field}**: {stats['coverage_percentage']:.1f}% coverage ({stats['present']} products)\n"
    
    markdown_content += "\n### Enhancement Opportunities\n\n"
    
    for opportunity in analysis['enhancement_opportunities'][:10]:  # Top 10 opportunities
        markdown_content += f"- **{opportunity['field']}** ({opportunity['type']}): {opportunity['recommendation']}\n"
    
    markdown_content += "\n## Proposed New Metadata Fields\n\n"
    
    for field in analysis['missing_fields']:
        markdown_content += f"### {field['field']}\n\n"
        markdown_content += f"- **Description**: {field['description']}\n"
        markdown_content += f"- **Type**: {field['type']}\n"
        markdown_content += f"- **Priority**: {field['priority']}\n"
        markdown_content += f"- **Examples**: {', '.join(str(ex) for ex in field['examples'])}\n\n"
    
    markdown_content += "## Implementation Plan\n\n"
    
    for phase in plan['implementation_phases']:
        markdown_content += f"### Phase {phase['phase']}: {phase['name']}\n\n"
        markdown_content += f"- **Duration**: {phase['duration']}\n"
        markdown_content += f"- **Description**: {phase['description']}\n\n"
        
        markdown_content += "**Tasks**:\n"
        for task in phase['tasks']:
            markdown_content += f"- {task}\n"
        
        markdown_content += "\n**Deliverables**:\n"
        for deliverable in phase['deliverables']:
            markdown_content += f"- {deliverable}\n"
        
        markdown_content += "\n"
    
    markdown_content += "## Automation Opportunities\n\n"
    
    for automation in plan['automation_opportunities']:
        markdown_content += f"### {automation['task']}\n\n"
        markdown_content += f"- **Description**: {automation['description']}\n"
        markdown_content += f"- **Complexity**: {automation['complexity']}\n"
        markdown_content += f"- **Impact**: {automation['impact']}\n\n"
    
    markdown_content += "## Quality Metrics\n\n"
    
    for metric, description in plan['quality_metrics'].items():
        markdown_content += f"- **{metric.replace('_', ' ').title()}**: {description}\n"
    
    markdown_content += "\n## Standardization Needs\n\n"
    
    for need in analysis['standardization_needs'][:10]:  # Top 10 standardization needs
        markdown_content += f"- **{need['field']}** ({need['issue']}): {need['recommendation']}\n"
    
    with open('metadata_enhancement_summary.md', 'w', encoding='utf-8') as f:
        f.write(markdown_content)

def main():
    """Main execution function."""
    try:
        print("🔍 Analyzing current metadata structure...\n")
        
        # Analyze current metadata
        analysis = analyze_current_metadata()
        
        print(f"\n📊 Metadata Analysis Results:")
        print(f"   Current fields: {len(analysis['current_structure'])}")
        print(f"   Enhancement opportunities: {len(analysis['enhancement_opportunities'])}")
        print(f"   Missing fields identified: {len(analysis['missing_fields'])}")
        print(f"   Standardization needs: {len(analysis['standardization_needs'])}")
        
        # Generate enhancement plan
        print("\n🎯 Generating enhancement plan...")
        plan = generate_enhancement_plan(analysis)
        
        # Create enhanced schema
        print("\n📋 Creating enhanced schema...")
        schema = create_enhanced_schema()
        
        # Save reports
        print("\n💾 Saving metadata analysis and enhancement plan...")
        save_metadata_analysis(analysis, plan, schema)
        
        print("\n🎉 Metadata enhancement analysis completed!")
        print("   📋 Detailed report: metadata_enhancement_analysis.json")
        print("   📝 Summary report: metadata_enhancement_summary.md")
        print(f"   🔧 Implementation phases: {len(plan['implementation_phases'])}")
        print(f"   🤖 Automation opportunities: {len(plan['automation_opportunities'])}")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        raise

if __name__ == "__main__":
    main()