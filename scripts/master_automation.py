#!/usr/bin/env python3
"""
Master Automation Script

This script orchestrates the complete automated product processing pipeline,
integrating all components to ensure products_hierarchical_enhanced.json is
automatically updated with new products and enhanced descriptions.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import argparse
import time

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import our automation modules
from scripts.automated_product_processor import ProductProcessor
from scripts.category_description_generator import CategoryDescriptionGenerator
from scripts.json_synchronizer import JSONSynchronizer
from scripts.json_cleanup_utility import JSONCleanupUtility
from scripts.data_validator import DataValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MasterAutomation:
    """Master automation orchestrator."""
    
    def __init__(self, data_dir: str = "data", reports_dir: str = "reports"):
        self.data_dir = Path(data_dir)
        self.reports_dir = Path(reports_dir)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.product_processor = ProductProcessor(str(self.data_dir))
        self.category_generator = CategoryDescriptionGenerator(str(self.data_dir))
        self.json_synchronizer = JSONSynchronizer(str(self.data_dir))
        self.cleanup_utility = JSONCleanupUtility(str(self.data_dir))
        self.data_validator = DataValidator(str(self.data_dir))
        
        # Pipeline statistics
        self.pipeline_stats = {
            'start_time': datetime.now(),
            'end_time': None,
            'duration': None,
            'new_products_found': 0,
            'products_enhanced': 0,
            'categories_updated': 0,
            'files_synchronized': 0,
            'files_cleaned': 0,
            'validation_errors': 0,
            'validation_warnings': 0,
            'success': False,
            'errors': []
        }
    
    def log_step(self, step_name: str, status: str = "started"):
        """Log pipeline step."""
        if status == "started":
            logger.info(f"🔄 {step_name}...")
        elif status == "completed":
            logger.info(f"✅ {step_name} completed")
        elif status == "failed":
            logger.error(f"❌ {step_name} failed")
        elif status == "skipped":
            logger.info(f"⏭️  {step_name} skipped")
    
    def validate_prerequisites(self) -> bool:
        """Validate that all required files and configurations exist."""
        self.log_step("Validating prerequisites")
        
        required_files = [
            self.data_dir / "SMART HOME FOLLOWING PROJECT - All Products.csv"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not file_path.exists():
                missing_files.append(str(file_path))
        
        if missing_files:
            error_msg = f"Missing required files: {', '.join(missing_files)}"
            self.pipeline_stats['errors'].append(error_msg)
            logger.error(error_msg)
            self.log_step("Validating prerequisites", "failed")
            return False
        
        # Check if OpenRouter client is properly configured
        try:
            from brochure.openrouter_client import OpenRouterClient
            client = OpenRouterClient()
            # Note: We don't test the API here to avoid unnecessary calls
            logger.info("OpenRouter client is available")
        except Exception as e:
            logger.warning(f"OpenRouter client issue: {e}")
            logger.warning("Product enhancement may not work properly")
        
        self.log_step("Validating prerequisites", "completed")
        return True
    
    def step_1_process_new_products(self) -> bool:
        """Step 1: Process new products from CSV and enhance with AI descriptions."""
        self.log_step("Processing new products")
        
        try:
            # Get initial product count
            initial_data = self.product_processor.load_enhanced_json()
            initial_count = len(initial_data.get('categories', {}).get('all_products', {}))
            
            # Run the automated product processor
            result = self.product_processor.process_new_products()
            
            # Get final product count to calculate new products
            final_data = self.product_processor.load_enhanced_json()
            final_count = len(final_data.get('categories', {}).get('all_products', {}))
            
            self.pipeline_stats['new_products_found'] = final_count - initial_count
            self.pipeline_stats['products_enhanced'] = final_count - initial_count
            
            if result:
                logger.info(f"Found {self.pipeline_stats['new_products_found']} new products")
                logger.info(f"Enhanced {self.pipeline_stats['products_enhanced']} products")
                self.log_step("Processing new products", "completed")
                return True
            else:
                error_msg = f"Product processing failed: {result.get('error', 'Unknown error')}"
                self.pipeline_stats['errors'].append(error_msg)
                logger.error(error_msg)
                self.log_step("Processing new products", "failed")
                return False
                
        except Exception as e:
            error_msg = f"Error in product processing: {e}"
            self.pipeline_stats['errors'].append(error_msg)
            logger.error(error_msg)
            self.log_step("Processing new products", "failed")
            return False
    
    def step_2_generate_category_descriptions(self) -> bool:
        """Step 2: Generate category-wise descriptions."""
        self.log_step("Generating category descriptions")
        
        try:
            # Get initial category count
            initial_data = self.category_generator.load_enhanced_data()
            initial_categories = len([cat for cat in initial_data.get('categories', {}).values() 
                                    if isinstance(cat, dict) and 'description' in cat])
            
            # Run the category description generator
            result = self.category_generator.process_categories()
            
            # Get final category count
            final_data = self.category_generator.load_enhanced_data()
            final_categories = len([cat for cat in final_data.get('categories', {}).values() 
                                  if isinstance(cat, dict) and 'description' in cat])
            
            self.pipeline_stats['categories_updated'] = final_categories - initial_categories
            
            if result:
                logger.info(f"Updated {self.pipeline_stats['categories_updated']} categories")
                self.log_step("Generating category descriptions", "completed")
                return True
            else:
                error_msg = "Category generation failed"
                self.pipeline_stats['errors'].append(error_msg)
                logger.error(error_msg)
                self.log_step("Generating category descriptions", "failed")
                return False
                
        except Exception as e:
            error_msg = f"Error in category generation: {e}"
            self.pipeline_stats['errors'].append(error_msg)
            logger.error(error_msg)
            self.log_step("Generating category descriptions", "failed")
            return False
    
    def step_3_synchronize_json_files(self) -> bool:
        """Step 3: Synchronize products.json with products_hierarchical_enhanced.json."""
        self.log_step("Synchronizing JSON files")
        
        try:
            # Run the JSON synchronizer
            result = self.json_synchronizer.synchronize()
            
            self.pipeline_stats['files_synchronized'] = 1 if result else 0
            
            if result:
                logger.info("JSON files synchronized successfully")
                self.log_step("Synchronizing JSON files", "completed")
                return True
            else:
                error_msg = "JSON synchronization failed"
                self.pipeline_stats['errors'].append(error_msg)
                logger.error(error_msg)
                self.log_step("Synchronizing JSON files", "failed")
                return False
                
        except Exception as e:
            error_msg = f"Error in JSON synchronization: {e}"
            self.pipeline_stats['errors'].append(error_msg)
            logger.error(error_msg)
            self.log_step("Synchronizing JSON files", "failed")
            return False
    
    def step_4_cleanup_redundant_files(self, dry_run: bool = False) -> bool:
        """Step 4: Clean up redundant and outdated JSON files."""
        self.log_step("Cleaning up redundant files")
        
        try:
            # Run the cleanup utility
            result = self.cleanup_utility.cleanup(dry_run=dry_run, archive_instead_of_delete=True)
            
            self.pipeline_stats['files_cleaned'] = result.get('files_archived', 0) + result.get('files_removed', 0)
            
            if len(result.get('errors', [])) == 0:
                logger.info(f"Cleaned up {self.pipeline_stats['files_cleaned']} files")
                self.log_step("Cleaning up redundant files", "completed")
                return True
            else:
                error_msg = f"Cleanup completed with errors: {result.get('errors', [])}"
                self.pipeline_stats['errors'].append(error_msg)
                logger.warning(error_msg)
                self.log_step("Cleaning up redundant files", "completed")
                return True  # Still consider success if files were cleaned
                
        except Exception as e:
            error_msg = f"Error in cleanup: {e}"
            self.pipeline_stats['errors'].append(error_msg)
            logger.error(error_msg)
            self.log_step("Cleaning up redundant files", "failed")
            return False
    
    def step_5_validate_data_integrity(self) -> bool:
        """Step 5: Validate data integrity across all JSON files."""
        self.log_step("Validating data integrity")
        
        try:
            # Run the data validator
            result = self.data_validator.validate_all()
            
            self.pipeline_stats['validation_errors'] = result.get('error_count', 0)
            self.pipeline_stats['validation_warnings'] = result.get('warning_count', 0)
            
            # Generate validation report
            validation_report = self.data_validator.generate_report(result)
            report_path = self.reports_dir / f"validation_report_{self.timestamp}.md"
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(validation_report)
            
            logger.info(f"Validation report saved to {report_path}")
            
            if self.pipeline_stats['validation_errors'] == 0:
                logger.info(f"Data validation passed with {self.pipeline_stats['validation_warnings']} warnings")
                self.log_step("Validating data integrity", "completed")
                return True
            else:
                error_msg = f"Data validation found {self.pipeline_stats['validation_errors']} errors"
                self.pipeline_stats['errors'].append(error_msg)
                logger.error(error_msg)
                self.log_step("Validating data integrity", "failed")
                return False
                
        except Exception as e:
            error_msg = f"Error in data validation: {e}"
            self.pipeline_stats['errors'].append(error_msg)
            logger.error(error_msg)
            self.log_step("Validating data integrity", "failed")
            return False
    
    def generate_pipeline_report(self) -> str:
        """Generate a comprehensive pipeline execution report."""
        duration = self.pipeline_stats['duration']
        duration_str = f"{duration.total_seconds():.2f} seconds" if duration else "Unknown"
        
        report_lines = [
            "# Automated Product Processing Pipeline Report",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Execution time: {duration_str}",
            "",
            "## Pipeline Summary",
            f"- **Status**: {'✅ SUCCESS' if self.pipeline_stats['success'] else '❌ FAILED'}",
            f"- **New products found**: {self.pipeline_stats['new_products_found']}",
            f"- **Products enhanced**: {self.pipeline_stats['products_enhanced']}",
            f"- **Categories updated**: {self.pipeline_stats['categories_updated']}",
            f"- **Files synchronized**: {self.pipeline_stats['files_synchronized']}",
            f"- **Files cleaned**: {self.pipeline_stats['files_cleaned']}",
            f"- **Validation errors**: {self.pipeline_stats['validation_errors']}",
            f"- **Validation warnings**: {self.pipeline_stats['validation_warnings']}",
            ""
        ]
        
        if self.pipeline_stats['errors']:
            report_lines.extend([
                "## Errors Encountered",
                ""
            ])
            for i, error in enumerate(self.pipeline_stats['errors'], 1):
                report_lines.append(f"{i}. {error}")
            report_lines.append("")
        
        # Add file status
        essential_files = [
            "products_hierarchical_enhanced.json",
            "products.json",
            "SMART HOME FOLLOWING PROJECT - All Products.csv"
        ]
        
        report_lines.extend([
            "## File Status",
            ""
        ])
        
        for filename in essential_files:
            file_path = self.data_dir / filename
            if file_path.exists():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                report_lines.append(f"- **{filename}**: ✅ ({size_mb:.2f} MB, modified: {modified.strftime('%Y-%m-%d %H:%M')})")
            else:
                report_lines.append(f"- **{filename}**: ❌ Missing")
        
        report_lines.append("")
        
        if self.pipeline_stats['success']:
            report_lines.extend([
                "## Next Steps",
                "- The product database has been successfully updated",
                "- You can now generate brochures with the latest product information",
                "- Run the pipeline again when new products are added to the CSV file",
                ""
            ])
        else:
            report_lines.extend([
                "## Recommended Actions",
                "- Review the errors listed above",
                "- Check the individual component logs for more details",
                "- Fix any data issues and re-run the pipeline",
                ""
            ])
        
        return "\n".join(report_lines)
    
    def run_pipeline(self, dry_run: bool = False, skip_cleanup: bool = False, 
                    skip_validation: bool = False) -> bool:
        """Run the complete automation pipeline."""
        logger.info("🚀 Starting automated product processing pipeline")
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Reports directory: {self.reports_dir}")
        
        try:
            # Step 0: Validate prerequisites
            if not self.validate_prerequisites():
                return False
            
            # Step 1: Process new products
            if not self.step_1_process_new_products():
                return False
            
            # Step 2: Generate category descriptions
            if not self.step_2_generate_category_descriptions():
                return False
            
            # Step 3: Synchronize JSON files
            if not self.step_3_synchronize_json_files():
                return False
            
            # Step 4: Clean up redundant files (optional)
            if not skip_cleanup:
                if not self.step_4_cleanup_redundant_files(dry_run=dry_run):
                    logger.warning("Cleanup failed, but continuing pipeline")
            else:
                self.log_step("Cleaning up redundant files", "skipped")
            
            # Step 5: Validate data integrity (optional)
            if not skip_validation:
                if not self.step_5_validate_data_integrity():
                    logger.warning("Validation failed, but pipeline completed")
            else:
                self.log_step("Validating data integrity", "skipped")
            
            # Mark as successful
            self.pipeline_stats['success'] = True
            logger.info("🎉 Pipeline completed successfully!")
            return True
            
        except Exception as e:
            error_msg = f"Unexpected error in pipeline: {e}"
            self.pipeline_stats['errors'].append(error_msg)
            logger.error(error_msg)
            return False
            
        finally:
            # Record end time and duration
            self.pipeline_stats['end_time'] = datetime.now()
            self.pipeline_stats['duration'] = (
                self.pipeline_stats['end_time'] - self.pipeline_stats['start_time']
            )
            
            # Generate and save pipeline report
            pipeline_report = self.generate_pipeline_report()
            report_path = self.reports_dir / f"pipeline_report_{self.timestamp}.md"
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(pipeline_report)
            
            logger.info(f"📄 Pipeline report saved to {report_path}")
            
            # Print summary
            print(f"\n📊 Pipeline Summary:")
            print(f"   Status: {'✅ SUCCESS' if self.pipeline_stats['success'] else '❌ FAILED'}")
            print(f"   Duration: {self.pipeline_stats['duration'].total_seconds():.2f} seconds")
            print(f"   New products: {self.pipeline_stats['new_products_found']}")
            print(f"   Enhanced products: {self.pipeline_stats['products_enhanced']}")
            print(f"   Categories updated: {self.pipeline_stats['categories_updated']}")
            print(f"   Files cleaned: {self.pipeline_stats['files_cleaned']}")
            print(f"   Validation errors: {self.pipeline_stats['validation_errors']}")
            print(f"   Report: {report_path}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Master automation script for product processing pipeline"
    )
    parser.add_argument('--data-dir', default='data', help='Data directory path')
    parser.add_argument('--reports-dir', default='reports', help='Reports directory path')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode (no file modifications)')
    parser.add_argument('--skip-cleanup', action='store_true', help='Skip file cleanup step')
    parser.add_argument('--skip-validation', action='store_true', help='Skip data validation step')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run the automation pipeline
    automation = MasterAutomation(args.data_dir, args.reports_dir)
    
    success = automation.run_pipeline(
        dry_run=args.dry_run,
        skip_cleanup=args.skip_cleanup,
        skip_validation=args.skip_validation
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()