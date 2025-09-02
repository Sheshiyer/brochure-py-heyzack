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
            return {"row_count": 0, "data_hash": "", "last_row_hash": ""}
        
        # Calculate hash of all data
        data_str = json.dumps(sheets_data, sort_keys=True)
        data_hash = hashlib.md5(data_str.encode('utf-8')).hexdigest()
        
        # Calculate hash of last row for quick new row detection
        last_row_hash = ""
        if len(sheets_data) > 1:  # Skip header
            last_row_str = json.dumps(sheets_data[-1], sort_keys=True)
            last_row_hash = hashlib.md5(last_row_str.encode('utf-8')).hexdigest()
        
        return {
            "row_count": len(sheets_data) - 1,  # Exclude header
            "data_hash": data_hash,
            "last_row_hash": last_row_hash,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def detect_changes(self, current_data: List[List[str]]) -> Dict[str, Any]:
        """Detect what has changed since last check."""
        current_fingerprint = self.create_data_fingerprint(current_data)
        
        changes = {
            "has_changes": False,
            "new_rows": [],
            "new_row_count": 0,
            "total_rows": current_fingerprint["row_count"],
            "previous_rows": self.metadata.get("sheet_fingerprint", {}).get("row_count", 0)
        }
        
        previous_fingerprint = self.metadata.get("sheet_fingerprint", {})
        
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
    
    def _create_product_from_row(self, row: List[str], headers: List[str]) -> Optional[Dict[str, Any]]:
        """Create a product object from a Google Sheets row."""
        if len(row) < len(headers):
            # Pad row with empty strings if needed
            row = row + [''] * (len(headers) - len(row))
        
        # Create mapping of headers to values
        row_data = {headers[i]: (row[i] if i < len(row) else '') for i in range(len(headers))}
        
        # Extract key fields (adjust based on your sheet structure)
        name = str(row_data.get('Product Name', '')).strip()
        if not name:
            return None
        
        # Generate unique product ID
        timestamp = int(time.time() * 1000000)  # microsecond precision
        product_id = f"product-{timestamp}"
        
        # Build product object
        product = {
            "id": product_id,
            "name": name,
            "model": str(row_data.get('Model', '')).strip(),
            "supplier": str(row_data.get('Supplier', '')).strip(),
            "category": str(row_data.get('Category', '')).strip(),
            "price": self._parse_price(str(row_data.get('Price', ''))),
            "currency": "USD",
            "status": "published",
            "images": [],
            "specifications": {
                "description": str(row_data.get('Description', '')).strip() or "New smart home product with advanced features.",
                "specifications": str(row_data.get('Specifications', '')).strip(),
                "features": str(row_data.get('Features', '')).strip(),
                "communication_protocol": str(row_data.get('Protocol', '')).strip(),
                "power_source": str(row_data.get('Power Source', '')).strip(),
                "country": str(row_data.get('Country', '')).strip(),
                "moq": str(row_data.get('MOQ', '')).strip(),
                "lead_time": str(row_data.get('Lead Time', '')).strip()
            },
            "metadata": {
                "enhanced_id": f"{str(row_data.get('Supplier', '')).strip()}_{str(row_data.get('Model', '')).strip()}",
                "drive_link": str(row_data.get('Drive Link', '')).strip(),
                "price_raw": str(row_data.get('Price', '')).strip(),
                "ref_heyzack": str(row_data.get('Ref Heyzack', '')).strip() or None,
                "designation_fr": str(row_data.get('Designation FR', '')).strip() or None
            },
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }
        
        return product
    
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
    
    def update_catalog(self, new_products: List[Dict[str, Any]]) -> bool:
        """Add new products to the catalog."""
        if not new_products:
            return False
        
        try:
            products_data = self._load_products()
            
            # Add new products
            products_data["products"].extend(new_products)
            
            # Update categories and suppliers in metadata
            self._update_metadata_stats(products_data)
            
            # Save updated data
            self._save_products(products_data)
            
            logger.info(f"Added {len(new_products)} new products to catalog")
            return True
            
        except Exception as e:
            logger.error(f"Error updating catalog: {e}")
            return False
    
    def _update_metadata_stats(self, products_data: Dict[str, Any]):
        """Update metadata statistics."""
        products = products_data["products"]
        
        # Extract unique categories and suppliers
        categories = set()
        suppliers = set()
        total_price = 0
        price_count = 0
        
        for product in products:
            if product.get("category"):
                categories.add(product["category"])
            if product.get("supplier"):
                suppliers.add(product["supplier"])
            
            price = product.get("price", 0)
            if price > 0:
                total_price += price
                price_count += 1
        
        # Update metadata
        metadata = products_data.setdefault("metadata", {})
        metadata.update({
            "categories": sorted(list(categories)),
            "categories_count": len(categories),
            "suppliers": sorted(list(suppliers)),
            "suppliers_count": len(suppliers),
            "average_price": total_price / price_count if price_count > 0 else 0
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
            sheets_data = self.client.get_sheet_data(self.spreadsheet_id, "All Products")
            
            if not sheets_data:
                logger.warning("No data found in Google Sheets")
                return
            
            # Detect changes
            changes = self.change_detector.detect_changes(sheets_data)
            
            if not changes["has_changes"]:
                logger.info("No changes detected in Google Sheets")
                return
            
            if changes["new_row_count"] > 0:
                logger.info(f"Processing {changes['new_row_count']} new rows")
                
                # Process new rows
                headers = sheets_data[0] if sheets_data else []
                new_products = self.data_processor.process_new_rows(changes["new_rows"], headers)
                
                if new_products:
                    # Update catalog
                    success = self.data_processor.update_catalog(new_products)
                    
                    if success:
                        self.stats["products_added"] += len(new_products)
                        logger.info(f"Successfully added {len(new_products)} new products")
                        
                        # Send notification if callback is provided
                        if self.notification_callback:
                            try:
                                await self.notification_callback(new_products)
                            except Exception as e:
                                logger.error(f"Error sending notification: {e}")
                        
                        await self._notify_new_products(new_products)
                    else:
                        logger.error("Failed to update catalog")
                else:
                    logger.warning("No valid products extracted from new rows")
            
        except Exception as e:
            logger.error(f"Error polling and processing: {e}")
    
    async def _notify_new_products(self, new_products: List[Dict[str, Any]]):
        """Send notification about new products (placeholder for WebSocket integration)."""
        notification = {
            "type": "new_products",
            "count": len(new_products),
            "products": [{"id": p["id"], "name": p["name"], "category": p["category"]} for p in new_products],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # TODO: Implement WebSocket broadcasting
        logger.info(f"New products notification: {notification}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current polling service status."""
        return {
            "is_running": self.is_running,
            "poll_interval": self.poll_interval,
            "last_sync": self.change_detector.metadata.get("last_sync"),
            "last_check": self.stats["last_check"],
            "total_checks": self.stats["total_checks"],
            "products_added": self.stats["products_added"],
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
    SHEETS_URL = "https://docs.google.com/spreadsheets/d/17xcmTsSZkguOjXC6h6YDrNcOU27jrpU8Ah9xEONARg8/edit?gid=86173031#gid=86173031"
    
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
