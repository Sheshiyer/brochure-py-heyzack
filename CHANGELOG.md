# Changelog

## [Enhanced] - PDF Export Functionality for Live Catalog

### PDF Generation Improvements
- **Added multiple PDF generation methods**: Playwright (sync/async), Pyppeteer, and ReportLab with automatic fallback
- **Windows compatibility**: Implemented synchronous Playwright approach to handle Windows subprocess limitations
- **Live catalog design preservation**: PDF now maintains exact visual design from live catalog instead of simple format
- **Enhanced CSS optimization**: Added PDF-specific styling to hide live elements and optimize page breaks
- **Improved error handling**: Better fallback mechanisms when primary PDF generation methods fail

### Technical Implementation
- **Playwright Sync Method**: Primary method using synchronous Playwright API for Windows compatibility
- **CSS Injection**: Automatically hides live indicators, notifications, and export buttons in PDF
- **Page Break Optimization**: Ensures proper page breaks for product pages, cover, and back cover
- **Image Rendering**: Optimized image display and scaling for PDF output
- **Background Printing**: Preserves colors and gradients in PDF output

### Dependencies Added
- `playwright>=1.40.0` - For browser-based PDF generation
- `pyppeteer>=1.0.2` - Alternative browser automation
- `fastapi>=0.104.0` - Web framework for API endpoints
- `uvicorn>=0.24.0` - ASGI server
- `python-multipart>=0.0.6` - Form data handling
- `python-dotenv>=1.0.0` - Environment variable management
- `boto3>=1.34.0` - AWS S3 integration

### User Experience
- **One-click PDF export**: Users can download live catalog as PDF with same design
- **Automatic filename**: PDFs are named with current date (e.g., `HeyZack-Catalog-2025-01-15.pdf`)
- **Loading states**: Button shows progress during PDF generation
- **Error handling**: User-friendly error messages if PDF generation fails

## [Fixed] - Catalog Live Template Alignment Issues

### Back Cover Layout Fixes
- **Fixed section class**: Changed from `cover-page` to `back-cover` for proper styling
- **Fixed company title visibility**: "HeyZack AI Calling Agent" now displays correctly with proper CSS styling
- **Fixed value proposition alignment**: "Why Choose HeyZack?" section now has proper grid alignment
- **Fixed partner section**: Wrapped image in proper `partner-section` div for consistent layout

### Technical Changes
- Updated HTML structure to use correct CSS classes (`back-cover`, `partner-section`)
- Ensured proper grid layout for value proposition items
- Fixed text visibility with appropriate color contrast and styling

## [Updated] - Automated Polling Service Enhancement

### Changes Made

#### Enhanced Change Detection
- **Row-level fingerprinting**: Added individual row hash tracking for precise change detection
- **Modified row detection**: Service now detects changes in existing rows, not just new additions
- **Detailed change tracking**: Tracks both new rows and modified rows separately

#### Updated Product Structure
- **Aligned with current products.json**: Updated product creation to match the existing structure:
  - `name`: Product name
  - `model`: Model number
  - `category`: Product category
  - `specifications`: Product specifications
  - `features`: Product features
  - `hero_image`: Primary product image
  - `secondary_image`: Secondary product image

#### Enhanced Data Processing
- **Flexible header matching**: Case-insensitive header matching with multiple possible field names
- **Modified product handling**: New method to process and update existing products
- **Improved catalog updates**: Handles both new additions and modifications in a single operation

#### Updated Metadata Management
- **Current structure compliance**: Metadata now matches the existing products.json format
- **Enhanced statistics**: Tracks both added and modified product counts
- **Source tracking**: Maintains source information for data lineage

#### Notification System
- **Dual notification types**: Separate notifications for new and modified products
- **Enhanced callback support**: Updated callback structure to handle both change types
- **Detailed logging**: Comprehensive logging for all change operations

### Technical Improvements

#### ChangeDetector Class
- `create_data_fingerprint()`: Now creates individual row hashes for detailed tracking
- `detect_changes()`: Enhanced to detect both new and modified rows
- Improved metadata storage for better change tracking

