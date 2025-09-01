#!/usr/bin/env python3
"""
Data Validator

This script validates product data integrity across JSON files, checks for
inconsistencies, missing fields, and data quality issues.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Set, Any, Optional, Tuple
import logging
from pathlib import Path
import re
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    level: ValidationLevel
    category: str
    message: str
    file_path: str
    location: str = ""
    suggestion: str = ""

class DataValidator:
    """Validates product data integrity and quality."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.issues: List[ValidationIssue] = []
        
        # Required fields for different data types
        self.required_product_fields = {
            'name', 'category', 'model'
        }
        
        self.recommended_product_fields = {
            'description', 'specifications', 'price', 'availability'
        }
        
        # Valid categories (can be extended)
        self.valid_categories = {
            'Smart Locks', 'Smart Cameras', 'Smart Doorbells', 
            'Smart Sensors', 'Smart Lighting', 'Smart Thermostats',
            'Smart Switches', 'Smart Plugs', 'Smart Speakers',
            'Smart Displays', 'Smart Security', 'Smart Home Hubs'
        }
        
        # Data patterns
        self.model_pattern = re.compile(r'^[A-Z0-9-_]+$', re.IGNORECASE)
        self.price_pattern = re.compile(r'^\$?\d+(\.\d{2})?$')
    
    def add_issue(self, level: ValidationLevel, category: str, message: str, 
                  file_path: str, location: str = "", suggestion: str = ""):
        """Add a validation issue."""
        issue = ValidationIssue(
            level=level,
            category=category,
            message=message,
            file_path=file_path,
            location=location,
            suggestion=suggestion
        )
        self.issues.append(issue)
        
        # Log the issue
        log_message = f"{file_path}: {message}"
        if location:
            log_message += f" (at {location})"
            
        if level == ValidationLevel.ERROR:
            logger.error(log_message)
        elif level == ValidationLevel.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def validate_json_structure(self, file_path: Path) -> bool:
        """Validate basic JSON structure and syntax."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except json.JSONDecodeError as e:
            self.add_issue(
                ValidationLevel.ERROR,
                "JSON Syntax",
                f"Invalid JSON syntax: {e}",
                str(file_path),
                f"Line {e.lineno}, Column {e.colno}",
                "Fix JSON syntax errors"
            )
            return False
        except Exception as e:
            self.add_issue(
                ValidationLevel.ERROR,
                "File Access",
                f"Cannot read file: {e}",
                str(file_path),
                suggestion="Check file permissions and encoding"
            )
            return False
    
    def validate_product_fields(self, product: Dict[str, Any], 
                               file_path: str, product_index: int) -> None:
        """Validate individual product fields."""
        location = f"Product {product_index}"
        
        # Check required fields
        for field in self.required_product_fields:
            if field not in product or not product[field]:
                self.add_issue(
                    ValidationLevel.ERROR,
                    "Missing Required Field",
                    f"Missing required field '{field}'",
                    file_path,
                    location,
                    f"Add '{field}' field to product"
                )
        
        # Check recommended fields
        for field in self.recommended_product_fields:
            if field not in product or not product[field]:
                self.add_issue(
                    ValidationLevel.WARNING,
                    "Missing Recommended Field",
                    f"Missing recommended field '{field}'",
                    file_path,
                    location,
                    f"Consider adding '{field}' field for better data quality"
                )
        
        # Validate specific field formats
        if 'name' in product:
            name = product['name']
            if not isinstance(name, str) or len(name.strip()) == 0:
                self.add_issue(
                    ValidationLevel.ERROR,
                    "Invalid Field Value",
                    "Product name must be a non-empty string",
                    file_path,
                    location
                )
            elif len(name) > 200:
                self.add_issue(
                    ValidationLevel.WARNING,
                    "Field Length",
                    f"Product name is very long ({len(name)} characters)",
                    file_path,
                    location,
                    "Consider shortening the product name"
                )
        
        # Validate category
        if 'category' in product:
            category = product['category']
            if category not in self.valid_categories:
                self.add_issue(
                    ValidationLevel.WARNING,
                    "Unknown Category",
                    f"Unknown category '{category}'",
                    file_path,
                    location,
                    f"Use one of: {', '.join(sorted(self.valid_categories))}"
                )
        
        # Validate model format
        if 'model' in product:
            model = product['model']
            if not self.model_pattern.match(str(model)):
                self.add_issue(
                    ValidationLevel.WARNING,
                    "Model Format",
                    f"Model '{model}' doesn't follow standard format",
                    file_path,
                    location,
                    "Use alphanumeric characters, hyphens, and underscores only"
                )
        
        # Validate price format
        if 'price' in product and product['price']:
            price = str(product['price'])
            if not self.price_pattern.match(price):
                self.add_issue(
                    ValidationLevel.WARNING,
                    "Price Format",
                    f"Price '{price}' doesn't follow standard format",
                    file_path,
                    location,
                    "Use format like '$99.99' or '99.99'"
                )
        
        # Validate specifications
        if 'specifications' in product:
            specs = product['specifications']
            if isinstance(specs, dict):
                if len(specs) == 0:
                    self.add_issue(
                        ValidationLevel.WARNING,
                        "Empty Specifications",
                        "Specifications object is empty",
                        file_path,
                        location,
                        "Add technical specifications"
                    )
            elif isinstance(specs, str):
                if len(specs.strip()) == 0:
                    self.add_issue(
                        ValidationLevel.WARNING,
                        "Empty Specifications",
                        "Specifications string is empty",
                        file_path,
                        location,
                        "Add technical specifications"
                    )
    
    def validate_hierarchical_structure(self, data: Dict[str, Any], file_path: str) -> None:
        """Validate hierarchical product structure."""
        if 'categories' not in data:
            self.add_issue(
                ValidationLevel.ERROR,
                "Structure",
                "Missing 'categories' key in hierarchical structure",
                file_path,
                suggestion="Add 'categories' object to root level"
            )
            return
        
        categories = data['categories']
        if not isinstance(categories, dict):
            self.add_issue(
                ValidationLevel.ERROR,
                "Structure",
                "'categories' must be an object",
                file_path
            )
            return
        
        if len(categories) == 0:
            self.add_issue(
                ValidationLevel.WARNING,
                "Empty Structure",
                "No categories found in hierarchical structure",
                file_path,
                suggestion="Add product categories"
            )
            return
        
        # Validate each category
        for category_name, category_data in categories.items():
            location = f"Category '{category_name}'"
            
            if not isinstance(category_data, dict):
                self.add_issue(
                    ValidationLevel.ERROR,
                    "Structure",
                    f"Category data must be an object",
                    file_path,
                    location
                )
                continue
            
            # Check for products in category
            if 'products' not in category_data:
                self.add_issue(
                    ValidationLevel.WARNING,
                    "Missing Products",
                    f"Category has no 'products' key",
                    file_path,
                    location,
                    "Add 'products' array to category"
                )
                continue
            
            products = category_data['products']
            if not isinstance(products, list):
                self.add_issue(
                    ValidationLevel.ERROR,
                    "Structure",
                    "'products' must be an array",
                    file_path,
                    location
                )
                continue
            
            if len(products) == 0:
                self.add_issue(
                    ValidationLevel.INFO,
                    "Empty Category",
                    f"Category has no products",
                    file_path,
                    location
                )
                continue
            
            # Validate each product in category
            for i, product in enumerate(products):
                if not isinstance(product, dict):
                    self.add_issue(
                        ValidationLevel.ERROR,
                        "Structure",
                        f"Product {i} must be an object",
                        file_path,
                        f"{location}, Product {i}"
                    )
                    continue
                
                self.validate_product_fields(product, file_path, i)
    
    def validate_product_list(self, data: List[Dict[str, Any]], file_path: str) -> None:
        """Validate flat product list structure."""
        if len(data) == 0:
            self.add_issue(
                ValidationLevel.WARNING,
                "Empty Data",
                "Product list is empty",
                file_path,
                suggestion="Add products to the list"
            )
            return
        
        for i, product in enumerate(data):
            if not isinstance(product, dict):
                self.add_issue(
                    ValidationLevel.ERROR,
                    "Structure",
                    f"Product {i} must be an object",
                    file_path,
                    f"Index {i}"
                )
                continue
            
            self.validate_product_fields(product, file_path, i)
    
    def check_data_consistency(self, files_data: Dict[str, Any]) -> None:
        """Check consistency across multiple data files."""
        # Extract all products from different files
        all_products = {}
        
        for file_path, data in files_data.items():
            products = []
            
            if isinstance(data, list):
                products = data
            elif isinstance(data, dict) and 'categories' in data:
                for category_data in data['categories'].values():
                    if isinstance(category_data, dict) and 'products' in category_data:
                        products.extend(category_data['products'])
            
            for product in products:
                if isinstance(product, dict) and 'model' in product:
                    model = product['model']
                    if model in all_products:
                        # Check for inconsistencies
                        existing = all_products[model]
                        current = product
                        
                        # Compare key fields
                        for field in ['name', 'category', 'price']:
                            if (field in existing and field in current and 
                                existing[field] != current[field]):
                                self.add_issue(
                                    ValidationLevel.WARNING,
                                    "Data Inconsistency",
                                    f"Model '{model}' has different '{field}' values across files",
                                    file_path,
                                    f"Model {model}",
                                    "Ensure consistent data across all files"
                                )
                    else:
                        all_products[model] = product
    
    def validate_file(self, file_path: Path) -> bool:
        """Validate a single JSON file."""
        logger.info(f"Validating {file_path.name}")
        
        # Check JSON syntax first
        if not self.validate_json_structure(file_path):
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Determine data structure and validate accordingly
            if isinstance(data, list):
                self.validate_product_list(data, str(file_path))
            elif isinstance(data, dict):
                if 'categories' in data:
                    self.validate_hierarchical_structure(data, str(file_path))
                else:
                    # Single product or metadata structure
                    if any(field in data for field in self.required_product_fields):
                        self.validate_product_fields(data, str(file_path), 0)
            
            return True
            
        except Exception as e:
            self.add_issue(
                ValidationLevel.ERROR,
                "Validation Error",
                f"Error during validation: {e}",
                str(file_path)
            )
            return False
    
    def validate_all(self) -> Dict[str, Any]:
        """Validate all JSON files in the data directory."""
        logger.info(f"Starting validation of data directory: {self.data_dir}")
        
        validation_stats = {
            'files_validated': 0,
            'files_with_errors': 0,
            'files_with_warnings': 0,
            'total_issues': 0,
            'error_count': 0,
            'warning_count': 0,
            'info_count': 0
        }
        
        # Find all JSON files
        json_files = list(self.data_dir.glob("*.json"))
        
        if not json_files:
            logger.warning("No JSON files found in data directory")
            return validation_stats
        
        # Validate each file
        files_data = {}
        for file_path in json_files:
            validation_stats['files_validated'] += 1
            
            initial_issue_count = len(self.issues)
            success = self.validate_file(file_path)
            
            if success:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        files_data[str(file_path)] = json.load(f)
                except:
                    pass
            
            # Count issues for this file
            file_issues = self.issues[initial_issue_count:]
            has_errors = any(issue.level == ValidationLevel.ERROR for issue in file_issues)
            has_warnings = any(issue.level == ValidationLevel.WARNING for issue in file_issues)
            
            if has_errors:
                validation_stats['files_with_errors'] += 1
            if has_warnings:
                validation_stats['files_with_warnings'] += 1
        
        # Check cross-file consistency
        if len(files_data) > 1:
            self.check_data_consistency(files_data)
        
        # Count issues by level
        for issue in self.issues:
            validation_stats['total_issues'] += 1
            if issue.level == ValidationLevel.ERROR:
                validation_stats['error_count'] += 1
            elif issue.level == ValidationLevel.WARNING:
                validation_stats['warning_count'] += 1
            else:
                validation_stats['info_count'] += 1
        
        logger.info(f"Validation completed: {validation_stats['total_issues']} issues found")
        return validation_stats
    
    def generate_report(self, stats: Dict[str, Any]) -> str:
        """Generate a detailed validation report."""
        report_lines = [
            "# Data Validation Report",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- **Files validated**: {stats['files_validated']}",
            f"- **Files with errors**: {stats['files_with_errors']}",
            f"- **Files with warnings**: {stats['files_with_warnings']}",
            f"- **Total issues**: {stats['total_issues']}",
            f"  - Errors: {stats['error_count']}",
            f"  - Warnings: {stats['warning_count']}",
            f"  - Info: {stats['info_count']}",
            ""
        ]
        
        if not self.issues:
            report_lines.extend([
                "## ✅ Validation Results",
                "All data files passed validation with no issues found!",
                ""
            ])
            return "\n".join(report_lines)
        
        # Group issues by category
        issues_by_category = {}
        for issue in self.issues:
            category = issue.category
            if category not in issues_by_category:
                issues_by_category[category] = []
            issues_by_category[category].append(issue)
        
        # Add issues by category
        for category, category_issues in sorted(issues_by_category.items()):
            report_lines.extend([
                f"## {category} Issues",
                ""
            ])
            
            # Group by file
            issues_by_file = {}
            for issue in category_issues:
                file_name = Path(issue.file_path).name
                if file_name not in issues_by_file:
                    issues_by_file[file_name] = []
                issues_by_file[file_name].append(issue)
            
            for file_name, file_issues in sorted(issues_by_file.items()):
                report_lines.append(f"### {file_name}")
                report_lines.append("")
                
                for issue in file_issues:
                    level_emoji = {
                        ValidationLevel.ERROR: "❌",
                        ValidationLevel.WARNING: "⚠️",
                        ValidationLevel.INFO: "ℹ️"
                    }
                    
                    location_str = f" ({issue.location})" if issue.location else ""
                    suggestion_str = f"\n  - **Suggestion**: {issue.suggestion}" if issue.suggestion else ""
                    
                    report_lines.append(
                        f"- {level_emoji[issue.level]} **{issue.level.value.upper()}**{location_str}: {issue.message}{suggestion_str}"
                    )
                
                report_lines.append("")
        
        return "\n".join(report_lines)
    
    def get_issues_by_level(self, level: ValidationLevel) -> List[ValidationIssue]:
        """Get all issues of a specific level."""
        return [issue for issue in self.issues if issue.level == level]

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate product data integrity")
    parser.add_argument('--data-dir', default='data', help='Data directory path')
    parser.add_argument('--report-file', help='Output report file path')
    parser.add_argument('--fail-on-errors', action='store_true', help='Exit with error code if validation errors found')
    
    args = parser.parse_args()
    
    validator = DataValidator(args.data_dir)
    
    # Run validation
    stats = validator.validate_all()
    
    # Generate report
    report = validator.generate_report(stats)
    
    # Save report
    if args.report_file:
        report_path = Path(args.report_file)
    else:
        report_path = Path("reports") / "data_validation_report.md"
    
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📊 Validation Results:")
    print(f"   Files validated: {stats['files_validated']}")
    print(f"   Total issues: {stats['total_issues']}")
    print(f"   Errors: {stats['error_count']}")
    print(f"   Warnings: {stats['warning_count']}")
    print(f"   Info: {stats['info_count']}")
    print(f"\n📄 Report saved to: {report_path}")
    
    if stats['error_count'] == 0 and stats['warning_count'] == 0:
        print("\n✅ All data files passed validation!")
    elif stats['error_count'] == 0:
        print("\n⚠️  Validation completed with warnings")
    else:
        print("\n❌ Validation failed with errors")
        if args.fail_on_errors:
            sys.exit(1)

if __name__ == "__main__":
    main()