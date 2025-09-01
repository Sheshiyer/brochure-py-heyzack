"""PDF generation functionality for HeyZack brochures."""

import logging
import os
from pathlib import Path
from typing import Optional
import importlib.util

# Don't import weasyprint at module level to avoid system dependency issues
WEASYPRINT_AVAILABLE = False
REPORTLAB_AVAILABLE = False

# Check availability without importing
try:
    if importlib.util.find_spec("weasyprint") is not None:
        WEASYPRINT_AVAILABLE = True
except ImportError:
    pass

try:
    if importlib.util.find_spec("reportlab") is not None:
        REPORTLAB_AVAILABLE = True
except ImportError:
    pass

if not WEASYPRINT_AVAILABLE:
    logging.warning("WeasyPrint not available. PDF generation will be disabled.")
if not REPORTLAB_AVAILABLE:
    logging.warning("ReportLab not available. Alternative PDF generation will be disabled.")

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Handles PDF generation from HTML brochures."""
    
    def __init__(self, method: str = "weasyprint"):
        """Initialize PDF generator.
        
        Args:
            method: PDF generation method ('weasyprint' or 'reportlab')
        """
        self.method = method
        self._validate_dependencies()
    
    def _validate_dependencies(self):
        """Validate that required dependencies are available."""
        if self.method == "weasyprint" and not WEASYPRINT_AVAILABLE:
            raise ImportError(
                "WeasyPrint is required for PDF generation. "
                "Install with: pip install weasyprint"
            )
        elif self.method == "reportlab" and not REPORTLAB_AVAILABLE:
            raise ImportError(
                "ReportLab is required for PDF generation. "
                "Install with: pip install reportlab"
            )
    
    def generate_pdf_from_html(self, html_file: str, output_file: str, 
                              base_url: Optional[str] = None) -> str:
        """Generate PDF from HTML file using WeasyPrint.
        
        Args:
            html_file: Path to HTML file
            output_file: Path for output PDF
            base_url: Base URL for resolving relative paths
            
        Returns:
            Path to generated PDF file
        """
        if self.method != "weasyprint":
            raise ValueError("This method requires WeasyPrint")
        
        logger.info(f"Generating PDF from {html_file} using WeasyPrint")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Set base URL if not provided
        if base_url is None:
            base_url = Path(html_file).resolve().parent.as_uri()
        
        try:
            # Import weasyprint only when needed
            import weasyprint
            
            # Generate PDF with WeasyPrint
            html_doc = weasyprint.HTML(filename=html_file, base_url=base_url)
            css_files = self._get_css_files(html_file)
            
            # Apply CSS stylesheets
            css_objects = []
            for css_file in css_files:
                if os.path.exists(css_file):
                    css_objects.append(weasyprint.CSS(filename=css_file))
            
            # Generate PDF with print-optimized settings
            html_doc.write_pdf(
                output_file,
                stylesheets=css_objects,
                optimize_images=True,
                presentational_hints=True
            )
            
            logger.info(f"PDF generated successfully: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise
    
    def _get_css_files(self, html_file: str) -> list:
        """Get CSS files associated with the HTML file."""
        html_dir = Path(html_file).parent
        css_files = []
        
        # Look for common CSS file locations
        possible_css_paths = [
            html_dir / "static" / "css" / "luxury-dark.css",
            html_dir / "css" / "luxury-dark.css",
            html_dir / "luxury-dark.css"
        ]
        
        for css_path in possible_css_paths:
            if css_path.exists():
                css_files.append(str(css_path))
        
        return css_files
    
    def generate_simple_pdf(self, products_data: list, output_file: str, 
                           company_info: dict) -> str:
        """Generate a simple PDF using ReportLab (fallback method).
        
        Args:
            products_data: List of product dictionaries
            output_file: Path for output PDF
            company_info: Company information dictionary
            
        Returns:
            Path to generated PDF file
        """
        if self.method != "reportlab":
            raise ValueError("This method requires ReportLab")
        
        logger.info(f"Generating simple PDF using ReportLab: {output_file}")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        try:
            # Import reportlab only when needed
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            
            # Create PDF document
            doc = SimpleDocTemplate(output_file, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Add title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                textColor=colors.HexColor('#1a1a1a'),
                alignment=1  # Center alignment
            )
            
            story.append(Paragraph(company_info.get('name', 'HeyZack'), title_style))
            story.append(Paragraph(company_info.get('tagline', 'Smart Home Solutions'), styles['Heading2']))
            story.append(Spacer(1, 20))
            
            # Add product summary
            summary_style = styles['Normal']
            story.append(Paragraph(f"Product Catalog - {len(products_data)} Products", styles['Heading3']))
            story.append(Spacer(1, 12))
            
            # Group products by category
            categories = {}
            for product in products_data:
                category = product.get('category', 'Other')
                if category not in categories:
                    categories[category] = []
                categories[category].append(product)
            
            # Add products by category
            for category, products in categories.items():
                story.append(Paragraph(f"{category} ({len(products)} products)", styles['Heading4']))
                
                # Create table data
                table_data = [['Product', 'Model', 'Price', 'Status']]
                
                for product in products[:10]:  # Limit to first 10 products per category
                    table_data.append([
                        product.get('name', 'N/A')[:30],  # Truncate long names
                        product.get('model', 'N/A')[:20],
                        f"€{product.get('price', 0):.2f}",
                        product.get('status', 'N/A')
                    ])
                
                # Create and style table
                table = Table(table_data, colWidths=[2.5*inch, 1.5*inch, 1*inch, 1*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d4af37')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(table)
                story.append(Spacer(1, 20))
            
            # Add footer information
            story.append(Spacer(1, 30))
            story.append(Paragraph("Company Information", styles['Heading3']))
            story.append(Paragraph(company_info.get('description', ''), styles['Normal']))
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"Simple PDF generated successfully: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Failed to generate simple PDF: {e}")
            raise
    
    @staticmethod
    def is_available(method: str = "weasyprint") -> bool:
        """Check if PDF generation is available.
        
        Args:
            method: PDF generation method to check
            
        Returns:
            True if the method is available
        """
        if method == "weasyprint":
            return WEASYPRINT_AVAILABLE
        elif method == "reportlab":
            return REPORTLAB_AVAILABLE
        return False