#!/usr/bin/env python3
"""CLI interface for the HeyZack brochure generator."""

import click
import json
import logging
import sys
from pathlib import Path
from typing import Optional, List

from .parser import ProductParser
from .renderer import BrochureRenderer
from .pdf_generator import PDFGenerator
from .category_selector import select_categories_interactive
from .hierarchical_loader import HierarchicalProductLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option()
def cli():
    """HeyZack Dynamic HTML Brochure Generator
    
    Generate luxury-grade, print-ready HTML catalogues from product data.
    """
    pass


@cli.command()
@click.option('--src', default='data/products_hierarchical_enhanced.json', type=click.Path(exists=True), 
              help='Path to products directory, products.json file, or hierarchical JSON (default: data/products_hierarchical_enhanced.json)')
@click.option('--out', default='out', type=click.Path(), 
              help='Output directory (default: out)')
@click.option('--include', type=str, 
              help='Comma-separated list of models to include')
@click.option('--categories', type=str, 
              help='Comma-separated list of categories to include (for hierarchical data)')
@click.option('--rules', type=click.Path(exists=True), 
              help='Path to layout_rules.json file')
@click.option('--theme', default='luxury-dark', 
              help='Theme name (default: luxury-dark)')
@click.option('--pdf', is_flag=True, help='Generate PDF output in addition to HTML')
@click.option('--pdf-only', is_flag=True, help='Generate only PDF output (no HTML)')
@click.option('--pdf-method', default='weasyprint', type=click.Choice(['weasyprint', 'reportlab']), 
              help='PDF generation method')
@click.option('--interactive', '-i', is_flag=True,
              help='Interactive category selection before generating brochure')
