from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import boto3, base64, uuid, asyncio, json, tempfile
from botocore.exceptions import NoCredentialsError
from typing import List
import sys
import os
import platform
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

# Windows-specific imports and compatibility handling
if platform.system() == "Windows":
    import subprocess
    # Set up Windows-compatible asyncio policy
    if sys.version_info >= (3, 8):
        try:
            from asyncio import WindowsProactorEventLoopPolicy
            asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy())
        except ImportError:
            pass

# Load environment variables from .env file
load_dotenv()

# Add scripts directory to path for importing polling service
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
from automated_polling_service import AutomatedPollingService

# Add brochure directory to path for PDF generation
sys.path.append(os.path.join(os.path.dirname(__file__), 'brochure'))
from pdf_generator import PDFGenerator
from playwright.async_api import async_playwright

# ---------------- CONFIG ----------------
AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET             = os.getenv("S3_BUCKET")
S3_REGION             = os.getenv("S3_REGION")

# Validate that all required environment variables are set
if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET, S3_REGION]):
    raise ValueError("Missing required AWS environment variables. Please check your .env file.")
# ----------------------------------------

# Initialize FastAPI app
app = FastAPI(title="HeyZack Product Catalog API")

# Setup templates and static files
templates = Jinja2Templates(directory="brochure/templates")
app.mount("/static", StaticFiles(directory="brochure/static"), name="static")

# Global polling service instance
polling_service = None
active_connections: List[WebSocket] = []

# Initialize boto3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=S3_REGION
)

# Define request body model
class UploadRequest(BaseModel):
    modelNumber: str
    imageBase64: str

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                # Remove broken connections
                self.disconnect(connection)

manager = ConnectionManager()

# Callback function for polling service to notify of product changes
async def notify_product_changes(change_data: dict):
    """Called by polling service when products are detected (new or modified)"""
    new_products = change_data.get("new_products", [])
    modified_products = change_data.get("modified_products", [])
    
    # Send notification for new products
    if new_products:
        notification = {
            "type": "new_products",
            "count": len(new_products),
            "products": [{"name": p["name"], "model": p.get("model"), "category": p.get("category")} for p in new_products],
            "timestamp": datetime.now().isoformat()
        }
        await manager.broadcast(notification)
    
    # Send notification for modified products
    if modified_products:
        notification = {
            "type": "modified_products",
            "count": len(modified_products),
            "products": [{"name": p["name"], "model": p.get("model"), "category": p.get("category")} for p in modified_products],
            "timestamp": datetime.now().isoformat()
        }
        await manager.broadcast(notification)
    
    # Send notification for deleted products
    deleted_products = change_data.get("deleted_products", [])
    if deleted_products:
        notification = {
            "type": "deleted_products",
            "count": len(deleted_products),
            "products": [{"name": p.get("name", "Unknown"), "model": p.get("model", "No model")} for p in deleted_products],
            "timestamp": datetime.now().isoformat()
        }
        await manager.broadcast(notification)

@app.post("/upload")
async def upload_image(req: UploadRequest):
    try:
        # Decode base64
        image_bytes = base64.b64decode(req.imageBase64)

        # File name
        file_name = f"{req.modelNumber}_{uuid.uuid4().hex}.jpg"

        # Upload to S3 (no ACL)
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=file_name,
            Body=image_bytes,
            ContentType="image/jpeg"
        )

        # Public URL (works because of bucket policy)
        s3_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{file_name}"

        return {"success": True, "s3Url": s3_url}

    except Exception as e:
        return {"success": False, "error": str(e)}

