#!/usr/bin/env python3
"""
Detailed Google Sheets Data Analyzer

Analyzes the 'All Products' sheet in detail and compares with existing data.
"""

import json
import csv
import os
from typing import Dict, List, Any
from google_sheets_client import GoogleSheetsClient

def load_existing_csv_data(csv_path: str) -> List[Dict[str, Any]]:
    """
    Load existing CSV data for comparison.
    """
    if not os.path.exists(csv_path):
        return []
    
    data = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(dict(row))
    return data

def analyze_drive_links(sheet_data: List[List[str]], headers: List[str]) -> Dict[str, Any]:
    """
    Analyze Drive links in the sheet data.
    """
    drive_link_col = None
    for i, header in enumerate(headers):
        if 'drive' in header.lower() and 'link' in header.lower():
            drive_link_col = i
            break
    
    if drive_link_col is None:
        return {"error": "No Drive Link column found"}
    
    drive_links = []
    for row_idx, row in enumerate(sheet_data[1:], 1):  # Skip header
        if drive_link_col < len(row) and row[drive_link_col]:
            link = str(row[drive_link_col]).strip()
            if link and 'drive.google.com' in link:
                drive_links.append({
                    "row": row_idx,
                    "url": link,
                    "type": "view" if "/view" in link else "other",
                    "file_id": extract_drive_file_id(link)
                })
    
    return {
        "total_drive_links": len(drive_links),
        "view_links": len([l for l in drive_links if l["type"] == "view"]),
        "other_links": len([l for l in drive_links if l["type"] == "other"]),
        "sample_links": drive_links[:5],
        "all_links": drive_links
    }

def extract_drive_file_id(drive_url: str) -> str:
    """
    Extract file ID from Google Drive URL.
    """
    if "/file/d/" in drive_url:
        start = drive_url.find("/file/d/") + len("/file/d/")
        end = drive_url.find("/", start)
        if end == -1:
            end = drive_url.find("?", start)
        if end == -1:
            end = len(drive_url)
        return drive_url[start:end]
    return ""

def compare_with_csv(sheet_data: List[List[str]], csv_data: List[Dict[str, Any]], headers: List[str]) -> Dict[str, Any]:
    """
    Compare Google Sheets data with existing CSV data.
    """
    # Convert sheet data to dict format
    sheet_products = []
    for row in sheet_data[1:]:  # Skip header
        if len(row) > 0:  # Skip empty rows
            product = {}
            for i, header in enumerate(headers):
                product[header] = row[i] if i < len(row) else ""
            sheet_products.append(product)
    
    comparison = {
        "sheets_count": len(sheet_products),
        "csv_count": len(csv_data),
        "sheets_headers": headers,
        "csv_headers": list(csv_data[0].keys()) if csv_data else [],
        "common_headers": [],
        "sheets_only_headers": [],
        "csv_only_headers": []
    }
    
    if csv_data:
        csv_headers = set(csv_data[0].keys())
        sheets_headers = set(headers)
        
        comparison["common_headers"] = list(csv_headers.intersection(sheets_headers))
        comparison["sheets_only_headers"] = list(sheets_headers - csv_headers)
        comparison["csv_only_headers"] = list(csv_headers - sheets_headers)
    
    return comparison

def main():
    """
    Analyze Google Sheets data in detail.
    """
    # Configuration
    API_KEY = "AIzaSyB23iX6kXdCBVIx2YVFSrdE2r9DXjl7T3k"
    SHEETS_URL = "https://docs.google.com/spreadsheets/d/17xcmTsSZkguOjXC6h6YDrNcOU27jrpU8Ah9xEONARg8/edit?gid=1707985453#gid=1707985453"
    CSV_PATH = "data/SMART HOME FOLLOWING PROJECT - All Products.csv"
    
    try:
        # Initialize client
        client = GoogleSheetsClient(API_KEY)
        spreadsheet_id = client.extract_spreadsheet_id(SHEETS_URL)
        
        print("=== Detailed Analysis of 'All Products' Sheet ===")
        
        # Get full data from All Products sheet
        sheet_data = client.get_sheet_data(spreadsheet_id, "All Products")
        headers = sheet_data[0] if sheet_data else []
        
        print(f"Total rows: {len(sheet_data)}")
        print(f"Headers: {headers}")
        
        # Analyze Drive links
        print("\n=== Drive Links Analysis ===")
        drive_analysis = analyze_drive_links(sheet_data, headers)
        if "error" not in drive_analysis:
            print(f"Total Drive links: {drive_analysis['total_drive_links']}")
            print(f"View links: {drive_analysis['view_links']}")
            print(f"Other links: {drive_analysis['other_links']}")
            
            print("\nSample Drive links:")
            for link in drive_analysis['sample_links']:
                print(f"  Row {link['row']}: {link['type']} - {link['url'][:80]}...")
                if link['file_id']:
                    print(f"    File ID: {link['file_id']}")
        else:
            print(f"Error: {drive_analysis['error']}")
        
        # Compare with existing CSV
        print("\n=== Comparison with Existing CSV ===")
        csv_data = load_existing_csv_data(CSV_PATH)
        comparison = compare_with_csv(sheet_data, csv_data, headers)
        
        print(f"Google Sheets products: {comparison['sheets_count']}")
        print(f"CSV products: {comparison['csv_count']}")
        print(f"Common headers: {len(comparison['common_headers'])}")
        print(f"Sheets-only headers: {comparison['sheets_only_headers']}")
        print(f"CSV-only headers: {comparison['csv_only_headers']}")
        
        # Save detailed analysis
        analysis_report = {
            "timestamp": "2025-01-27",
            "spreadsheet_id": spreadsheet_id,
            "sheet_analysis": {
                "name": "All Products",
                "total_rows": len(sheet_data),
                "headers": headers
            },
            "drive_links": drive_analysis,
            "csv_comparison": comparison
        }
        
        with open("reports/google_sheets_analysis.json", "w", encoding="utf-8") as f:
            json.dump(analysis_report, f, indent=2, ensure_ascii=False)
        
        print("\n✅ Detailed analysis saved to reports/google_sheets_analysis.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())