import json
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import time

@dataclass
class OpenRouterConfig:
    api_key: str
    model_id: str
    base_url: str = "https://openrouter.ai/api/v1"

class OpenRouterClient:
    def __init__(self, config: OpenRouterConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/brochure-py",
            "X-Title": "Brochure Technical Specs Enhancer"
        })
    
    def enhance_specifications(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance product specifications using AI."""
        try:
            # Extract current specifications
            current_specs = product_data.get('specifications', [])
            description = product_data.get('description', '')
            name = product_data.get('name', '')
            category = product_data.get('category', '')
            
            # Create enhancement prompt
            prompt = self._create_enhancement_prompt(name, category, description, current_specs)
            
            # Call OpenRouter API
            response = self._make_api_call(prompt)
            
            if response:
                # Parse and apply enhancements
                enhanced_data = self._parse_enhancement_response(response, product_data)
                return enhanced_data
            
            return product_data
            
        except Exception as e:
            print(f"Error enhancing specifications for {product_data.get('name', 'unknown')}: {e}")
            return product_data
    
    def _create_enhancement_prompt(self, name: str, category: str, description: str, specs: List[str]) -> str:
        """Create a structured prompt for specification enhancement."""
        current_specs_text = "\n".join([f"- {spec}" for spec in specs]) if specs else "No specifications provided"
        
        prompt = f"""You are a technical specification expert. Enhance the following product specifications:

Product: {name}
Category: {category}
Current Description: {description}

Current Specifications:
{current_specs_text}

Tasks:
1. Fix any technical inaccuracies or unclear specifications
2. Add missing relevant technical specifications for this product category
3. Ensure all specifications use proper pipe-separated format (Feature|Value)
4. Provide a more detailed and accurate product description
5. Maintain consistency with the product category and name

Return your response in this exact JSON format:
{{
  "enhanced_description": "Improved product description here",
  "enhanced_specifications": [
    "Feature 1|Value 1",
    "Feature 2|Value 2",
    "Feature 3|Value 3"
  ],
  "corrections_made": [
    "Description of correction 1",
    "Description of correction 2"
  ]
}}

Ensure all specifications are technically accurate and relevant to {category} products."""
        
        return prompt
    
    def _make_api_call(self, prompt: str) -> Optional[str]:
        """Make API call to OpenRouter."""
        try:
            payload = {
                "model": self.config.model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            }
            
            response = self.session.post(
                f"{self.config.base_url}/chat/completions",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                print(f"API call failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"API call error: {e}")
            return None
    
    def _parse_enhancement_response(self, response: str, original_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AI response and apply enhancements."""
        try:
            # Extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                enhancement_data = json.loads(json_str)
                
                # Apply enhancements to original data
                enhanced_data = original_data.copy()
                
                if 'enhanced_description' in enhancement_data:
                    enhanced_data['description'] = enhancement_data['enhanced_description']
                
                if 'enhanced_specifications' in enhancement_data:
                    enhanced_data['specifications'] = enhancement_data['enhanced_specifications']
                
                # Log corrections made
                if 'corrections_made' in enhancement_data:
                    print(f"Corrections made for {original_data.get('name', 'unknown')}:")
                    for correction in enhancement_data['corrections_made']:
                        print(f"  - {correction}")
                
                return enhanced_data
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse enhancement response: {e}")
        except Exception as e:
            print(f"Error parsing enhancement response: {e}")
        
        return original_data
    
    def batch_enhance_products(self, products_data: Dict[str, Any], delay: float = 1.0) -> Dict[str, Any]:
        """Enhance all products in the hierarchical structure."""
        enhanced_data = products_data.copy()
        
        if 'categories' in enhanced_data:
            for category_name, category_data in enhanced_data['categories'].items():
                if 'products' in category_data:
                    print(f"Enhancing products in category: {category_name}")
                    
                    for i, product in enumerate(category_data['products']):
                        print(f"  Processing product {i+1}/{len(category_data['products'])}: {product.get('name', 'unknown')}")
                        
                        enhanced_product = self.enhance_specifications(product)
                        category_data['products'][i] = enhanced_product
                        
                        # Add delay to respect rate limits
                        if delay > 0:
                            time.sleep(delay)
        
        return enhanced_data

def create_openrouter_client(model_id: str = "google/gemini-2.5-pro-exp-03-25") -> OpenRouterClient:
    """Create OpenRouter client with provided credentials."""
    config = OpenRouterConfig(
        api_key="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",
        model_id=model_id
    )
    return OpenRouterClient(config)