# Polling control endpoints
@app.post("/polling/start")
async def start_polling():
    """Start the automated polling service"""
    global polling_service
    try:
        if polling_service and polling_service.is_running:
            return {"success": False, "message": "Polling service is already running"}
        
        polling_service = AutomatedPollingService(
            spreadsheet_url="https://docs.google.com/spreadsheets/d/17xcmTsSZkguOjXC6h6YDrNcOU27jrpU8Ah9xEONARg8/edit?gid=1707985453#gid=1707985453",
            catalog_path="data/products.json",
            notification_callback=notify_product_changes
        )
        
        # Start polling in background
        asyncio.create_task(polling_service.start_polling())
        
        return {"success": True, "message": "Polling service started successfully"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/polling/stop")
async def stop_polling():
    """Stop the automated polling service"""
    global polling_service
    try:
        if not polling_service or not polling_service.is_running:
            return {"success": False, "message": "Polling service is not running"}
        
        await polling_service.stop_polling()
        return {"success": True, "message": "Polling service stopped successfully"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/polling/status")
async def get_polling_status():
    """Get current polling service status"""
    global polling_service
    try:
        if not polling_service:
            return {
                "running": False,
                "message": "Polling service not initialized",
                "stats": {}
            }
        
        stats = polling_service.get_status()
        return {
            "running": polling_service.is_running,
            "message": "Polling service active" if polling_service.is_running else "Polling service inactive",
            "stats": stats
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}

# WebSocket endpoint for real-time notifications
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            # Echo back for testing purposes
            await websocket.send_text(f"Server received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Live catalog endpoint that auto-updates
@app.get("/catalog", response_class=HTMLResponse)
async def live_catalog(request: Request, rows: str = None, category: str = None):
    """Live catalog that automatically updates when new products are added
    
    Args:
        rows: Comma-separated row numbers to filter products (e.g., "1,5,10,15")
              If not provided, shows all products
        category: Category name to filter products (e.g., "Smart Lighting", "Security")
                 If not provided, shows all categories
    """
    try:
        # Load products from JSON file
        with open("data/products.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        products = data.get("products", [])
        metadata = data.get("metadata", {})
        
        # Filter products by row numbers if specified
        if rows:
            try:
                # Parse comma-separated row numbers
                row_numbers = [int(row.strip()) for row in rows.split(',') if row.strip().isdigit()]
                print(f"Filtering products by row numbers: {row_numbers}")
                
                # Filter products based on row numbers (assuming products are in order)
                # Note: Row numbers are 1-based, so we need to subtract 1 for 0-based indexing
                filtered_products = []
                for row_num in row_numbers:
                    if 1 <= row_num <= len(products):
                        filtered_products.append(products[row_num - 1])
                    else:
                        print(f"Warning: Row number {row_num} is out of range (1-{len(products)})")
                
                products = filtered_products
                print(f"Filtered to {len(products)} products from {len(row_numbers)} row numbers")
                
            except ValueError as e:
                print(f"Error parsing row numbers '{rows}': {e}")
                # Continue with all products if parsing fails
        
        # Filter by category if specified
        if category:
            print(f"Filtering products by category: {category}")
            products = [p for p in products if p.get("category", "").lower() == category.lower()]
            print(f"Filtered to {len(products)} products in category '{category}'")
        
        # Group products by category
        grouped_products = defaultdict(list)
        for product in products:
            product_category = product.get("category", "Uncategorized")
            # Format product for template
            formatted_product = {
                "name": product.get("name", ""),
                "model": product.get("model", ""),
                "supplier": "Tuya",  # Default supplier
                "hero_image": product.get("hero_image", ""),
                "secondary_image": product.get("secondary_image", ""),
                "short_description": product.get("features", "")[:200] + "..." if product.get("features", "") else "",
                "specifications": product.get("specifications", ""),
                "features": []
            }
            
            # Extract features from features field
            features_text = product.get("features", "")
            if features_text and features_text.strip():
                # Split by newlines and clean up
                features_list = [f.strip() for f in features_text.split("\n") if f.strip()]
                # Remove numbers from the beginning of each feature (e.g., "1. " -> "")
                cleaned_features = []
                for feature in features_list:
                    # Remove pattern like "1. ", "2. ", etc. from the beginning
                    import re
                    cleaned_feature = re.sub(r'^\d+\.\s*', '', feature)
                    cleaned_features.append(cleaned_feature)
                formatted_product["features"] = cleaned_features[:10]  # Limit to 10 features
            
            grouped_products[product_category].append(formatted_product)
        
        # Template context
        context = {
            "request": request,
            "company_info": {"name": "HeyZack"},
            "theme": "luxury-dark",
            "generation_date": datetime.now().strftime("%B %d, %Y"),
            "total_products": len(products),
            "categories": list(grouped_products.keys()),
            "grouped_products": dict(grouped_products)
        }
        
        # Render template with WebSocket auto-refresh
        return templates.TemplateResponse("catalog_live.html", context)
        
    except Exception as e:
        return HTMLResponse(f"Error loading catalog: {str(e)}", status_code=500)

# Get available categories endpoint
@app.get("/catalog/categories")
async def get_categories():
    """Get list of available product categories"""
    try:
        # Load products from JSON file
        with open("data/products.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        products = data.get("products", [])
        
        # Extract unique categories
        categories = set()
        for product in products:
            category = product.get("category", "Uncategorized")
            if category and category.strip():
                categories.add(category)
        
        # Convert to sorted list
        categories_list = sorted(list(categories))
        
        return {
            "categories": categories_list,
            "total_categories": len(categories_list),
            "total_products": len(products)
        }
        
    except Exception as e:
        return {"error": f"Error loading categories: {str(e)}"}


# PDF catalog endpoint
@app.get("/catalog/pdf")
async def generate_catalog_pdf(request: Request, rows: str = None, category: str = None):
    """Generate and download PDF version of the live catalog with enhanced Windows compatibility
    
    Args:
        rows: Comma-separated row numbers to filter products (e.g., "1,5,10,15")
              If not provided, shows all products
        category: Category name to filter products (e.g., "Smart Lighting", "Security")
                 If not provided, shows all categories
    """
    try:
        # Load products from JSON file
        with open("data/products.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        products = data.get("products", [])
        metadata = data.get("metadata", {})
        
        # Filter products by row numbers if specified
        if rows:
            try:
                # Parse comma-separated row numbers
                row_numbers = [int(row.strip()) for row in rows.split(',') if row.strip().isdigit()]
                print(f"PDF: Filtering products by row numbers: {row_numbers}")
                
                # Filter products based on row numbers (assuming products are in order)
                # Note: Row numbers are 1-based, so we need to subtract 1 for 0-based indexing
                filtered_products = []
                for row_num in row_numbers:
                    if 1 <= row_num <= len(products):
                        filtered_products.append(products[row_num - 1])
                    else:
                        print(f"PDF: Warning: Row number {row_num} is out of range (1-{len(products)})")
                
                products = filtered_products
                print(f"PDF: Filtered to {len(products)} products from {len(row_numbers)} row numbers")
                
            except ValueError as e:
                print(f"PDF: Error parsing row numbers '{rows}': {e}")
                # Continue with all products if parsing fails
        
        # Filter by category if specified
        if category:
            print(f"PDF: Filtering products by category: {category}")
            products = [p for p in products if p.get("category", "").lower() == category.lower()]
            print(f"PDF: Filtered to {len(products)} products in category '{category}'")
        
        # Group products by category
        grouped_products = defaultdict(list)
        for product in products:
            product_category = product.get("category", "Uncategorized")
            # Format product for template
            formatted_product = {
                "name": product.get("name", ""),
                "model": product.get("model", ""),
                "supplier": "Tuya",  # Default supplier
                "hero_image": product.get("hero_image", ""),
                "secondary_image": product.get("secondary_image", ""),
                "short_description": product.get("features", "")[:200] + "..." if product.get("features", "") else "",
                "specifications": product.get("specifications", ""),
                "features": []
            }
            
            # Extract features from features field
            features_text = product.get("features", "")
            if features_text and features_text.strip():
                # Split by newlines and clean up
                features_list = [f.strip() for f in features_text.split("\n") if f.strip()]
                # Remove numbers from the beginning of each feature (e.g., "1. " -> "")
                cleaned_features = []
                for feature in features_list:
                    # Remove pattern like "1. ", "2. ", etc. from the beginning
                    import re
                    cleaned_feature = re.sub(r'^\d+\.\s*', '', feature)
                    cleaned_features.append(cleaned_feature)
                formatted_product["features"] = cleaned_features[:10]  # Limit to 10 features
            
            grouped_products[product_category].append(formatted_product)
        
        # Load font as base64 for PDF generation
        brinnan_font_base64 = ""
        font_path = "brochure/static/fonts/Brinnan Regular.otf"
        if os.path.exists(font_path):
            with open(font_path, 'rb') as font_file:
                brinnan_font_base64 = base64.b64encode(font_file.read()).decode('utf-8')
        
        # Load images as base64 for PDF generation
        intro_image_base64 = ""
        outer_image_base64 = ""
        
        intro_path = "brochure/static/images/intro.png"
        if os.path.exists(intro_path):
            with open(intro_path, 'rb') as img_file:
                intro_image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                print(f"Cover page image loaded: {len(intro_image_base64)} characters")
        else:
            print(f"Cover page image not found at: {intro_path}")
        
        outer_path = "brochure/static/images/outer.png"
        if os.path.exists(outer_path):
            with open(outer_path, 'rb') as img_file:
                outer_image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                print(f"Back cover image loaded: {len(outer_image_base64)} characters")
        else:
            print(f"Back cover image not found at: {outer_path}")
        
        # Convert product images to base64 for PDF generation
        import requests
        for product in products:
            # Convert hero image
            if product.get('hero_image') and product['hero_image'].startswith('http'):
                try:
                    print(f"Converting hero image to base64: {product['name']}")
                    response = requests.get(product['hero_image'], timeout=10)
                    if response.status_code == 200:
                        product['hero_image_base64'] = base64.b64encode(response.content).decode('utf-8')
                        print(f"Hero image converted: {product['name']} - {len(product['hero_image_base64'])} characters")
                    else:
                        print(f"Failed to download hero image: {product['name']} - Status: {response.status_code}")
                        product['hero_image_base64'] = ""
                except Exception as e:
                    print(f"Error converting hero image for {product['name']}: {e}")
                    product['hero_image_base64'] = ""
            else:
                product['hero_image_base64'] = ""
            
            # Convert secondary image
            if product.get('secondary_image') and product['secondary_image'].startswith('http'):
                try:
                    print(f"Converting secondary image to base64: {product['name']}")
                    response = requests.get(product['secondary_image'], timeout=10)
                    if response.status_code == 200:
                        product['secondary_image_base64'] = base64.b64encode(response.content).decode('utf-8')
                        print(f"Secondary image converted: {product['name']} - {len(product['secondary_image_base64'])} characters")
                    else:
                        print(f"Failed to download secondary image: {product['name']} - Status: {response.status_code}")
                        product['secondary_image_base64'] = ""
                except Exception as e:
                    print(f"Error converting secondary image for {product['name']}: {e}")
                    product['secondary_image_base64'] = ""
            else:
                product['secondary_image_base64'] = ""
        
        # Template context for PDF (similar to live catalog but without WebSocket elements)
        context = {
            "request": request,
            "company_info": {"name": "HeyZack"},
            "theme": "luxury-dark",
            "generation_date": datetime.now().strftime("%B %d, %Y"),
            "total_products": len(products),
            "categories": list(grouped_products.keys()),
            "grouped_products": dict(grouped_products),
            "brinnan_font_base64": brinnan_font_base64,
            "intro_image_base64": intro_image_base64,
            "outer_image_base64": outer_image_base64
        }
        
        # Generate filename with current date
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Try multiple PDF generation methods in order of preference
        # Prioritize browser-based methods that preserve the live catalog design
        pdf_methods = [
            "playwright_sync",      # Browser-based method for Windows
            "pyppeteer",           # Alternative browser method
            "reportlab_enhanced"   # Simple text fallback
        ]
        
        for method in pdf_methods:
            try:
                print(f"Trying PDF generation method: {method}")
                temp_pdf_path = await generate_pdf_with_method(method, context, request, grouped_products, products)
                if temp_pdf_path:
                    filename = f"HeyZack-Catalog-{date_str}.pdf"
                    print(f"PDF generated successfully using method: {method}")
                    
                    return FileResponse(
                        path=temp_pdf_path,
                        filename=filename,
                        media_type="application/pdf",
                        background=None
                    )
            except Exception as method_error:
                print(f"PDF generation method {method} failed: {str(method_error)}")
                # Suppress asyncio errors for cleaner logs
                import logging
                logging.getLogger('asyncio').setLevel(logging.WARNING)
                continue
        
        # If all methods fail, return error
        return HTMLResponse(
            "PDF generation failed with all available methods. Please try again or contact support.",
            status_code=500
        )
        
    except Exception as e:
        return HTMLResponse(f"Error generating PDF catalog: {str(e)}", status_code=500)


async def generate_pdf_with_method(method: str, context: dict, request: Request, grouped_products: dict, products: list):
    """Generate PDF using specified method with enhanced error handling"""
    
    if method == "playwright_sync":
        # Synchronous Playwright implementation optimized for Windows
        try:
            from playwright.sync_api import sync_playwright
            import threading
            
            # Create temporary PDF file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name
            
            def run_playwright():
                with sync_playwright() as p:
                    # Launch browser with Windows-optimized settings
                    browser = p.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-setuid-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-gpu',
                            '--disable-web-security',
                            '--single-process',
                            '--no-zygote'
                        ]
                    )
                    
                    try:
                        page = browser.new_page()
                        
                        # Set viewport for consistent rendering
                        page.set_viewport_size({"width": 1200, "height": 1600})
                        
                        # Create a temporary HTML file with the PDF template
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_html:
                            html_content = templates.get_template("catalog_pdf.html").render(**context)
                            temp_html.write(html_content)
                            temp_html_path = temp_html.name
                        
                        # Navigate to the temporary HTML file
                        page.goto(f"file://{temp_html_path}", wait_until="networkidle", timeout=30000)
                        
                        # Wait for content to load
                        try:
                            page.wait_for_selector('.product-page', timeout=10000)
                        except:
                            pass  # Continue even if selector not found
                        
                        page.wait_for_load_state("networkidle")
                        
                        # Load and inject the CSS file content
                        css_file_path = "brochure/static/css/luxury-dark.css"
                        if os.path.exists(css_file_path):
                            with open(css_file_path, 'r', encoding='utf-8') as css_file:
                                css_content = css_file.read()
                                # Inject the full CSS content
                                page.add_style_tag(content=css_content)
                                print(f"CSS injected: {len(css_content)} characters")
                        else:
                            print(f"CSS file not found at: {css_file_path}")
                        
                        # Wait for images to load
                        page.wait_for_load_state("networkidle")
                        import time
                        time.sleep(3)  # Extra wait for base64 images
                        
                        # Add additional CSS to hide live elements and optimize for PDF
                        page.add_style_tag(content="""
                            /* Hide live elements for PDF */
                            .live-indicator,
                            .notification,
                            .pdf-export-button,
                            #liveStatus,
                            #notification,
                            #pdfExport {
                                display: none !important;
                            }
                            
                            /* Optimize for PDF rendering */
                            body {
                                margin: 0;
                                padding: 0;
                                -webkit-print-color-adjust: exact;
                                print-color-adjust: exact;
                            }
                            
                            /* Ensure proper page breaks and full page usage */
                            .product-page {
                                page-break-after: always;
                                break-after: page;
                                margin: 0;
                                box-shadow: none !important;
                                height: 100vh;
                                width: 100%;
                                overflow: hidden;
                                display: block !important;
                            }
                            
                            /* Remove page break from last product to avoid extra white page */
                            .product-page:last-of-type {
                                page-break-after: auto;
                                break-after: auto;
                            }
                            
                            .cover-page {
                                page-break-after: always;
                                break-after: page;
                                margin: 0;
                                height: 100vh;
                                width: 100%;
                            }
                            
                            .back-cover-fixed {
                                page-break-before: always;
                                break-before: page;
                                margin: 0;
                                height: 100vh;
                                width: 100%;
                                background: linear-gradient(135deg, #333232 0%, #222222 50%, #1a1a1a 100%);
                                color: #ffffff;
                                display: flex;
                                align-items: center;
                                padding: 4rem;
                                overflow: hidden;
                            }
                            
                            .back-content-fixed {
                                max-width: 1200px;
                                margin: 0 auto;
                                display: grid;
                                grid-template-columns: 1fr 1fr;
                                gap: 4rem;
                                width: 100%;
                            }
                            
                            .company-section-fixed {
                                grid-column: 1 / -1;
                                margin-bottom: 3rem;
                            }
                            
                            .value-proposition h3 {
                                font-size: 1.5rem;
                                color: #ffffff;
                                margin-bottom: 2rem;
                            }
                            
                            .value-grid {
                                display: grid;
                                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                                gap: 1.5rem;
                            }
                            
                            .value-item {
                                padding: 1.5rem;
                                background: rgba(255, 255, 255, 0.05);
                                border-radius: 8px;
                                border: 1px solid rgba(232, 47, 137, 0.2);
                            }
                            
                            .value-item h4 {
                                font-size: 1.1rem;
                                color: #e82f89;
                                margin-bottom: 0.5rem;
                            }
                            
                            .value-item p {
                                font-size: 0.85rem;
                                color: #dddddd;
                                line-height: 1.4;
                            }
                            
                            .partner-section-fixed {
                                flex: 1;
                                display: flex;
                            }
                            
                            .partner-section-fixed img {
                                width: 100%;
                                height: 100%;
                                object-fit: cover;
                                border-radius: 0;
                                padding-top: 160px;
                            }
                            
                            /* Force structured layout to use full page */
                            .product-layout.layout-structured {
                                height: 100vh !important;
                                max-height: 100vh !important;
                                width: 100% !important;
                                overflow: hidden !important;
                                display: grid !important;
                                grid-template-rows: 30vh 70vh !important;
                                grid-template-columns: 1fr !important;
                            }
                            
                            .layout-structured .hero-section {
                                height: 30vh !important;
                                max-height: 30vh !important;
                                overflow: hidden !important;
                            }
                            
                            .layout-structured .details-section {
                                height: 70vh !important;
                                max-height: 70vh !important;
                                overflow: hidden !important;
                            }
                            
                            .layout-structured .left-column {
                                height: 100% !important;
                                overflow: hidden !important;
                                display: flex !important;
                                flex-direction: column !important;
                            }
                            
                            .layout-structured .right-column {
                                height: 100% !important;
                                overflow: hidden !important;
                            }
                            
                            /* Ensure content fits within page bounds */
                            .layout-structured .features {
                                flex: 1 !important;
                                overflow: hidden !important;
                                margin-bottom: 10px !important;
                            }
                            
                            .layout-structured .specifications {
                                flex: 1 !important;
                                overflow: hidden !important;
                                margin-bottom: 10px !important;
                            }
                            
                            .layout-structured .features-content,
                            .layout-structured .spec-content {
                                height: 100% !important;
                                overflow: hidden !important;
                            }
                            
                            .layout-structured .features-text,
                            .layout-structured .specifications-text {
                                font-size: 0.8em !important;
                                line-height: 1.3 !important;
                                max-height: 100% !important;
                                overflow: hidden !important;
                            }
                            
                            .layout-structured .features-list {
                                max-height: 100% !important;
                                overflow: hidden !important;
                            }
                            
                            .layout-structured .features-text {
                                font-size: 0.8em !important;
                                line-height: 1.3 !important;
                                color: #333 !important;
                                white-space: pre-wrap !important;
                                max-height: 100% !important;
                                overflow: hidden !important;
                            }
                            
                            /* Prevent content from breaking across pages */
                            .product-layout,
                            .hero-section,
                            .details-section,
                            .left-column,
                            .right-column,
                            .features,
                            .specifications,
                            .product-header {
                                page-break-inside: avoid !important;
                                break-inside: avoid !important;
                            }
                            
                            /* Ensure images render properly */
                            img {
                                max-width: 100%;
                                height: auto;
                                object-fit: contain;
                                -webkit-print-color-adjust: exact;
                                print-color-adjust: exact;
                            }
                        """)
                        
                        # Generate PDF with optimized settings
                        page.pdf(
                            path=temp_pdf_path,
                            format='A4',
                            print_background=True,
                            margin={
                                'top': '0mm',
                                'right': '0mm', 
                                'bottom': '0mm',
                                'left': '0mm'
                            },
                            prefer_css_page_size=True,
                            display_header_footer=False,
                            scale=1.0
                        )
                        
                    finally:
                        browser.close()
                        # Clean up temporary HTML file
                        if 'temp_html_path' in locals() and os.path.exists(temp_html_path):
                            os.unlink(temp_html_path)
            
            # Run in thread to avoid blocking async function
            thread = threading.Thread(target=run_playwright)
            thread.start()
            thread.join(timeout=60)  # 60 second timeout
            
            if thread.is_alive():
                raise Exception("Playwright PDF generation timed out")
            
            return temp_pdf_path
                    
        except Exception as e:
            # Clean up on failure
            if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
            raise e
    
    elif method == "playwright_enhanced":
        # Enhanced Playwright implementation with better Windows compatibility
        try:
            # Detect Windows and adjust subprocess handling
            import platform
            is_windows = platform.system() == "Windows"
            
            # Create temporary PDF file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name
            
            # Use synchronous approach for Windows compatibility
            if is_windows:
                from playwright.sync_api import sync_playwright
                
                with sync_playwright() as p:
                    # Enhanced browser launch arguments for Windows compatibility
                    launch_args = [
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--disable-gpu',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--run-all-compositor-stages-before-draw',
                        '--disable-background-timer-throttling',
                        '--disable-renderer-backgrounding',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-ipc-flooding-protection',
                        '--single-process',
                        '--no-zygote',
                        '--disable-extensions',
                        '--disable-default-apps',
                        '--disable-sync',
                        '--no-default-browser-check'
                    ]
                    
                    browser = p.chromium.launch(
                        headless=True,
                        args=launch_args
                    )
                    
                    try:
                        page = browser.new_page()
                        
                        # Set viewport for consistent rendering
                        page.set_viewport_size({"width": 1200, "height": 1600})
                        
                        # Navigate to live catalog URL
                        catalog_url = f"http://{request.url.netloc}/catalog"
                        page.goto(catalog_url, wait_until="networkidle", timeout=30000)
                        
                        # Wait for content to load
                        page.wait_for_selector('.product-page', timeout=15000)
                        page.wait_for_load_state("networkidle")
                        
                        # Enhanced CSS for PDF optimization
                        page.add_style_tag(content="""
                            /* Hide live elements for PDF */
                            .live-indicator,
                            .notification,
                            .pdf-export-button,
                            #liveStatus,
                            #notification,
                            #pdfExport {
                                display: none !important;
                            }
                            
                            /* Optimize for PDF rendering */
                            body {
                                margin: 0;
                                padding: 20px 0;
                                -webkit-print-color-adjust: exact;
                                print-color-adjust: exact;
                            }
                            
                            /* Ensure proper page breaks */
                            .product-page {
                                page-break-after: always;
                                break-after: page;
                                margin: 0 auto 20px auto;
                                box-shadow: none !important;
                            }
                            
                            .cover-page {
                                page-break-after: always;
                                break-after: page;
                                margin: 0 auto 20px auto;
                            }
                            
                            .back-cover-fixed {
                                page-break-before: always;
                                break-before: page;
                                margin: 20px auto 0 auto;
                            }
                            
                            /* Fix text rendering issues */
                            .spec-text, .product-description p {
                                text-rendering: optimizeLegibility;
                                -webkit-font-smoothing: antialiased;
                            }
                            
                            /* Ensure images render properly */
                            img {
                                max-width: 100%;
                                height: auto;
                                object-fit: contain;
                            }
                            
                            /* Fix grid layouts for PDF */
                            .spec-table.linear-layout,
                            .spec-table.left-right-layout {
                                grid-gap: 0.4rem 0.8rem;
                                align-items: start;
                            }
                        """)
                        
                        # Generate PDF with optimized settings
                        page.pdf(
                            path=temp_pdf_path,
                            format='A4',
                            print_background=True,
                            margin={
                                'top': '0mm',
                                'right': '0mm', 
                                'bottom': '0mm',
                                'left': '0mm'
                            },
                            prefer_css_page_size=True,
                            display_header_footer=False,
                            scale=1.0
                        )
                        
                        return temp_pdf_path
                        
                    finally:
                        browser.close()
            else:
                # Async approach for non-Windows systems
                async with async_playwright() as p:
                    # Enhanced browser launch arguments for Windows compatibility
                    launch_args = [
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--disable-gpu',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--run-all-compositor-stages-before-draw',
                        '--disable-background-timer-throttling',
                        '--disable-renderer-backgrounding',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-ipc-flooding-protection',
                    ]
                    
                    browser = await p.chromium.launch(
                        headless=True,
                        args=launch_args,
                        timeout=60000
                    )
                
                try:
                    page = await browser.new_page()
                    
                    # Set viewport for consistent rendering
                    await page.set_viewport_size({"width": 1200, "height": 1600})
                    
                    # Navigate to live catalog URL with retries
                    catalog_url = f"http://{request.url.netloc}/catalog"
                    max_retries = 3
                    
                    for attempt in range(max_retries):
                        try:
                            await page.goto(catalog_url, wait_until="networkidle", timeout=30000)
                            break
                        except Exception as nav_error:
                            if attempt == max_retries - 1:
                                raise nav_error
                            await asyncio.sleep(2)
                    
                    # Wait for content to load with multiple selectors
                    selectors_to_wait = ['.product-page', '.cover-page', '.back-cover']
                    for selector in selectors_to_wait:
                        try:
                            await page.wait_for_selector(selector, timeout=15000)
                        except:
                            pass  # Continue if selector not found
                    
                    # Additional wait for images to load
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)  # Extra buffer for slow loading images
                    
                    # Enhanced CSS for PDF optimization
                    await page.add_style_tag(content="""
                        /* Hide live elements for PDF */
                        .live-indicator,
                        .notification,
                        .pdf-export-button,
                        #liveStatus,
                        #notification,
                        #pdfExport {
                            display: none !important;
                        }
                        
                        /* Optimize for PDF rendering */
                        body {
                            margin: 0;
                            padding: 20px 0;
                            -webkit-print-color-adjust: exact;
                            print-color-adjust: exact;
                        }
                        
                        /* Ensure proper page breaks */
                        .product-page {
                            page-break-after: always;
                            break-after: page;
                            margin: 0 auto 20px auto;
                            box-shadow: none !important;
                        }
                        
                        .cover-page {
                            page-break-after: always;
                            break-after: page;
                            margin: 0 auto 20px auto;
                        }
                        
                        .back-cover {
                            page-break-before: always;
                            break-before: page;
                            margin: 20px auto 0 auto;
                        }
                        
                        /* Fix text rendering issues */
                        .spec-text, .product-description p {
                            text-rendering: optimizeLegibility;
                            -webkit-font-smoothing: antialiased;
                        }
                        
                        /* Ensure images render properly */
                        img {
                            max-width: 100%;
                            height: auto;
                            object-fit: contain;
                        }
                        
                        /* Fix grid layouts for PDF */
                        .spec-table.linear-layout,
                        .spec-table.left-right-layout {
                            grid-gap: 0.4rem 0.8rem;
                            align-items: start;
                        }
                    """)
                    
                    # Generate PDF with optimized settings
                    await page.pdf(
                        path=temp_pdf_path,
                        format='A4',
                        print_background=True,
                        margin={
                            'top': '10mm',
                            'right': '10mm', 
                            'bottom': '10mm',
                            'left': '10mm'
                        },
                        prefer_css_page_size=True,
                        display_header_footer=False,
                        scale=0.95  # Slightly smaller scale for better fit
                    )
                    
                    return temp_pdf_path
                    
                finally:
                    await browser.close()
                    
        except Exception as e:
            # Clean up on failure
            if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
            raise e
    
    elif method == "pyppeteer":
        # Pyppeteer as alternative (often works better on Windows)
        try:
            import pyppeteer
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name
            
            browser = await pyppeteer.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--single-process'
                ]
            )
            
            try:
                page = await browser.newPage()
                await page.setViewport({'width': 1200, 'height': 1600})
                
                catalog_url = f"http://{request.url.netloc}/catalog"
                await page.goto(catalog_url, {'waitUntil': 'networkidle0'})
                
                await page.pdf({
                    'path': temp_pdf_path,
                    'format': 'A4',
                    'printBackground': True,
                    'margin': {
                        'top': '10mm',
                        'right': '10mm',
                        'bottom': '10mm',
                        'left': '10mm'
                    }
                })
                
                return temp_pdf_path
                
            finally:
                await browser.close()
                
        except ImportError:
            # Pyppeteer not installed, skip this method
            raise Exception("Pyppeteer not available")
        except Exception as e:
            if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
            raise e
    
    elif method == "weasyprint_enhanced":
        # WeasyPrint implementation using dedicated PDF template
        try:
            import weasyprint
            from weasyprint import HTML, CSS
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name
            
            # Create a temporary HTML file with the PDF template
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_html:
                # Render the dedicated PDF template
                html_content = templates.get_template("catalog_pdf.html").render(**context)
                temp_html.write(html_content)
                temp_html_path = temp_html.name
            
            try:
                # Generate PDF with WeasyPrint
                html_doc = HTML(filename=temp_html_path)
                
                # Load the CSS file
                css_file = "brochure/static/css/luxury-dark.css"
                if os.path.exists(css_file):
                    css_doc = CSS(filename=css_file)
                    html_doc.write_pdf(temp_pdf_path, stylesheets=[css_doc])
                else:
                    html_doc.write_pdf(temp_pdf_path)
                
                return temp_pdf_path
                
            finally:
                # Clean up temporary HTML file
                if os.path.exists(temp_html_path):
                    os.unlink(temp_html_path)
                    
        except ImportError:
            raise Exception("WeasyPrint not available")
        except Exception as e:
            if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
            raise e
    
    elif method == "reportlab_enhanced":
        # Enhanced ReportLab fallback that better matches live design
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm, inch
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name
            
            # Create PDF document
            doc = SimpleDocTemplate(
                temp_pdf_path,
                pagesize=A4,
                rightMargin=15*mm,
                leftMargin=15*mm,
                topMargin=15*mm,
                bottomMargin=15*mm
            )
            
            # Enhanced styles that mimic the live catalog
            styles = getSampleStyleSheet()
            
            # Custom styles matching live catalog
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=12,
                textColor=colors.Color(0.91, 0.18, 0.54),  # #e82f89
                fontName='Helvetica-Bold',
                alignment=TA_CENTER
            )
            
            product_title_style = ParagraphStyle(
                'ProductTitle',
                parent=styles['Heading2'],
                fontSize=18,
                spaceAfter=6,
                textColor=colors.black,
                fontName='Helvetica-Bold'
            )
            
            description_style = ParagraphStyle(
                'Description',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=8,
                textColor=colors.Color(0.2, 0.2, 0.2),
                fontName='Helvetica'
            )
            
            feature_style = ParagraphStyle(
                'Feature',
                parent=styles['Normal'],
                fontSize=9,
                spaceAfter=3,
                leftIndent=15,
                textColor=colors.Color(0.13, 0.13, 0.13),
                fontName='Helvetica'
            )
            
            story = []
            
            # Cover page
            story.append(Spacer(1, 60*mm))
            story.append(Paragraph("HeyZack", title_style))
            story.append(Spacer(1, 10*mm))
            story.append(Paragraph("Your Home, Smarter Than Ever", styles['Heading3']))
            story.append(Spacer(1, 20*mm))
            story.append(Paragraph(f"Product Catalog - {context['generation_date']}", styles['Normal']))
            story.append(Paragraph(f"{context['total_products']} Products across {len(context['categories'])} Categories", styles['Normal']))
            story.append(PageBreak())
            
            # Product pages
            product_count = 1
            for category, category_products in grouped_products.items():
                for product in category_products:
                    # Product title and basic info
                    story.append(Paragraph(f"{product_count:02d}. {product['name']}", product_title_style))
                    if product['model']:
                        story.append(Paragraph(f"Model: {product['model']}", styles['Normal']))
                    story.append(Spacer(1, 5*mm))
                    
                    # Description
                    if product['short_description']:
                        story.append(Paragraph("Description:", styles['Heading4']))
                        story.append(Paragraph(product['short_description'], description_style))
                        story.append(Spacer(1, 5*mm))
                    
                    # Features
                    if product['features']:
                        story.append(Paragraph("Key Features:", styles['Heading4']))
                        for feature in product['features'][:15]:  # Limit features for space
                            story.append(Paragraph(f"• {feature}", feature_style))
                        story.append(Spacer(1, 5*mm))
                    
                    # Supplier info
                    if product['supplier']:
                        story.append(Paragraph(f"Supplier: {product['supplier']}", styles['Normal']))
                    
                    story.append(Spacer(1, 10*mm))
                    story.append(PageBreak())
                    
                    product_count += 1
            
            # Back cover
            story.append(Spacer(1, 40*mm))
            story.append(Paragraph("HeyZack AI Calling Agent", title_style))
            story.append(Spacer(1, 10*mm))
            story.append(Paragraph("Complete AI-powered smart home ecosystem", styles['Normal']))
            story.append(Spacer(1, 20*mm))
            story.append(Paragraph(f"Generated on {context['generation_date']}", styles['Normal']))
            
            # Build PDF
            doc.build(story)
            
            return temp_pdf_path
            
        except Exception as e:
            if 'temp_pdf_path' in locals() and os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
            raise e
    
    return None

