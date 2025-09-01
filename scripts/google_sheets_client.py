#!/usr/bin/env python3
"""
Google Sheets API Client for Smart Home Product Data

This module provides read-only access to the Google Sheets master data source.
Treats the Google Sheets as the authoritative source of truth.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs

try:
    import requests
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleSheetsClient:
    """
    Read-only Google Sheets API client for accessing product data.
    
    Uses the Google Sheets API v4 to safely read data without modification.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://sheets.googleapis.com/v4/spreadsheets"
        self.session = requests.Session()
        
    def extract_spreadsheet_id(self, sheets_url: str) -> str:
        """
        Extract spreadsheet ID from Google Sheets URL.
        
        Args:
            sheets_url: Full Google Sheets URL
            
        Returns:
            Spreadsheet ID string
        """
        # Extract ID from URL like: https://docs.google.com/spreadsheets/d/{ID}/edit...
        if "/spreadsheets/d/" in sheets_url:
            start = sheets_url.find("/spreadsheets/d/") + len("/spreadsheets/d/")
            end = sheets_url.find("/", start)
            if end == -1:
                end = sheets_url.find("?", start)
            if end == -1:
                end = len(sheets_url)
            return sheets_url[start:end]
        raise ValueError(f"Invalid Google Sheets URL: {sheets_url}")
    
    def get_spreadsheet_metadata(self, spreadsheet_id: str) -> Dict[str, Any]:
        """
        Get spreadsheet metadata including all sheet names and properties.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            
        Returns:
            Dictionary containing spreadsheet metadata
        """
        url = f"{self.base_url}/{spreadsheet_id}"
        params = {
            "key": self.api_key,
            "fields": "sheets.properties,properties.title"
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get spreadsheet metadata: {e}")
            raise
    
    def get_sheet_data(self, spreadsheet_id: str, sheet_name: str, range_spec: str = None) -> List[List[str]]:
        """
        Get data from a specific sheet.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the sheet to read
            range_spec: Optional range specification (e.g., "A1:Z1000")
            
        Returns:
            List of rows, where each row is a list of cell values
        """
        # Construct range
        if range_spec:
            range_name = f"'{sheet_name}'!{range_spec}"
        else:
            range_name = f"'{sheet_name}'"
        
        url = f"{self.base_url}/{spreadsheet_id}/values/{range_name}"
        params = {
            "key": self.api_key,
            "valueRenderOption": "UNFORMATTED_VALUE",
            "dateTimeRenderOption": "FORMATTED_STRING"
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("values", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get sheet data: {e}")
            raise
    
    def analyze_sheet_structure(self, spreadsheet_id: str, sheet_name: str) -> Dict[str, Any]:
        """
        Analyze the structure of a sheet including headers and data types.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of the sheet to analyze
            
        Returns:
            Dictionary containing structure analysis
        """
        # Get first 100 rows to analyze structure
        data = self.get_sheet_data(spreadsheet_id, sheet_name, "A1:Z100")
        
        if not data:
            return {"error": "No data found in sheet"}
        
        headers = data[0] if data else []
        sample_rows = data[1:min(10, len(data))] if len(data) > 1 else []
        
        analysis = {
            "sheet_name": sheet_name,
            "total_rows_sampled": len(data),
            "headers": headers,
            "header_count": len(headers),
            "sample_data_rows": len(sample_rows),
            "column_analysis": {}
        }
        
        # Analyze each column
        for i, header in enumerate(headers):
            column_values = []
            for row in sample_rows:
                if i < len(row) and row[i] is not None:
                    column_values.append(str(row[i]))
            
            analysis["column_analysis"][header] = {
                "index": i,
                "sample_values": column_values[:5],  # First 5 non-empty values
                "non_empty_count": len(column_values),
                "contains_urls": any("http" in str(val) for val in column_values),
                "contains_drive_links": any("drive.google.com" in str(val) for val in column_values)
            }
        
        return analysis
    
    def batch_update_cells(self, spreadsheet_id: str, updates: List[dict]) -> bool:
        """
        Batch update multiple cells in the spreadsheet.
        Note: This is a read-only API key implementation that cannot actually update.
        This method is included for interface compatibility but will return False.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet
            updates: List of update objects with 'range' and 'values' keys
            
        Returns:
            False (read-only API cannot update)
        """
        print("⚠️  Cannot update Google Sheets with read-only API key")
        print("   To enable updates, you need:")
        print("   1. Service Account credentials (JSON file)")
        print("   2. Google Sheets API write permissions")
        print("   3. Sheet shared with service account email")
        print(f"\n   Would update {len(updates)} cells:")
        for update in updates[:3]:  # Show first 3 updates
            print(f"   - {update['range']}: {update['values'][0][0][:50]}...")
        if len(updates) > 3:
            print(f"   - ... and {len(updates) - 3} more")
        return False

def main():
    """
    Test the Google Sheets client with the provided credentials.
    """
    # Configuration
    API_KEY = "AIzaSyB23iX6kXdCBVIx2YVFSrdE2r9DXjl7T3k"
    SHEETS_URL = "https://docs.google.com/spreadsheets/d/17xcmTsSZkguOjXC6h6YDrNcOU27jrpU8Ah9xEONARg8/edit?gid=86173031#gid=86173031"
    
    try:
        # Initialize client
        client = GoogleSheetsClient(API_KEY)
        spreadsheet_id = client.extract_spreadsheet_id(SHEETS_URL)
        
        print(f"Spreadsheet ID: {spreadsheet_id}")
        
        # Get spreadsheet metadata
        print("\n=== Spreadsheet Metadata ===")
        metadata = client.get_spreadsheet_metadata(spreadsheet_id)
        print(f"Spreadsheet Title: {metadata.get('properties', {}).get('title', 'Unknown')}")
        
        # List all sheets
        sheets = metadata.get('sheets', [])
        print(f"\nFound {len(sheets)} sheets:")
        for sheet in sheets:
            props = sheet.get('properties', {})
            print(f"  - {props.get('title', 'Unnamed')} (ID: {props.get('sheetId', 'Unknown')})")
        
        # Analyze each sheet
        print("\n=== Sheet Analysis ===")
        for sheet in sheets:
            sheet_name = sheet.get('properties', {}).get('title', 'Unnamed')
            print(f"\nAnalyzing sheet: {sheet_name}")
            
            try:
                analysis = client.analyze_sheet_structure(spreadsheet_id, sheet_name)
                print(f"  Headers ({analysis['header_count']}): {', '.join(analysis['headers'][:5])}{'...' if len(analysis['headers']) > 5 else ''}")
                print(f"  Rows sampled: {analysis['total_rows_sampled']}")
                
                # Check for Drive links
                drive_columns = []
                for header, col_info in analysis['column_analysis'].items():
                    if col_info['contains_drive_links']:
                        drive_columns.append(header)
                
                if drive_columns:
                    print(f"  🔗 Drive links found in columns: {', '.join(drive_columns)}")
                
            except Exception as e:
                print(f"  ❌ Error analyzing sheet: {e}")
        
        print("\n✅ Google Sheets analysis completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())