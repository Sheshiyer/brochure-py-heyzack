#!/usr/bin/env python3
"""
Automated Google Sheets Polling Service

Monitors Google Sheets every 5 minutes for new data and updates the local catalog.
Provides change detection, data processing, and real-time notifications.
"""

import json
import asyncio
import logging
import hashlib
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
import csv
from google_sheets_client import GoogleSheetsClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChangeDetector:
    """Detects changes in Google Sheets data using fingerprinting."""
    
    def __init__(self, metadata_file: str = "data/polling_metadata.json"):
        self.metadata_file = metadata_file
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load polling metadata from file."""
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info("No existing metadata found, creating new tracking state")
            return {
                "last_sync": None,
                "row_count": 0,
                "data_hash": None,
                "last_row_processed": 0,
                "sheet_fingerprint": {}
            }
        except Exception as e:
            logger.error(f"Error loading metadata: {e}")
            return {}
    
    def _save_metadata(self):
        """Save polling metadata to file."""
        try:
            # Ensure directory exists
            Path(self.metadata_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def create_data_fingerprint(self, sheets_data: List[List[str]]) -> Dict[str, Any]:
        """Create a fingerprint of the sheets data for change detection."""
        if not sheets_data:
            return {"row_count": 0, "data_hash": "", "row_hashes": {}}
        
        # Calculate hash of all data
        data_str = json.dumps(sheets_data, sort_keys=True)
        data_hash = hashlib.md5(data_str.encode('utf-8')).hexdigest()
        
        # Calculate hash for each row (excluding header) for detailed change detection
        row_hashes = {}
        if len(sheets_data) > 1:  # Skip header
            for i, row in enumerate(sheets_data[1:], start=1):  # Start from 1 to account for header
                row_str = json.dumps(row, sort_keys=True)
                row_hashes[str(i)] = hashlib.md5(row_str.encode('utf-8')).hexdigest()
        
        return {
            "row_count": len(sheets_data) - 1,  # Exclude header
            "data_hash": data_hash,
            "row_hashes": row_hashes,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def detect_changes(self, current_data: List[List[str]]) -> Dict[str, Any]:
        """Detect what has changed since last check."""
        current_fingerprint = self.create_data_fingerprint(current_data)
        
        changes = {
            "has_changes": False,
            "new_rows": [],
            "modified_rows": [],
            "deleted_rows": [],
            "new_row_count": 0,
            "modified_row_count": 0,
            "deleted_row_count": 0,
            "total_rows": current_fingerprint["row_count"],
            "previous_rows": self.metadata.get("sheet_fingerprint", {}).get("row_count", 0)
        }
        
        previous_fingerprint = self.metadata.get("sheet_fingerprint", {})
        previous_row_hashes = previous_fingerprint.get("row_hashes", {})
        current_row_hashes = current_fingerprint["row_hashes"]
        
        # Check if data hash changed
        if current_fingerprint["data_hash"] != previous_fingerprint.get("data_hash"):
            changes["has_changes"] = True
            
            # Check for new rows
            previous_row_count = previous_fingerprint.get("row_count", 0)
            current_row_count = current_fingerprint["row_count"]
            
            if current_row_count > previous_row_count:
                # Extract new rows
                new_row_start = previous_row_count + 1  # +1 to account for header
                new_rows = current_data[new_row_start:]
                changes["new_rows"] = new_rows
                changes["new_row_count"] = len(new_rows)
                
                logger.info(f"Detected {len(new_rows)} new rows in Google Sheets")
            
            # Check for modified existing rows
            modified_rows = []
            for row_index, current_hash in current_row_hashes.items():
                if row_index in previous_row_hashes:
                    if current_hash != previous_row_hashes[row_index]:
                        # Row has been modified
                        row_data_index = int(row_index)  # This is 1-based row number
                        # Access the data array: header is at index 0, first data row at index 1, etc.
                        if row_data_index <= len(current_data) - 1:  # Check bounds
                            modified_rows.append({
                                "row_index": row_data_index,
                                "row_data": current_data[row_data_index],  # row_data_index is already correct for 0-based array
                                "previous_hash": previous_row_hashes[row_index],
                                "current_hash": current_hash
                            })
            
            if modified_rows:
                changes["modified_rows"] = modified_rows
                changes["modified_row_count"] = len(modified_rows)
                logger.info(f"Detected {len(modified_rows)} modified rows in Google Sheets")
            
            # Check for deleted rows (rows that existed before but not now)
            deleted_rows = []
            for row_index, previous_hash in previous_row_hashes.items():
                if row_index not in current_row_hashes:
                    # This row was deleted
                    deleted_rows.append({
                        "row_index": int(row_index),
                        "previous_hash": previous_hash
                    })
            
            if deleted_rows:
                changes["deleted_rows"] = deleted_rows
                changes["deleted_row_count"] = len(deleted_rows)
                logger.info(f"Detected {len(deleted_rows)} deleted rows in Google Sheets")
        
        # Update metadata
        self.metadata["sheet_fingerprint"] = current_fingerprint
        self.metadata["last_sync"] = datetime.now(timezone.utc).isoformat()
        self._save_metadata()
        
        return changes

class DataProcessor:
    """Processes new Google Sheets data and updates the local catalog."""
    
    def __init__(self, products_file: str = "data/products.json"):
        self.products_file = products_file
    
    def _load_products(self) -> Dict[str, Any]:
        """Load existing products data."""
        try:
            with open(self.products_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading products: {e}")
            return {"metadata": {"total_products": 0}, "products": []}
    
    def _save_products(self, products_data: Dict[str, Any]):
        """Save updated products data."""
        try:
            # Update metadata
            products_data["metadata"]["last_synchronized"] = datetime.now(timezone.utc).isoformat()
            products_data["metadata"]["total_products"] = len(products_data["products"])
            
            # Create backup
            backup_file = f"data/backups/products_pre_update_{int(time.time())}.json"
            Path(backup_file).parent.mkdir(parents=True, exist_ok=True)
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(self._load_products(), f, indent=2, ensure_ascii=False)
            
            # Save updated data
            with open(self.products_file, 'w', encoding='utf-8') as f:
                json.dump(products_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Products updated successfully. Backup saved to {backup_file}")
        except Exception as e:
            logger.error(f"Error saving products: {e}")
            raise
    
    def process_new_rows(self, new_rows: List[List[str]], headers: List[str]) -> List[Dict[str, Any]]:
        """Convert new Google Sheets rows to product objects."""
        new_products = []
        
        for row in new_rows:
            try:
                # Map row data to product structure
                product = self._create_product_from_row(row, headers)
                if product:
                    new_products.append(product)
            except Exception as e:
                logger.error(f"Error processing row {row}: {e}")
                continue
        
        return new_products
    
    def process_modified_rows(self, modified_rows: List[Dict[str, Any]], headers: List[str]) -> List[Dict[str, Any]]:
        """Convert modified Google Sheets rows to product objects."""
        modified_products = []
        
        for modified_row in modified_rows:
            try:
                # Map row data to product structure
                product = self._create_product_from_row(modified_row["row_data"], headers)
                if product:
                    # Add metadata about the modification
                    product["_modification_info"] = {
                        "row_index": modified_row["row_index"],
                        "previous_hash": modified_row["previous_hash"],
                        "current_hash": modified_row["current_hash"],
                        "modified_at": datetime.now(timezone.utc).isoformat()
                    }
                    modified_products.append(product)
            except Exception as e:
                logger.error(f"Error processing modified row {modified_row}: {e}")
                continue
        
        return modified_products
    
    def process_deleted_rows(self, deleted_rows: List[Dict[str, Any]], headers: List[str]) -> List[Dict[str, Any]]:
        """Process deleted rows to identify which products were removed."""
        deleted_products = []
        
        for deleted_row in deleted_rows:
            try:
                # We can't get the actual row data since it's deleted, but we can use the row index
                # to identify which product was deleted based on the previous data
                deleted_products.append({
                    "row_index": deleted_row["row_index"],
                    "previous_hash": deleted_row["previous_hash"],
                    "deleted_at": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                logger.error(f"Error processing deleted row {deleted_row}: {e}")
                continue
        
        return deleted_products
    
    def _create_product_from_row(self, row: List[str], headers: List[str]) -> Optional[Dict[str, Any]]:
        """Create a product object from a Google Sheets row matching the current products.json structure."""
        # Ensure row has the same length as headers by padding with empty strings
        if len(row) < len(headers):
            row = row + [''] * (len(headers) - len(row))
        elif len(row) > len(headers):
            # Truncate row if it's longer than headers
            row = row[:len(headers)]
        
        # Create mapping of headers to values with case-insensitive matching
        row_data = {}
        header_map = {}
        for i, header in enumerate(headers):
            header_lower = header.lower()
            row_data[header] = row[i] if i < len(row) else ''
            header_map[header_lower] = header
        
        # Helper function to get data with flexible header matching
        def get_field(possible_names):
            for name in possible_names:
                # Try exact match first
                if name in row_data:
                    return str(row_data[name]).strip()
                # Try case-insensitive match
                name_lower = name.lower()
                if name_lower in header_map:
                    return str(row_data[header_map[name_lower]]).strip()
            return ''
        
        # Extract key fields based on the brochure-products sheet structure
        name = get_field(['Product Name'])
        if not name:
            return None
        
        # Get specifications and features
        specs_raw = get_field(['Specifications'])
        features = get_field(['Features'])
        
        # Process images
        hero_image = get_field(['Hero Image'])
        secondary_image = get_field(['Secondary Image'])
        
        # Build product object matching the current products.json structure
        product = {
            "name": name,
            "model": get_field(['Model Number']),
            "category": get_field(['Category']),
            "specifications": specs_raw or "",
            "features": features or "",
            "hero_image": hero_image or "",
            "secondary_image": secondary_image or ""
        }
        
        return product
    
    def _parse_specifications(self, specs_text: str) -> tuple[str, str]:
        """Parse specifications text to extract description and technical specs."""
        if not specs_text:
            return "", ""
        
        # Look for common patterns that separate features from specifications
        if 'Features:' in specs_text and 'Specifications:' in specs_text:
            parts = specs_text.split('Specifications:', 1)
            if len(parts) == 2:
                features_part = parts[0].replace('Features:', '').strip()
                specs_part = parts[1].strip()
                return features_part, specs_part
        elif 'Features:' in specs_text:
            # If only Features section exists, use it as description
            description = specs_text.replace('Features:', '').strip()
            return description, ""
        else:
            # If no clear structure, use first part as description
            sentences = specs_text.split('|')
            if len(sentences) > 3:
                description = ' | '.join(sentences[:3]).strip()
                technical_specs = ' | '.join(sentences[3:]).strip()
                return description, technical_specs
            else:
                return specs_text.strip(), ""
    
    def _parse_price(self, price_str: str) -> float:
        """Parse price string to float."""
        if not price_str:
            return 0.0
        
        # Remove currency symbols and whitespace
        price_clean = price_str.replace('$', '').replace('USD', '').replace('US$', '').strip()
        
        try:
            return float(price_clean)
        except ValueError:
            return 0.0
    
    def update_catalog(self, new_products: List[Dict[str, Any]] = None, modified_products: List[Dict[str, Any]] = None, current_sheet_models: List[str] = None) -> bool:
        """Add new products, update modified products, and remove deleted products from the catalog."""
        if not new_products and not modified_products and not current_sheet_models:
            return False
        
        try:
            products_data = self._load_products()
            
            # Add new products
            if new_products:
                products_data["products"].extend(new_products)
                logger.info(f"Added {len(new_products)} new products to catalog")
            
            # Update modified products
            if modified_products:
                updated_count = self._update_modified_products(products_data, modified_products)
                logger.info(f"Updated {updated_count} modified products in catalog")
            
            # Remove deleted products
            if current_sheet_models:
                removed_count = self._remove_deleted_products(products_data, current_sheet_models)
                if removed_count > 0:
                    logger.info(f"Removed {removed_count} deleted products from catalog")
            
            # Update categories and suppliers in metadata
            self._update_metadata_stats(products_data)
            
            # Save updated data
            self._save_products(products_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating catalog: {e}")
            return False
    
    def _update_modified_products(self, products_data: Dict[str, Any], modified_products: List[Dict[str, Any]]) -> int:
        """Update existing products with modified data."""
        updated_count = 0
        
        for modified_product in modified_products:
            # Find the product to update by model (primary key) since name might change
            product_name = modified_product.get("name")
            product_model = modified_product.get("model")
            
            if not product_model:  # Use model as primary identifier
                continue
            
            # Find matching product in the catalog by model (more reliable than name)
            for i, existing_product in enumerate(products_data["products"]):
                if existing_product.get("model") == product_model:
                    # Found matching product by model, update it
                    # Remove modification info before saving
                    clean_product = {k: v for k, v in modified_product.items() if not k.startswith("_")}
                    old_name = existing_product.get("name", "Unknown")
                    products_data["products"][i] = clean_product
                    updated_count += 1
                    logger.info(f"Updated product: {old_name} -> {product_name} ({product_model})")
                    break
        
        return updated_count
    
    def _remove_deleted_products(self, products_data: Dict[str, Any], current_sheet_models: List[str]) -> int:
        """Remove products from catalog that are no longer in the Google Sheet."""
        removed_count = 0
        
        # Create a set of model numbers that exist in the current sheet
        current_models = set(current_sheet_models)
        
        # Find products in catalog that are no longer in the sheet
        products_to_remove = []
        for i, product in enumerate(products_data["products"]):
            product_model = product.get("model", "")
            if product_model and product_model not in current_models:
                products_to_remove.append((i, product))
        
        # Remove products in reverse order to maintain indices
        for i, product in reversed(products_to_remove):
            logger.info(f"Removing deleted product: {product.get('name', 'Unknown')} ({product.get('model', 'No model')})")
            products_data["products"].pop(i)
            removed_count += 1
        
        return removed_count
    
    def _update_metadata_stats(self, products_data: Dict[str, Any]):
        """Update metadata statistics to match current products.json structure."""
        products = products_data["products"]
        
        # Extract unique categories
        categories = set()
        
        for product in products:
            if product.get("category"):
                categories.add(product["category"])
        
        # Update metadata to match current structure
        metadata = products_data.setdefault("metadata", {})
        metadata.update({
            "total_products": len(products),
            "categories": sorted(list(categories)),
            "categories_count": len(categories),
            "last_synchronized": datetime.now(timezone.utc).isoformat(),
            "source": "google_sheets_import"
        })

class AutomatedPollingService:
    """Main service for automated Google Sheets polling."""
    
    def __init__(self, spreadsheet_url: str, catalog_path: str = "data/products.json", notification_callback=None):
        # Default API key for Google Sheets
        self.api_key = "AIzaSyB23iX6kXdCBVIx2YVFSrdE2r9DXjl7T3k"
        self.client = GoogleSheetsClient(self.api_key)
        self.sheets_url = spreadsheet_url
        self.spreadsheet_id = self.client.extract_spreadsheet_id(spreadsheet_url)
        self.change_detector = ChangeDetector()
        self.data_processor = DataProcessor(catalog_path)
        self.notification_callback = notification_callback
        self.is_running = False
        self.poll_interval = 300  # 5 minutes
        self.stats = {
            "last_check": None,
            "total_checks": 0,
            "products_added": 0,
            "products_modified": 0,
            "products_deleted": 0,
            "errors": 0
        }
        
    async def start_polling(self):
        """Start the automated polling service."""
        self.is_running = True
        logger.info("Starting automated polling service...")
        logger.info(f"Polling interval: {self.poll_interval} seconds")
        
        while self.is_running:
            try:
                await self._poll_and_process()
                self.stats["last_check"] = datetime.now(timezone.utc).isoformat()
                self.stats["total_checks"] += 1
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                self.stats["errors"] += 1
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def stop_polling(self):
        """Stop the polling service."""
        self.is_running = False
        logger.info("Stopping polling service...")
    
    async def _poll_and_process(self):
        """Poll Google Sheets and process any changes."""
        try:
            logger.info("Checking Google Sheets for changes...")
            
            # Get current sheets data
            sheets_data = self.client.get_sheet_data(self.spreadsheet_id, "brochure-products")
            
            if not sheets_data:
                logger.warning("No data found in Google Sheets")
                return
            
            # Detect changes
            changes = self.change_detector.detect_changes(sheets_data)
            
            if not changes["has_changes"]:
                logger.info("No changes detected in Google Sheets")
                return
            
            headers = sheets_data[0] if sheets_data else []
            new_products = []
            modified_products = []
            current_sheet_models = []
            
            # Extract current model numbers from sheet data for deletion detection
            if len(sheets_data) > 1:  # Skip header
                for row in sheets_data[1:]:
                    if len(row) > 0:  # Make sure row has at least model number
                        model = row[0].strip() if row[0] else ""
                        if model:
                            current_sheet_models.append(model)
            
            # Process new rows
            if changes["new_row_count"] > 0:
                logger.info(f"Processing {changes['new_row_count']} new rows")
                logger.info(f"New Product Details: {changes['new_rows']}")
                
                new_products = self.data_processor.process_new_rows(changes["new_rows"], headers)
                
                if new_products:
                    self.stats["products_added"] += len(new_products)
                    logger.info(f"Successfully processed {len(new_products)} new products")
                else:
                    logger.warning("No valid products extracted from new rows")
            
            # Process modified rows
            if changes["modified_row_count"] > 0:
                logger.info(f"Processing {changes['modified_row_count']} modified rows")
                
                modified_products = self.data_processor.process_modified_rows(changes["modified_rows"], headers)
                
                if modified_products:
                    self.stats["products_modified"] += len(modified_products)
                    logger.info(f"Successfully processed {len(modified_products)} modified products")
                else:
                    logger.warning("No valid products extracted from modified rows")
            
            # Process deleted rows
            if changes["deleted_row_count"] > 0:
                logger.info(f"Processing {changes['deleted_row_count']} deleted rows")
                # We'll handle deletions by comparing current sheet models with catalog
            
            # Update catalog with new, modified, and deleted products
            if new_products or modified_products or current_sheet_models:
                success = self.data_processor.update_catalog(new_products, modified_products, current_sheet_models)
                
                if success:
                    # Send notifications
                    if new_products:
                        await self._notify_new_products(new_products)
                    
                    if modified_products:
                        await self._notify_modified_products(modified_products)
                    
                    # Send callback notification if provided
                    if self.notification_callback:
                        try:
                            await self.notification_callback({
                                "new_products": new_products,
                                "modified_products": modified_products
                            })
                        except Exception as e:
                            logger.error(f"Error sending notification: {e}")
                else:
                    logger.error("Failed to update catalog")
            
        except Exception as e:
            logger.error(f"Error polling and processing: {e}")
    
    async def _notify_new_products(self, new_products: List[Dict[str, Any]]):
        """Send notification about new products (placeholder for WebSocket integration)."""
        notification = {
            "type": "new_products",
            "count": len(new_products),
            "products": [{"name": p["name"], "model": p.get("model"), "category": p.get("category")} for p in new_products],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # TODO: Implement WebSocket broadcasting
        logger.info(f"New products notification: {notification}")
    
    async def _notify_modified_products(self, modified_products: List[Dict[str, Any]]):
        """Send notification about modified products (placeholder for WebSocket integration)."""
        notification = {
            "type": "modified_products",
            "count": len(modified_products),
            "products": [{"name": p["name"], "model": p.get("model"), "category": p.get("category")} for p in modified_products],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # TODO: Implement WebSocket broadcasting
        logger.info(f"Modified products notification: {notification}")
    
    async def _notify_deleted_products(self, deleted_products: List[Dict[str, Any]]):
        """Send notification about deleted products (placeholder for WebSocket integration)."""
        notification = {
            "type": "deleted_products",
            "count": len(deleted_products),
            "products": [{"name": p.get("name", "Unknown"), "model": p.get("model", "No model")} for p in deleted_products],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # TODO: Implement WebSocket broadcasting
        logger.info(f"Deleted products notification: {notification}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current polling service status."""
        return {
            "is_running": self.is_running,
            "poll_interval": self.poll_interval,
            "last_sync": self.change_detector.metadata.get("last_sync"),
            "last_check": self.stats["last_check"],
            "total_checks": self.stats["total_checks"],
            "products_added": self.stats["products_added"],
            "products_modified": self.stats["products_modified"],
            "products_deleted": self.stats["products_deleted"],
            "errors": self.stats["errors"],
            "total_rows": self.change_detector.metadata.get("sheet_fingerprint", {}).get("row_count", 0),
            "spreadsheet_id": self.spreadsheet_id
        }

# Global service instance
polling_service: Optional[AutomatedPollingService] = None

def get_polling_service() -> Optional[AutomatedPollingService]:
    """Get the global polling service instance."""
    return polling_service

def initialize_polling_service(sheets_url: str, catalog_path: str = "data/products.json", notification_callback=None) -> AutomatedPollingService:
    """Initialize the global polling service."""
    global polling_service
    polling_service = AutomatedPollingService(sheets_url, catalog_path, notification_callback)
    return polling_service

async def main():
    """Main function for testing the polling service."""
    # Configuration
    SHEETS_URL = "https://docs.google.com/spreadsheets/d/17xcmTsSZkguOjXC6h6YDrNcOU27jrpU8Ah9xEONARg8/edit?gid=1707985453#gid=1707985453"
    
    # Initialize service
    service = initialize_polling_service(SHEETS_URL)
    
    # Start polling
    try:
        await service.start_polling()
    except KeyboardInterrupt:
        logger.info("Polling service stopped by user")
        service.stop_polling()

if __name__ == "__main__":
    asyncio.run(main())