def build(src: str, out: str, include: Optional[str], categories: Optional[str],
          rules: Optional[str], theme: str, pdf: bool, pdf_only: bool, pdf_method: str, interactive: bool):
    """Build brochure from products directory, products.json file, or hierarchical JSON."""
    try:
        # Parse input data
        src_path = Path(src)
        normalized_products = []
        
        # Check if this is a hierarchical JSON file
        if src_path.is_file() and src_path.name.endswith('.json'):
            try:
                with open(src_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Check if it's hierarchical format
                if 'categories' in data and 'metadata' in data:
                    logger.info(f"Loading products from hierarchical JSON: {src}")
                    
                    # Parse categories filter
                    include_categories = None
                    if categories:
                        include_categories = [cat.strip() for cat in categories.split(',')]
                        logger.info(f"Including only categories: {include_categories}")
                    
                    # Parse include filter
                    include_models = None
                    if include:
                        include_models = [model.strip() for model in include.split(',')]
                        logger.info(f"Including only models: {include_models}")
                    
                    # Load using hierarchical loader
                    loader = HierarchicalProductLoader()
                    normalized_products = loader.load_products(
                        str(src_path),
                        include_categories=include_categories,
                        include_models=include_models
                    )
                    
                    logger.info(f"Loaded {len(normalized_products)} products from hierarchical structure")
                    
                else:
                    # Fall back to legacy format
                    logger.info(f"Loading products from legacy JSON file: {src}")
                    products_data = data if isinstance(data, list) else [data]
                    
            except Exception as e:
                logger.error(f"Failed to load JSON file {src}: {e}")
                raise
                
        elif src_path.is_dir():
            # Load from directory of JSON files (legacy)
            logger.info(f"Loading products from directory {src}")
            json_files = list(src_path.glob('*.json'))
            logger.info(f"Found {len(json_files)} JSON files")
            
            products_data = []
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        product_data = json.load(f)
                        products_data.append(product_data)
                except Exception as e:
                    logger.warning(f"Failed to load {json_file}: {e}")
                    continue
        else:
            raise ValueError(f"Source path {src} is not a valid file or directory")
        
        # If we loaded legacy data, parse it with the old parser
        if not normalized_products and 'products_data' in locals():
            logger.info(f"Loaded {len(products_data)} products from legacy format")
            
            # Parse include filter
            include_models = None
            if include:
                include_models = [model.strip() for model in include.split(',')]
                logger.info(f"Including only models: {include_models}")
            
            # Parse and normalize products using legacy parser
            parser = ProductParser()
            normalized_products = parser.parse_products(
                products_data, 
                include_models=include_models
            )
        
        # Interactive category selection if requested
        if interactive:
            click.echo("\n🎯 Starting interactive category selection...")
            
            # For hierarchical data, implement category selection
            if src_path.is_file() and src_path.name.endswith('.json'):
                try:
                    with open(src_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if 'categories' in data and 'metadata' in data:
                        # Display available categories
                        categories_info = data['categories']
                        click.echo("\n📋 Available Categories:")
                        click.echo("-" * 50)
                        
                        category_list = []
                        for i, (cat_name, cat_data) in enumerate(sorted(categories_info.items()), 1):
                            product_count = len(cat_data.get('products', []))
                            click.echo(f"{i:2d}. {cat_name} ({product_count} products)")
                            category_list.append(cat_name)
                        
                        click.echo("\n0. Select All Categories")
                        
                        # Get user selection
                        while True:
                            try:
                                selection = click.prompt("\nEnter category numbers (comma-separated) or 0 for all", type=str)
                                
                                if selection.strip() == '0':
                                    selected_categories = None  # All categories
                                    click.echo("✅ Selected: All categories")
                                    break
                                else:
                                    # Parse comma-separated numbers
                                    indices = [int(x.strip()) for x in selection.split(',')]
                                    selected_categories = [category_list[i-1] for i in indices if 1 <= i <= len(category_list)]
                                    
                                    if selected_categories:
                                        click.echo(f"✅ Selected: {', '.join(selected_categories)}")
                                        # Update categories filter
                                        categories = ','.join(selected_categories)
                                        break
                                    else:
                                        click.echo("❌ Invalid selection. Please try again.")
                                        
                            except (ValueError, IndexError):
                                click.echo("❌ Invalid input. Please enter numbers separated by commas.")
                        
                        # Reload products with selected categories
                        if selected_categories:
                            loader = HierarchicalProductLoader()
                            normalized_products = loader.load_products(
                                str(src_path),
                                include_categories=selected_categories,
                                include_models=include_models
                            )
                            logger.info(f"Filtered to {len(normalized_products)} products from selected categories")
                        
                except Exception as e:
                    logger.error(f"Interactive selection failed: {e}")
                    click.echo(f"❌ Interactive selection failed: {e}", err=True)
            else:
                logger.warning("Interactive mode not yet implemented for non-hierarchical data")
        
        # Load layout rules if provided
        layout_rules = None
        if rules:
            logger.info(f"Loading layout rules from {rules}")
            with open(rules, 'r', encoding='utf-8') as f:
                layout_rules = json.load(f)
        
        logger.info(f"Parsed {len(normalized_products)} products")
        
        # Render HTML brochure (unless PDF-only)
        html_output = None
        if not pdf_only:
            renderer = BrochureRenderer(theme=theme)
            html_output = renderer.render_brochure(
                normalized_products,
                output_dir=Path(out),
                layout_rules=layout_rules
            )
            
            logger.info(f"HTML brochure generated successfully at {html_output}")
            click.echo(f"✅ HTML brochure built: {html_output}")
        
        # Generate PDF if requested
        if pdf or pdf_only:
            try:
                pdf_generator = PDFGenerator(method=pdf_method)
                
                if pdf_method == "weasyprint" and html_output:
                    # Generate PDF from HTML
                    pdf_output = str(Path(out) / "brochure.pdf")
                    pdf_generator.generate_pdf_from_html(html_output, pdf_output)
                    click.echo(f"✅ PDF brochure built: {pdf_output}")
                    
                elif pdf_method == "reportlab" or not html_output:
                    # Generate simple PDF using ReportLab
                    pdf_output = str(Path(out) / "brochure.pdf")
                    
                    # Convert products to simple format for ReportLab
                    products_data = []
                    for product in normalized_products:
                        products_data.append({
                            'name': product.name,
                            'model': product.model,
                            'category': product.category,
                            'price': product.price,
                            'status': product.status
                        })
                    
                    company_info = {
                        'name': 'HeyZack AI Calling Agent',
                        'tagline': 'Your Home, Smarter Than Ever',
                        'description': 'Complete AI-powered smart home ecosystem that transforms how people interact with their living spaces.'
                    }
                    
                    pdf_generator.generate_simple_pdf(products_data, pdf_output, company_info)
                    click.echo(f"✅ PDF brochure built: {pdf_output}")
                    
            except ImportError as e:
                logger.error(f"PDF generation failed: {e}")
                click.echo(f"❌ PDF Error: {e}", err=True)
                click.echo("💡 Install PDF dependencies: pip install weasyprint reportlab", err=True)
            except Exception as e:
                logger.error(f"PDF generation failed: {e}")
                click.echo(f"❌ PDF Error: {e}", err=True)
        
    except Exception as e:
        logger.error(f"Build failed: {e}")
        click.echo(f"❌ Build failed: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()