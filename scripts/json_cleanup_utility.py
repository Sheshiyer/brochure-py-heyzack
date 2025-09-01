#!/usr/bin/env python3
"""
JSON Cleanup Utility

This script identifies and removes redundant, outdated, or unnecessary JSON files
from the data directory while preserving essential data files.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional
import logging
from pathlib import Path
import hashlib
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JSONCleanupUtility:
    """Utility for cleaning up redundant JSON files."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.archive_dir = self.data_dir / "archived"
        
        # Essential files that should never be deleted
        self.essential_files = {
            'products_hierarchical_enhanced.json',
            'products.json',
            'SMART HOME FOLLOWING PROJECT - All Products.csv'
        }
        
        # Files that are safe to remove (known redundant files)
        self.safe_to_remove = {
            'products_hierarchical.json',
            'products_hierarchical_enhanced_v2.json',
            'products_hierarchical_fixed.json',
            'sample_enhancement.json',
            'products_enhanced.json',
            'products_temp.json',
            'products_backup.json',
            'test_products.json',
            'products_old.json'
        }
        
        # Ensure archive directory exists
        self.archive_dir.mkdir(exist_ok=True)
    
    def scan_json_files(self) -> Dict[str, Dict[str, Any]]:
        """Scan all JSON files in the data directory."""
        json_files = {}
        
        for file_path in self.data_dir.glob("*.json"):
            try:
                file_info = {
                    'path': file_path,
                    'size': file_path.stat().st_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime),
                    'created': datetime.fromtimestamp(file_path.stat().st_ctime),
                    'is_essential': file_path.name in self.essential_files,
                    'is_safe_to_remove': file_path.name in self.safe_to_remove,
                    'content_hash': None,
                    'content_summary': None
                }
                
                # Try to analyze content
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        file_info['content_hash'] = hashlib.md5(content.encode()).hexdigest()
                        
                        # Parse JSON to get summary
                        data = json.loads(content)
                        file_info['content_summary'] = self._analyze_json_content(data)
                        
                except Exception as e:
                    logger.warning(f"Could not analyze content of {file_path.name}: {e}")
                    file_info['content_summary'] = {'error': str(e)}
                
                json_files[file_path.name] = file_info
                
            except Exception as e:
                logger.error(f"Error scanning {file_path}: {e}")
        
        logger.info(f"Scanned {len(json_files)} JSON files")
        return json_files
    
    def _analyze_json_content(self, data: Any) -> Dict[str, Any]:
        """Analyze JSON content to understand its structure and purpose."""
        summary = {
            'type': 'unknown',
            'size_estimate': 0,
            'key_fields': [],
            'product_count': 0,
            'categories_count': 0
        }
        
        try:
            if isinstance(data, dict):
                summary['type'] = 'object'
                summary['key_fields'] = list(data.keys())[:10]  # First 10 keys
                
                # Check if it's a hierarchical product structure
                if 'categories' in data:
                    summary['type'] = 'hierarchical_products'
                    categories = data.get('categories', {})
                    summary['categories_count'] = len(categories)
                    
                    # Count products
                    product_count = 0
                    for category_data in categories.values():
                        if isinstance(category_data, dict) and 'products' in category_data:
                            product_count += len(category_data.get('products', []))
                    summary['product_count'] = product_count
                
                # Check if it's metadata
                elif 'metadata' in data:
                    summary['type'] = 'metadata_structure'
                    if 'products' in data:
                        summary['product_count'] = len(data.get('products', []))
                
            elif isinstance(data, list):
                summary['type'] = 'array'
                summary['size_estimate'] = len(data)
                
                # Check if it's a product list
                if data and isinstance(data[0], dict):
                    first_item = data[0]
                    if any(key in first_item for key in ['name', 'product', 'model', 'category']):
                        summary['type'] = 'product_list'
                        summary['product_count'] = len(data)
                        summary['key_fields'] = list(first_item.keys())[:10]
            
        except Exception as e:
            summary['error'] = str(e)
        
        return summary
    
    def identify_duplicates(self, json_files: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """Identify duplicate files based on content hash."""
        hash_groups = {}
        
        # Group files by content hash
        for filename, file_info in json_files.items():
            content_hash = file_info.get('content_hash')
            if content_hash:
                if content_hash not in hash_groups:
                    hash_groups[content_hash] = []
                hash_groups[content_hash].append((filename, file_info))
        
        # Find groups with duplicates
        duplicates = []
        for content_hash, files in hash_groups.items():
            if len(files) > 1:
                # Sort by modification time (keep newest)
                files.sort(key=lambda x: x[1]['modified'], reverse=True)
                
                duplicate_group = {
                    'content_hash': content_hash,
                    'files': files,
                    'keep_file': files[0][0],  # Keep the newest
                    'remove_files': [f[0] for f in files[1:]]  # Remove the rest
                }
                duplicates.append(duplicate_group)
        
        logger.info(f"Found {len(duplicates)} duplicate groups")
        return duplicates
    
    def identify_outdated_files(self, json_files: Dict[str, Dict], days_threshold: int = 30) -> List[str]:
        """Identify files that haven't been modified recently and might be outdated."""
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        outdated_files = []
        
        for filename, file_info in json_files.items():
            if (file_info['modified'] < cutoff_date and 
                not file_info['is_essential'] and
                file_info.get('content_summary', {}).get('type') != 'hierarchical_products'):
                outdated_files.append(filename)
        
        logger.info(f"Found {len(outdated_files)} potentially outdated files")
        return outdated_files
    
    def archive_file(self, filename: str) -> bool:
        """Archive a file instead of deleting it."""
        try:
            source_path = self.data_dir / filename
            if not source_path.exists():
                return True
            
            # Create timestamped archive name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"{source_path.stem}_{timestamp}.json"
            archive_path = self.archive_dir / archive_name
            
            # Move file to archive
            shutil.move(str(source_path), str(archive_path))
            logger.info(f"Archived {filename} to {archive_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error archiving {filename}: {e}")
            return False
    
    def remove_file(self, filename: str) -> bool:
        """Remove a file permanently."""
        try:
            file_path = self.data_dir / filename
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Removed {filename}")
            return True
        except Exception as e:
            logger.error(f"Error removing {filename}: {e}")
            return False
    
    def generate_cleanup_report(self, json_files: Dict, duplicates: List, outdated: List) -> str:
        """Generate a detailed cleanup report."""
        report_lines = [
            "# JSON Cleanup Report",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- **Total JSON files scanned**: {len(json_files)}",
            f"- **Essential files (protected)**: {len([f for f in json_files.values() if f['is_essential']])}",
            f"- **Duplicate groups found**: {len(duplicates)}",
            f"- **Outdated files identified**: {len(outdated)}",
            f"- **Safe to remove files**: {len([f for f in json_files.values() if f['is_safe_to_remove']])}",
            ""
        ]
        
        # Essential files section
        essential_files = [name for name, info in json_files.items() if info['is_essential']]
        if essential_files:
            report_lines.extend([
                "## Essential Files (Protected)",
                "These files are critical and will not be modified:",
                ""
            ])
            for filename in essential_files:
                file_info = json_files[filename]
                size_mb = file_info['size'] / (1024 * 1024)
                report_lines.append(f"- **{filename}** ({size_mb:.2f} MB, modified: {file_info['modified'].strftime('%Y-%m-%d')})")
            report_lines.append("")
        
        # Duplicates section
        if duplicates:
            report_lines.extend([
                "## Duplicate Files",
                "Files with identical content:",
                ""
            ])
            for i, dup_group in enumerate(duplicates, 1):
                report_lines.append(f"### Duplicate Group {i}")
                report_lines.append(f"- **Keep**: {dup_group['keep_file']}")
                report_lines.append(f"- **Remove**: {', '.join(dup_group['remove_files'])}")
                report_lines.append("")
        
        # Outdated files section
        if outdated:
            report_lines.extend([
                "## Outdated Files",
                "Files that haven't been modified recently:",
                ""
            ])
            for filename in outdated:
                file_info = json_files[filename]
                days_old = (datetime.now() - file_info['modified']).days
                report_lines.append(f"- **{filename}** (last modified {days_old} days ago)")
            report_lines.append("")
        
        # Safe to remove section
        safe_files = [name for name, info in json_files.items() if info['is_safe_to_remove']]
        if safe_files:
            report_lines.extend([
                "## Known Redundant Files",
                "Files identified as safe to remove:",
                ""
            ])
            for filename in safe_files:
                report_lines.append(f"- **{filename}**")
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def cleanup(self, dry_run: bool = False, archive_instead_of_delete: bool = True) -> Dict[str, Any]:
        """Perform the cleanup operation."""
        logger.info(f"Starting JSON cleanup (dry_run={dry_run}, archive={archive_instead_of_delete})")
        
        cleanup_stats = {
            'files_scanned': 0,
            'files_removed': 0,
            'files_archived': 0,
            'duplicates_resolved': 0,
            'space_freed': 0,
            'errors': []
        }
        
        try:
            # Scan all JSON files
            json_files = self.scan_json_files()
            cleanup_stats['files_scanned'] = len(json_files)
            
            # Identify issues
            duplicates = self.identify_duplicates(json_files)
            outdated = self.identify_outdated_files(json_files)
            
            # Generate report
            report = self.generate_cleanup_report(json_files, duplicates, outdated)
            report_path = self.data_dir.parent / "reports" / "json_cleanup_report.md"
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Cleanup report saved to {report_path}")
            
            if dry_run:
                logger.info("Dry run mode - no files will be modified")
                return cleanup_stats
            
            # Remove known safe files
            for filename, file_info in json_files.items():
                if file_info['is_safe_to_remove'] and not file_info['is_essential']:
                    cleanup_stats['space_freed'] += file_info['size']
                    
                    if archive_instead_of_delete:
                        if self.archive_file(filename):
                            cleanup_stats['files_archived'] += 1
                        else:
                            cleanup_stats['errors'].append(f"Failed to archive {filename}")
                    else:
                        if self.remove_file(filename):
                            cleanup_stats['files_removed'] += 1
                        else:
                            cleanup_stats['errors'].append(f"Failed to remove {filename}")
            
            # Handle duplicates
            for dup_group in duplicates:
                for filename in dup_group['remove_files']:
                    if filename not in self.essential_files:
                        file_info = json_files.get(filename, {})
                        cleanup_stats['space_freed'] += file_info.get('size', 0)
                        
                        if archive_instead_of_delete:
                            if self.archive_file(filename):
                                cleanup_stats['files_archived'] += 1
                                cleanup_stats['duplicates_resolved'] += 1
                            else:
                                cleanup_stats['errors'].append(f"Failed to archive duplicate {filename}")
                        else:
                            if self.remove_file(filename):
                                cleanup_stats['files_removed'] += 1
                                cleanup_stats['duplicates_resolved'] += 1
                            else:
                                cleanup_stats['errors'].append(f"Failed to remove duplicate {filename}")
            
            # Clean up old archived files (keep only last 30 days)
            self._cleanup_old_archives(30)
            
            logger.info(f"Cleanup completed: {cleanup_stats['files_removed']} removed, {cleanup_stats['files_archived']} archived")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            cleanup_stats['errors'].append(str(e))
            return cleanup_stats
    
    def _cleanup_old_archives(self, keep_days: int) -> None:
        """Remove old archived files."""
        try:
            cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 3600)
            
            for archive_file in self.archive_dir.glob("*.json"):
                if archive_file.stat().st_mtime < cutoff_time:
                    archive_file.unlink()
                    logger.info(f"Removed old archive: {archive_file.name}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up old archives: {e}")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up redundant JSON files")
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--delete', action='store_true', help='Delete files instead of archiving them')
    parser.add_argument('--data-dir', default='data', help='Data directory path')
    
    args = parser.parse_args()
    
    cleanup_utility = JSONCleanupUtility(args.data_dir)
    
    # Perform cleanup
    stats = cleanup_utility.cleanup(
        dry_run=args.dry_run,
        archive_instead_of_delete=not args.delete
    )
    
    # Print results
    print(f"\n📊 Cleanup Results:")
    print(f"   Files scanned: {stats['files_scanned']}")
    print(f"   Files removed: {stats['files_removed']}")
    print(f"   Files archived: {stats['files_archived']}")
    print(f"   Duplicates resolved: {stats['duplicates_resolved']}")
    print(f"   Space freed: {stats['space_freed'] / (1024*1024):.2f} MB")
    
    if stats['errors']:
        print(f"\n⚠️  Errors encountered:")
        for error in stats['errors']:
            print(f"   - {error}")
    
    if stats['files_removed'] > 0 or stats['files_archived'] > 0:
        print("\n✅ JSON cleanup completed successfully")
    else:
        print("\n✨ No cleanup needed - all files are current")

if __name__ == "__main__":
    main()