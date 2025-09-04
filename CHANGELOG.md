# Changelog

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

## [Updated] - Intro Page Design Implementation

### New Intro Page Design
- **Dark Mode Interface**: Black background with white elements matching the reference image
- **House Icon**: Custom SVG house icon with door and windows
- **Brand Typography**: "HEY" in vertical text and "ZACK" in horizontal text with stylized triangular 'A'
- **Interactive Elements**: Subtle animations and interaction hints
- **Responsive Design**: Optimized for different screen sizes and print formats

### Design Features
- **Minimalist Layout**: Clean, focused design centered on brand identity
- **Floating Animation**: House icon with subtle floating animation
- **Pulse Effect**: Interactive hint dot with pulsing animation
- **Typography Styling**: Custom font weights and letter spacing
- **Print Optimization**: Ensures proper rendering in PDF generation

### Technical Implementation
- **SVG Graphics**: Scalable vector house icon for crisp rendering
- **CSS Animations**: Smooth floating and pulsing effects
- **Flexbox Layout**: Centered, responsive design
- **Print Styles**: Special CSS rules for PDF generation
- **Cross-browser Compatibility**: Works across modern browsers

### Integration
- **Cover Page Replacement**: Intro design now serves as the main cover page
- **Seamless Flow**: Smooth transition from intro to product showcase
- **Template Integration**: Fully integrated with existing brochure template system
- **Theme Consistency**: Maintains design consistency with overall brochure theme

### Live Catalog Integration
- **Consistent Design**: Live catalog now uses the same intro page design as the main brochure
- **Live Indicator**: Added "Live Catalog" indicator with pulsing animation on the intro page
- **Seamless Experience**: Both brochure and live catalog share the same visual identity
- **Real-time Updates**: Live catalog maintains the intro design while providing real-time product updates

### Intro Image Integration
- **Image-based Cover**: Replaced custom intro design with the actual intro.png image as the cover page
- **Full-page Display**: Intro image now covers the entire first page with proper scaling and positioning
- **Static Asset Management**: Intro image properly integrated into the static assets directory
- **Live Catalog Overlay**: Live catalog version includes overlay indicator on the intro image
- **Responsive Design**: Image scales properly across different screen sizes and print formats

### Full-Page Image Display Fix
- **Removed Live Indicator**: Eliminated "Live Catalog" text overlay from the intro image
- **Full-Page Coverage**: Image now covers the entire viewport without margins or padding
- **CSS Optimization**: Added proper viewport units (100vw, 100vh) for true full-page display
- **Margin/Padding Reset**: Ensured no default browser margins interfere with image display
- **Clean Layout**: Intro image now displays as a true full-page cover without any UI elements

### Full-Page Display Enhancement
- **Fixed Positioning**: Used `position: fixed` to ensure image covers entire viewport
- **CSS Override**: Added `!important` rules to override existing cover-page styles
- **Viewport Units**: Ensured 100vw/100vh coverage with absolute positioning
- **Container Override**: Removed all margins, padding, and centering from parent containers
- **Z-index Management**: Set high z-index to ensure image appears above other elements

### Complete Full-Page Coverage Fix
- **Object-fit Fill**: Changed from `object-fit: cover` to `object-fit: fill` to stretch image to fill entire viewport
- **Minimum Dimensions**: Added `min-width: 100vw` and `min-height: 100vh` to ensure complete coverage
- **Black Background**: Set black background on all containers to eliminate any visible gaps
- **Overflow Hidden**: Added `overflow: hidden` to html and body to prevent any scrolling or gaps
- **Border Removal**: Explicitly removed all borders and outlines that could create visible edges

### Image Scaling Enhancement
- **Increased Scale**: Applied `transform: scale(1.2)` to make the image 20% larger
- **Extended Dimensions**: Set image to `width: 120vw` and `height: 120vh` for complete coverage
- **Centered Positioning**: Used negative margins (`left: -10vw; top: -10vh`) to center the oversized image
- **Transform Origin**: Set `transform-origin: center center` for proper scaling from the center
- **Guaranteed Coverage**: Ensures the image extends beyond viewport boundaries to eliminate any gaps

### HTML Structure Cleanup
- **Removed Extra Container**: Eliminated the unnecessary `intro-image-container` div that was causing conflicts
- **Simplified HTML**: Changed from `class="cover-page intro-image"` to just `class="intro-image"` to avoid CSS conflicts
- **Direct Image Placement**: Image is now directly inside the section without extra wrapper divs
- **CSS Simplification**: Removed all duplicate and conflicting CSS rules
- **Clean Structure**: Now uses simple, direct CSS without complex overrides or transforms

### Image Centering Fix
- **Object Position Adjustment**: Changed `object-position` from `center center` to `60% center` to shift content right
- **Transform Translation**: Added `transform: translateX(10%)` to move the image content to the right
- **Absolute Positioning**: Ensured image is positioned absolutely within the container
- **Content Centering**: The intro image content should now appear centered on the page instead of shifted left

### CSS Override Enhancement
- **Selector Specificity**: Changed `.cover-page` to `.cover-page:not(.intro-image)` to exclude intro images
- **Important Declarations**: Added `!important` to all intro-image CSS properties to ensure they override existing styles
- **Complete Override**: Intro image now completely bypasses the original cover-page styles (210mm x 297mm dimensions)
- **Full Coverage**: Image should now properly cover the entire viewport without any interference from existing CSS

## [Updated] - Back Cover Page Redesign

