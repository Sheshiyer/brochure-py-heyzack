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
async def live_catalog(request: Request):
    """Live catalog that automatically updates when new products are added"""
    try:
        # Load products from JSON file
        with open("data/products.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        products = data.get("products", [])
        metadata = data.get("metadata", {})
        
        # Group products by category
        grouped_products = defaultdict(list)
        for product in products:
            category = product.get("category", "Uncategorized")
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
            
            grouped_products[category].append(formatted_product)
        
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

# PDF catalog endpoint
@app.get("/catalog/pdf")
async def generate_catalog_pdf(request: Request):
    """Generate and download PDF version of the live catalog with enhanced Windows compatibility"""
    try:
        # Load products from JSON file
        with open("data/products.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        products = data.get("products", [])
        metadata = data.get("metadata", {})
        
        # Group products by category
        grouped_products = defaultdict(list)
        for product in products:
            category = product.get("category", "Uncategorized")
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
            
            grouped_products[category].append(formatted_product)
        
        # Template context for PDF (similar to live catalog but without WebSocket elements)
        context = {
            "request": request,
            "company_info": {"name": "HeyZack"},
            "theme": "luxury-dark",
            "generation_date": datetime.now().strftime("%B %d, %Y"),
            "total_products": len(products),
            "categories": list(grouped_products.keys()),
            "grouped_products": dict(grouped_products)
        }
        
        # Generate filename with current date
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Try multiple PDF generation methods in order of preference
        pdf_methods = [
            "playwright_enhanced",
            "pyppeteer",
            "reportlab_enhanced"
        ]
        
        for method in pdf_methods:
            try:
                temp_pdf_path = await generate_pdf_with_method(method, context, request, grouped_products, products)
                if temp_pdf_path:
                    filename = f"HeyZack-Catalog-{date_str}.pdf"
                    
                    return FileResponse(
                        path=temp_pdf_path,
                        filename=filename,
                        media_type="application/pdf",
                        background=None
                    )
            except Exception as method_error:
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
    
    if method == "playwright_enhanced":
        # Enhanced Playwright implementation with better Windows compatibility
        try:
            # Detect Windows and adjust subprocess handling
            import platform
            is_windows = platform.system() == "Windows"
            
            # Create temporary PDF file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name
            
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
                
                if is_windows:
                    # Additional Windows-specific arguments
                    launch_args.extend([
                        '--single-process',
                        '--no-zygote',
                        '--disable-extensions',
                        '--disable-default-apps',
                        '--disable-sync',
                        '--no-default-browser-check'
                    ])
                
                browser = await p.chromium.launch(
                    headless=True,
                    args=launch_args,
                    timeout=60000  # Increased timeout for Windows
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
