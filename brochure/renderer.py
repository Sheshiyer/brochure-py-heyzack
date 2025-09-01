"""Brochure renderer for the HeyZack brochure generator."""

import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .parser import NormalizedProduct

logger = logging.getLogger(__name__)


class BrochureRenderer:
    """Renders brochures from normalized product data."""
    
    def __init__(self, theme: str = 'luxury-dark'):
        self.theme = theme
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / 'templates'
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Add custom filters
        self.jinja_env.filters['currency'] = self._format_currency
        self.jinja_env.filters['truncate_words'] = self._truncate_words
    
    def render_brochure(self, products: List[NormalizedProduct], 
                       output_dir: Path, 
                       layout_rules: Optional[Dict[str, Any]] = None) -> Path:
        """Render complete brochure.
        
        Args:
            products: List of normalized products
            output_dir: Output directory path
            layout_rules: Optional layout configuration
            
        Returns:
            Path to generated brochure HTML file
        """
        # Create output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy static assets
        self._copy_static_assets(output_dir)
        
        # Group products by category
        from .parser import ProductParser
        parser = ProductParser()
        grouped_products = parser.group_by_category(products)
        
        # Prepare template context with HeyZack branding
        context = {
            'products': products,
            'grouped_products': grouped_products,
            'total_products': len(products),
            'categories': list(grouped_products.keys()),
            'generation_date': datetime.now().strftime('%B %d, %Y'),
            'theme': self.theme,
            'layout_rules': layout_rules or {},
            'company_info': {
                'name': 'HeyZack AI Calling Agent',
                'tagline': 'Your Home, Smarter Than Ever',
                'mission': 'AI-powered smart home solutions designed for professionals and consumers',
                'description': 'Complete AI-powered smart home ecosystem that transforms how people interact with their living spaces.',
                'business_hours': {
                    'weekdays': 'Mon-Fri: 6 AM - 9 PM',
                    'saturday': 'Sat: 9 AM - 5 PM',
                    'sunday': 'Sun: 9 AM - 4 PM'
                },
                'value_props': [
                    'AI Guardian Technology - Proactive home management',
                    'Complete Integration - All devices work seamlessly together',
                    'Professional Support - Dedicated partner success program',
                    '30% Partner Margins - Industry-leading profitability'
                ],
                'partner_benefits': [
                    '2-3 additional installs per month',
                    'Free demo kits for approved partners',
                    'Pre-qualified leads delivered directly',
                    'Ultra-fast, professional-grade setup'
                ],
                'cta_options': [
                    'Schedule a 15-minute Zoom call for detailed discussion',
                    'Request email overview for self-paced review',
                    'Book demo kit for hands-on experience'
                ]
            }
        }
        
        # Render main brochure
        template = self.jinja_env.get_template('brochure.html')
        html_content = template.render(**context)
        
        # Write HTML file
        output_file = output_dir / 'brochure.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"Brochure rendered to {output_file}")
        return output_file
    
    def _copy_static_assets(self, output_dir: Path):
        """Copy CSS, JS, and other static assets to output directory."""
        static_dir = Path(__file__).parent / 'static'
        output_static_dir = output_dir / 'static'
        
        if static_dir.exists():
            if output_static_dir.exists():
                shutil.rmtree(output_static_dir)
            shutil.copytree(static_dir, output_static_dir)
            self.logger.info(f"Static assets copied to {output_static_dir}")
    
    def _get_company_info(self) -> Dict[str, str]:
        """Get HeyZack company information."""
        return {
            'name': 'HeyZack',
            'tagline': 'Smart Home Made Simple',
            'website': 'https://heyzack.com',
            'phone': '1-800-HEYZACK',
            'email': 'info@heyzack.com'
        }
    
    def _format_currency(self, value: float) -> str:
        """Format currency values."""
        try:
            return f"${value:,.2f}"
        except (ValueError, TypeError):
            return "$0.00"
    
    def _truncate_words(self, text: str, length: int = 50) -> str:
        """Truncate text to specified word count."""
        if not isinstance(text, str):
            return ''
        
        words = text.split()
        if len(words) <= length:
            return text
        
        return ' '.join(words[:length]) + '...'