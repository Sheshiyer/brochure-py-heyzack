# HeyZack Dynamic HTML Brochure Generator

A deterministic Python brochure generator that composes luxury-grade, print-ready HTML + CSS catalogues from products.json files.

## Features

- **Deterministic Output**: Same input always produces identical results
- **Luxury Design**: Professional dark theme with gold accents
- **Responsive Layout**: Works on desktop, tablet, and mobile devices
- **Print-Ready**: Optimized CSS for high-quality printing
- **Interactive Features**: Search, smooth scrolling, and accessibility support
- **Flexible Filtering**: Include/exclude products by model
- **Category Organization**: Automatic grouping by product categories

## Project Structure

```
brochure-py/
├── brochure/              # Main application package
│   ├── cli.py            # Command-line interface
│   ├── hierarchical_loader.py  # Data loading
│   ├── parser.py         # Product parsing
│   ├── renderer.py       # HTML rendering
│   ├── pdf_generator.py  # PDF generation
│   └── templates/        # HTML templates
├── data/                 # Product data files
│   ├── products_hierarchical_enhanced_v2.json
│   ├── products.json
│   └── *.csv            # Raw data files
├── scripts/              # Analysis and utility scripts
│   ├── analyze_specifications.py
│   ├── enhance_specifications.py
│   └── fix_missing_data.py
├── reports/              # Analysis reports
│   ├── metadata_enhancement_summary.md
│   ├── drive_link_strategy_summary.md
│   └── memory.md        # Project history
├── docs/                 # Documentation
│   └── PRD.md           # Product requirements
├── out/                  # Generated output
│   ├── brochure.html
│   └── brochure.pdf
└── main.py              # Entry point
```

## Installation

1. **Clone or download the project**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

Generate a brochure from your products data:

```bash
# Use the enhanced hierarchical data (default)
python main.py build

# Or specify a different data file
python main.py build --src data/products.json
```

This creates an `out/` directory with:
- `brochure.html` - Main brochure file
- `static/` - CSS and JavaScript assets

### Advanced Options

```bash
# Specify output directory
python main.py build --out my-catalog

# Include only specific categories
python main.py build --categories "Video Door Bell,Smart Lock"

# Include only specific models
python main.py build --include "Model-A,Model-B,Model-C"

# Generate PDF output
python main.py build --pdf

# Interactive category selection
python main.py build --interactive
```

### CLI Help

```bash
python main.py --help
python main.py build --help
```

## Input Format

The generator expects a JSON file with an array of product objects:

```json
[
  {
    "id": "1",
    "name": "Smart Thermostat Pro",
    "model": "ST-PRO-001",
    "supplier": "TechCorp",
    "category": "Climate Control",
    "price": 299.99,
    "status": "active",
    "images": ["https://example.com/image1.jpg"],
    "specifications": {
      "description": "Advanced smart thermostat with AI learning",
      "specifications": {
        "connectivity": "WiFi, Bluetooth",
        "display": "3.5 inch touchscreen"
      },
      "features": [
        "AI-powered temperature learning",
        "Remote control via mobile app",
        "Energy usage analytics"
      ]
    }
  }
]
```

## Output Structure

```
out/
├── brochure.html          # Main brochure file
└── static/
    ├── css/
    │   └── luxury-dark.css   # Theme styles
    └── js/
        └── brochure.js       # Interactive features
```

## Themes

Currently available themes:
- `luxury-dark` (default) - Dark background with gold accents

## Layout Rules

Optional `layout_rules.json` file for customization:

```json
{
  "products_per_row": 3,
  "show_prices": true,
  "max_features": 4,
  "image_aspect_ratio": "16:9"
}
```

## Browser Compatibility

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Print Optimization

- Automatic page breaks between categories
- High-contrast colors for printing
- Expanded content (no truncation)
- Optimized margins and spacing

## Accessibility Features

- Keyboard navigation support
- Screen reader compatibility
- High contrast ratios
- Skip-to-content links
- Semantic HTML structure

## Development

### Project Structure

```
brochure-py/
├── brochure/
│   ├── __init__.py
│   ├── cli.py              # Command-line interface
│   ├── parser.py           # Product data parsing
│   ├── renderer.py         # HTML rendering
│   ├── templates/
│   │   └── brochure.html   # Main template
│   └── static/
│       ├── css/
│       │   └── luxury-dark.css
│       └── js/
│           └── brochure.js
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
└── README.md              # This file
```

### Adding New Themes

1. Create a new CSS file in `brochure/static/css/`
2. Follow the CSS custom properties pattern
3. Test with sample data
4. Update theme options in CLI

## Troubleshooting

### Common Issues

**Missing images**: Images that fail to load will show placeholder initials

**Large files**: For catalogs with 1000+ products, consider filtering by category

**Print issues**: Use Chrome or Firefox for best print results

### Error Messages

- `Build failed: [Errno 2] No such file or directory`: Check that your products.json file exists
- `Invalid JSON`: Validate your JSON syntax using an online validator
- `No products found`: Check that your JSON contains a valid array of products

## License

Copyright © 2025 HeyZack. All rights reserved.