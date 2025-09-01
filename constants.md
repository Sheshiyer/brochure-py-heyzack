# Development Constants & Branding Guidelines

*Critical constants that must remain consistent across multiple chat sessions and development teams.*

---

## 🎨 Brand Identity

### Company Information
- **Company Name**: HeyZack
- **Brand Colors**: 
  - Primary: Luxury Dark Theme
  - Secondary: Professional Blue (#1e40af)
  - Accent: Gold (#fbbf24)
- **Typography**: Modern, clean sans-serif fonts
- **Design Philosophy**: Luxury, professional, technology-focused

### Product Categories
- Security Cameras
- Smart Lighting
- Video Doorbells
- Smart Switches
- Home Automation
- Access Control

---

## 🔧 Technical Constants

### File Naming Conventions
```
# AI Generated Images
use-case-{model_id}.png
use-case-{model_id}.json

# Brochure Output
brochure_output.html
brochure_output.pdf

# Data Files
products_hierarchical_enhanced.json
SMART HOME FOLLOWING PROJECT - All Products.csv
```

### Directory Structure
```
brochure-py/
├── data/                    # Source data files
├── scripts/                 # Core processing scripts
├── brochure/               # Brochure generation engine
├── generated_images/       # AI-generated images output
├── constants.md            # This file
└── README.md              # Project documentation
```

### API Configuration
```python
# Google Gemini AI
GOOGLE_API_KEY = "your_google_gemini_api_key_here"
MODEL_NAME = "gemini-2.0-flash-exp"
IMAGE_RESOLUTION = "1024x1024"
OUTPUT_FORMAT = "PNG"

# S3 Configuration (Optional)
ENABLE_S3_UPLOAD = False  # Default: disabled
S3_BUCKET_NAME = "your-bucket-name"
S3_REGION = "us-east-1"
S3_PREFIX = "generated-images/"
```

---

## 📊 Data Standards

### Product Data Schema
```json
{
  "model_id": "string (unique identifier)",
  "product_name": "string",
  "category": "string (from approved categories)",
  "key_features": ["array of strings"],
  "specifications": {
    "key": "value pairs"
  },
  "usage_scenarios": ["array of use cases"]
}
```

### Image Metadata Schema
```json
{
  "model_id": "string",
  "image_path": "string",
  "generation_timestamp": "ISO 8601 datetime",
  "prompt_used": "string",
  "ai_model": "gemini-2.0-flash-exp",
  "s3_url": "string (optional)",
  "generation_status": "success|failed",
  "error_message": "string (if failed)"
}
```

---

## 🚀 Development Workflow Constants

### Git Branch Naming
```
feature/description-of-feature
bugfix/description-of-bug
hotfix/critical-issue
release/version-number
```

### Environment Variables
```bash
# Required for AI image generation
GOOGLE_API_KEY=your_google_gemini_api_key

# Optional for S3 upload
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# Optional for Google Sheets integration
GOOGLE_SHEETS_API_KEY=your_sheets_api_key
```

### Testing Standards
```python
# Test file naming
test_*.py
*_test.py

# Test categories
- Unit tests: Individual function testing
- Integration tests: API and service integration
- End-to-end tests: Complete workflow validation
```

---

## 📝 Documentation Standards

### Code Comments
```python
# Function documentation
def generate_ai_image(product_data: dict) -> dict:
    """
    Generate AI image using Google Gemini 2.5 Flash Image Preview.
    
    Args:
        product_data (dict): Product specifications and features
        
    Returns:
        dict: Generation result with image path and metadata
        
    Raises:
        APIError: When Google Gemini API fails
        ValidationError: When product data is invalid
    """
```

### README Structure
1. Project Overview
2. Quick Start Guide
3. Configuration Instructions
4. API Integration Details
5. Architecture Documentation
6. Performance Considerations
7. Error Handling
8. Integration Workflow

---

## 🔒 Security Guidelines

### API Key Management
- **NEVER** commit API keys to version control
- Use environment variables or secure configuration files
- Rotate keys regularly
- Use least-privilege access principles

### Data Privacy
- Product data may contain sensitive information
- Implement proper access controls
- Log access and modifications
- Follow data retention policies

### Error Handling
```python
# Standard error handling pattern
try:
    result = api_call()
except APIError as e:
    logger.error(f"API call failed: {e}")
    # Graceful degradation
except Exception as e:
    logger.critical(f"Unexpected error: {e}")
    # Fail safely
```

---

## 🎯 Quality Assurance

### Code Quality Standards
- **PEP 8** compliance for Python code
- **Type hints** for all function parameters and returns
- **Docstrings** for all public functions and classes
- **Error handling** for all external API calls
- **Logging** for all significant operations

### Performance Benchmarks
- AI image generation: < 30 seconds per image
- Batch processing: Handle 100+ products efficiently
- Memory usage: < 2GB for typical workloads
- S3 upload: < 10 seconds per image (when enabled)

### Success Metrics
- Image generation success rate: > 95%
- API error recovery: Automatic retry with exponential backoff
- Data integrity: 100% metadata preservation
- User experience: Clear error messages and progress indicators

---

## 📋 Deployment Checklist

### Pre-deployment
- [ ] All API keys configured
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Data files present in correct locations
- [ ] Output directories created
- [ ] Permissions set correctly

### Post-deployment
- [ ] Test image generation with sample products
- [ ] Verify local storage functionality
- [ ] Test S3 upload (if enabled)
- [ ] Check error logging
- [ ] Validate output file formats

---

## 🔄 Maintenance Schedule

### Weekly
- Review error logs
- Check API usage and quotas
- Validate generated image quality
- Update product data if needed

### Monthly
- Review and rotate API keys
- Update dependencies
- Performance optimization review
- Backup critical data

### Quarterly
- Architecture review
- Security audit
- Documentation updates
- Feature roadmap planning

---

*Last Updated: January 2025*
*Version: 1.0*
*Maintainer: Development Team*