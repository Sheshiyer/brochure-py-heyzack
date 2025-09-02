from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import boto3, base64, uuid, asyncio, json
from botocore.exceptions import NoCredentialsError
from typing import List
import sys
import os
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add scripts directory to path for importing polling service
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
from automated_polling_service import AutomatedPollingService

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

# Callback function for polling service to notify of new products
async def notify_new_products(new_products: List[dict]):
    """Called by polling service when new products are detected"""
    notification = {
        "type": "new_products",
        "count": len(new_products),
        "products": new_products,
        "timestamp": new_products[0].get("metadata", {}).get("last_updated") if new_products else None
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
            spreadsheet_url="https://docs.google.com/spreadsheets/d/17xcmTsSZkguOjXC6h6YDrNcOU27jrpU8Ah9xEONARg8/edit?gid=86173031#gid=86173031",
            catalog_path="data/products.json",
            notification_callback=notify_new_products
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
                "supplier": product.get("supplier", ""),
                "primary_image": product.get("metadata", {}).get("drive_link", ""),
                "short_description": product.get("specifications", {}).get("description", "")[:200] + "..." if product.get("specifications", {}).get("description", "") else "",
                "features": []
            }
            
            # Extract features from specifications
            specs = product.get("specifications", {})
            features_text = specs.get("features", "")
            if features_text and features_text != "Feature":
                # Split by commas and clean up
                features_list = [f.strip() for f in features_text.split(",") if f.strip() and f.strip() != "Feature"]
                formatted_product["features"] = features_list[:10]  # Limit to 10 features
            
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