# Simple dashboard endpoint for testing
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Simple dashboard to monitor polling status"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>HeyZack Product Catalog Monitor</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .status { padding: 20px; border-radius: 5px; margin: 10px 0; }
            .running { background-color: #d4edda; border-color: #c3e6cb; }
            .stopped { background-color: #f8d7da; border-color: #f5c6cb; }
            .button { padding: 10px 20px; margin: 5px; cursor: pointer; }
            .logs { background: #f8f9fa; padding: 15px; border-radius: 5px; height: 300px; overflow-y: scroll; }
            .catalog-link { background: #007bff; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; display: inline-block; margin: 10px 5px; }
        </style>
    </head>
    <body>
        <h1>Product Catalog Monitor</h1>
        <div id="status" class="status"></div>
        
        <div>
            <button class="button" onclick="startPolling()">Start Polling</button>
            <button class="button" onclick="stopPolling()">Stop Polling</button>
            <button class="button" onclick="getStatus()">Refresh Status</button>
            <a href="/catalog" class="catalog-link" target="_blank">View Live Catalog</a>
            <a href="/catalog?rows=1,5,10" class="catalog-link" target="_blank">View Rows 1,5,10</a>
        </div>
        
        <h3>Real-time Updates</h3>
        <div id="logs" class="logs"></div>
        
        <script>
            const ws = new WebSocket("ws://localhost:8000/ws");
            
            ws.onmessage = function(event) {
                const logs = document.getElementById('logs');
                const data = JSON.parse(event.data);
                
                if (data.type === 'new_products') {
                    logs.innerHTML += `<div><strong>${new Date().toLocaleTimeString()}</strong>: ${data.count} new products detected! Catalog will auto-refresh.</div>`;
                } else if (data.type === 'modified_products') {
                    logs.innerHTML += `<div><strong>${new Date().toLocaleTimeString()}</strong>: ${data.count} products updated! Catalog will auto-refresh.</div>`;
                } else if (data.type === 'deleted_products') {
                    logs.innerHTML += `<div><strong>${new Date().toLocaleTimeString()}</strong>: ${data.count} products deleted! Catalog will auto-refresh.</div>`;
                } else {
                    logs.innerHTML += `<div>${new Date().toLocaleTimeString()}: ${event.data}</div>`;
                }
                logs.scrollTop = logs.scrollHeight;
            };
            
            async function startPolling() {
                const response = await fetch('/polling/start', { method: 'POST' });
                const result = await response.json();
                alert(result.message || result.error);
                getStatus();
            }
            
            async function stopPolling() {
                const response = await fetch('/polling/stop', { method: 'POST' });
                const result = await response.json();
                alert(result.message || result.error);
                getStatus();
            }
            
            async function getStatus() {
                const response = await fetch('/polling/status');
                const result = await response.json();
                
                const statusDiv = document.getElementById('status');
                statusDiv.className = 'status ' + (result.running ? 'running' : 'stopped');
                statusDiv.innerHTML = `
                    <h3>Status: ${result.running ? 'RUNNING' : 'STOPPED'}</h3>
                    <p>${result.message}</p>
                    ${result.stats ? `
                        <p>Last Check: ${result.stats.last_check || 'Never'}</p>
                        <p>Total Checks: ${result.stats.total_checks || 0}</p>
                        <p>Products Added: ${result.stats.products_added || 0}</p>
                        <p>Products Modified: ${result.stats.products_modified || 0}</p>
                        <p>Products Deleted: ${result.stats.products_deleted || 0}</p>
                    ` : ''}
                `;
            }
            
            // Load status on page load
            getStatus();
        </script>
    </body>
    </html>
    """
    return html_content