### Simplified Back Cover Layout
- **Removed Sections**: Eliminated "Partner Network Benefits", "Business Hours", and "Ready to Partner?" sections
- **Clean Design**: Kept only "Why Choose HeyZack?" section at the top
- **Split Layout**: Back cover now has a 50/50 split between content and image
- **Outro Image Integration**: Added `outro.png` image to cover the bottom half of the back cover

### New Back Cover Structure
- **Top Half (50%)**: Contains "Why Choose HeyZack?" content with company description and value proposition
- **Bottom Half (50%)**: Features the `outro.png` image covering the entire bottom section
- **Full Coverage**: Outro image uses `object-fit: cover` to fill the entire bottom half
- **Consistent Styling**: Maintains the same dark gradient background for the top section

### Technical Implementation
- **Flexbox Layout**: Uses `display: flex; flex-direction: column` for clean 50/50 split
- **Image Optimization**: Outro image properly scaled and positioned to cover bottom half
- **Responsive Design**: Layout adapts to different screen sizes while maintaining proportions
- **Static Assets**: Outro image properly integrated into the static assets directory

## [Updated] - Back Cover Content Simplification

### Content Structure Changes
- **Removed Title**: Eliminated "HeyZack AI Calling Agent" title from the top section
- **Removed Description**: Removed the company description paragraph
- **Simplified Layout**: "Why Choose HeyZack?" is now the primary heading at the top
- **Clean Design**: Focus is now entirely on the value propositions and outro image

### Layout Structure
- **Top Half (50%)**: Contains only "Why Choose HeyZack?" with the 4 value propositions
- **Bottom Half (50%)**: Features the `outro.png` image covering the entire bottom section
- **Minimal Content**: Streamlined design with essential information only

## [Updated] - Back Cover Image Removal

### Content Structure Changes
- **Removed Outro Image**: Eliminated the `outro.png` image from the bottom half
- **Full Page Content**: "Why Choose HeyZack?" now covers the entire back cover page
- **Centered Layout**: Content is centered both horizontally and vertically on the page
- **Simplified Design**: Clean, text-only back cover with value propositions

### Layout Structure
- **Full Page (100%)**: "Why Choose HeyZack?" content covers the entire back cover
- **Centered Content**: Content is centered using flexbox alignment
- **Clean Design**: No image distractions, focus entirely on value propositions

## [Updated] - Back Cover Image Integration

### Content Structure Changes
- **Added Outro Image**: Integrated `outro.png` image below the "Why Choose HeyZack?" content
- **Vertical Layout**: Content flows vertically with text at top and image below
- **Balanced Design**: Proper spacing between content sections
- **Responsive Image**: Image scales appropriately while maintaining aspect ratio

### Layout Structure
- **Top Section**: "Why Choose HeyZack?" with 4 value propositions
- **Bottom Section**: Outro image centered below the content
- **Flexbox Layout**: Uses `flex-direction: column` for proper vertical stacking
- **Centered Design**: Both content and image are centered on the page

## [Updated] - Back Cover Alignment and Sizing Fixes

### Layout Improvements
- **Fixed Value Grid**: Changed from CSS Grid to Flexbox for proper vertical stacking
- **Single Column Layout**: Value propositions now stack vertically instead of 2x2 grid
- **Proper Sizing**: Added max-width constraints to prevent overflow
- **Responsive Design**: Content scales appropriately within page boundaries

### Technical Fixes
- **Value Grid**: Changed to `display: flex; flex-direction: column` with max-width: 400px
- **Content Container**: Added `overflow: hidden` and proper box-sizing
- **Image Sizing**: Reduced outro image max-width to 350px for better fit
- **Spacing**: Optimized padding and gaps for better content distribution
- **Alignment**: Ensured all content is properly centered and contained

## [Updated] - Back Cover Size Optimization

### Layout Improvements
- **Reduced Grid Size**: Decreased value-grid max-width to 450px to prevent overflow
- **Compact Value Items**: Reduced padding from 1rem to 0.8rem and font sizes
- **Smaller Image**: Reduced outro image max-width to 250px for better fit
- **Tighter Spacing**: Reduced gaps and margins throughout the layout

### Technical Changes
- **Value Grid**: Reduced max-width to 450px and gap to 0.8rem
- **Value Items**: Smaller padding (0.8rem), font sizes (1rem/0.8rem), and margins
- **Outro Image**: Reduced max-width to 250px with smaller shadow
- **Back Content**: Reduced padding to 1rem and gap to 1rem
- **Heading**: Reduced font size to 1.6rem and margin to 1rem

## [Updated] - Back Cover Image Removal and Alignment Focus

### Content Structure Changes
- **Removed Outro Image**: Eliminated the outro image to focus on content alignment
- **Centered Layout**: "Why Choose HeyZack?" content now centered on the entire back cover
- **Simplified Design**: Clean, text-only back cover for better alignment testing

### Layout Structure
- **Full Page Focus**: Content centered both horizontally and vertically
- **No Image Distractions**: Focus entirely on "Why Choose HeyZack?" alignment
- **Proper Centering**: Uses flexbox center alignment for perfect positioning

## [Updated] - Back Cover Content Positioning

### Layout Changes
- **Top Alignment**: Moved "Why Choose HeyZack?" content to the top of the back cover
- **Flex Start**: Changed from `align-items: center` to `align-items: flex-start`
- **Top Padding**: Increased top padding to 3rem for proper spacing from top edge
- **Horizontal Centering**: Maintained horizontal centering with `justify-content: center`

### Technical Changes
- **Back Content**: Changed alignment from center to flex-start
- **Top Spacing**: Added extra top padding (3rem) for proper positioning
- **Layout Focus**: Content now positioned at top for better visual hierarchy