#### DataProcessor Class
- `process_modified_rows()`: New method to handle modified row processing
- `_create_product_from_row()`: Updated to match current products.json structure
- `update_catalog()`: Enhanced to handle both new and modified products
- `_update_modified_products()`: New method for updating existing products
- `_update_metadata_stats()`: Updated to match current metadata structure

#### AutomatedPollingService Class
- Enhanced `_poll_and_process()`: Now handles both new and modified rows
- `_notify_modified_products()`: New notification method for modified products
- Updated statistics tracking for both addition and modification counts
- Enhanced status reporting with modification statistics

### Key Features

1. **Real-time Change Detection**: Monitors Google Sheets every 5 minutes for any changes
2. **Granular Change Tracking**: Detects changes at the individual row level
3. **Automatic Product Updates**: Updates existing products when their data changes
4. **Flexible Field Mapping**: Handles various header naming conventions
5. **Comprehensive Logging**: Detailed logs for all operations and changes
6. **Backup System**: Creates backups before any updates
7. **Notification System**: Ready for WebSocket integration for real-time updates

### Usage

The service now automatically:
- Detects new rows added to the Google Sheet
- Identifies modifications to existing rows
- Updates the products.json file accordingly
- Maintains proper metadata and statistics
- Provides detailed logging and notifications

### Configuration

The service uses the same Google Sheets URL and maintains backward compatibility with existing configurations while adding enhanced change detection capabilities.

## [Updated] - Server Integration Enhancement

### Server.py Updates

#### Enhanced Notification System
- **Updated callback function**: `notify_product_changes()` now handles both new and modified products
- **Dual notification types**: Separate WebSocket notifications for new vs modified products
- **Enhanced dashboard**: Shows both added and modified product counts

#### WebSocket Integration
- **Real-time notifications**: Dashboard now displays both new product additions and modifications
- **Enhanced logging**: Real-time logs show different messages for new vs modified products
- **Improved user feedback**: Clear distinction between new products and product updates

#### Dashboard Enhancements
- **Modified products tracking**: Dashboard now displays count of modified products
- **Enhanced status display**: Shows both `products_added` and `products_modified` statistics
- **Real-time updates**: WebSocket messages distinguish between new and modified product notifications

### Key Server Features

1. **Real-time Change Notifications**: WebSocket broadcasts for both new and modified products
2. **Enhanced Dashboard**: Shows comprehensive statistics including modification counts
3. **Improved User Experience**: Clear distinction between different types of changes
4. **Backward Compatibility**: Maintains existing API endpoints and functionality

## [Updated] - Product Deletion Support

### Enhanced Change Detection
- **Deleted row detection**: Service now detects when rows are removed from Google Sheets
- **Automatic product removal**: Deleted products are automatically removed from the catalog
- **Model-based matching**: Uses model numbers as primary identifiers for reliable product matching

### Deletion Processing
- **Smart product removal**: Compares current sheet models with catalog to identify deleted products
- **Robust matching**: Uses model numbers instead of names for more reliable product identification
- **Comprehensive logging**: Detailed logs for all deletion operations

### Enhanced Notifications
- **Deleted product notifications**: Separate WebSocket notifications for deleted products
- **Dashboard updates**: Shows count of deleted products in statistics
- **Real-time feedback**: Users can see when products are removed from the catalog

### Key Features Added

1. **Complete CRUD Support**: Create, Read, Update, and Delete operations for products
2. **Automatic Cleanup**: Removes products that no longer exist in Google Sheets
3. **Model-based Tracking**: Uses model numbers as unique identifiers for reliable matching
4. **Enhanced Statistics**: Tracks added, modified, and deleted product counts
5. **Real-time Deletion Notifications**: Immediate feedback when products are removed

### Technical Implementation

- **Row-level tracking**: Monitors individual row hashes to detect deletions
- **Model extraction**: Extracts model numbers from current sheet data for comparison
- **Catalog synchronization**: Ensures catalog matches the current state of Google Sheets
- **Backup system**: Creates backups before any deletion operations
