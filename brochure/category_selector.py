#!/usr/bin/env python3
"""
Interactive Category Selector for HeyZack Brochure Generator

Provides a CLI interface for users to select specific product categories
before generating the brochure, ensuring targeted content generation.
"""

import json
from typing import List, Dict, Any
from collections import defaultdict


class CategorySelector:
    """Interactive category selection interface for brochure generation."""
    
    def __init__(self, products_data: List[Dict[str, Any]]):
        """Initialize with product data.
        
        Args:
            products_data: List of product dictionaries
        """
        self.products_data = products_data
        self.categories = self._extract_categories()
    
    def _extract_categories(self) -> Dict[str, int]:
        """Extract unique categories and count products in each.
        
        Returns:
            Dictionary mapping category names to product counts
        """
        category_counts = defaultdict(int)
        
        for product in self.products_data:
            category = product.get('category', 'Uncategorized')
            if category:
                category_counts[category] += 1
        
        return dict(sorted(category_counts.items()))
    
    def display_categories(self) -> None:
        """Display available categories with product counts."""
        print("\n" + "="*60)
        print("🏠 HeyZack Smart Home Product Categories")
        print("="*60)
        print(f"Total Categories: {len(self.categories)}")
        print(f"Total Products: {sum(self.categories.values())}")
        print("\n📋 Available Categories:")
        print("-" * 40)
        
        for i, (category, count) in enumerate(self.categories.items(), 1):
            print(f"{i:2d}. {category:<30} ({count:3d} products)")
        
        print("-" * 40)
        print(f"{len(self.categories) + 1:2d}. Select All Categories")
        print("="*60)
    
    def get_user_selection(self) -> List[str]:
        """Get user's category selection through interactive CLI.
        
        Returns:
            List of selected category names
        """
        self.display_categories()
        
        while True:
            try:
                print("\n🎯 Selection Options:")
                print("   • Enter category numbers (e.g., 1,3,5)")
                print("   • Enter ranges (e.g., 1-5)")
                print("   • Mix both (e.g., 1,3-5,8)")
                print(f"   • Enter {len(self.categories) + 1} for all categories")
                print("   • Press Enter for all categories")
                
                user_input = input("\n➤ Your selection: ").strip()
                
                # Default to all categories if empty input
                if not user_input:
                    return list(self.categories.keys())
                
                selected_indices = self._parse_selection(user_input)
                
                # Validate indices
                max_index = len(self.categories) + 1
                if any(idx < 1 or idx > max_index for idx in selected_indices):
                    print(f"❌ Invalid selection. Please enter numbers between 1 and {max_index}.")
                    continue
                
                # Handle "Select All" option
                if max_index in selected_indices:
                    return list(self.categories.keys())
                
                # Get selected categories
                category_list = list(self.categories.keys())
                selected_categories = [category_list[idx - 1] for idx in selected_indices]
                
                # Confirm selection
                self._confirm_selection(selected_categories)
                return selected_categories
                
            except (ValueError, IndexError) as e:
                print(f"❌ Invalid input format. Please try again. Error: {e}")
            except KeyboardInterrupt:
                print("\n\n👋 Selection cancelled. Exiting...")
                exit(0)
    
    def _parse_selection(self, user_input: str) -> List[int]:
        """Parse user input string into list of category indices.
        
        Args:
            user_input: User input string (e.g., "1,3-5,8")
            
        Returns:
            List of category indices
        """
        indices = set()
        
        for part in user_input.split(','):
            part = part.strip()
            
            if '-' in part:
                # Handle range (e.g., "3-5")
                start, end = map(int, part.split('-'))
                indices.update(range(start, end + 1))
            else:
                # Handle single number
                indices.add(int(part))
        
        return sorted(list(indices))
    
    def _confirm_selection(self, selected_categories: List[str]) -> None:
        """Display confirmation of selected categories.
        
        Args:
            selected_categories: List of selected category names
        """
        total_products = sum(self.categories[cat] for cat in selected_categories)
        
        print("\n" + "="*50)
        print("✅ Selection Confirmed")
        print("="*50)
        print(f"Selected Categories: {len(selected_categories)}")
        print(f"Total Products: {total_products}")
        print("\n📦 Selected Categories:")
        
        for category in selected_categories:
            count = self.categories[category]
            print(f"   • {category:<30} ({count:3d} products)")
        
        print("="*50)
    
    def filter_products(self, selected_categories: List[str]) -> List[Dict[str, Any]]:
        """Filter products based on selected categories.
        
        Args:
            selected_categories: List of category names to include
            
        Returns:
            Filtered list of products
        """
        filtered_products = [
            product for product in self.products_data
            if product.get('category', 'Uncategorized') in selected_categories
        ]
        
        print(f"\n🔍 Filtered {len(filtered_products)} products from {len(selected_categories)} categories")
        return filtered_products


def select_categories_interactive(products_file: str) -> List[Dict[str, Any]]:
    """Main function to handle interactive category selection.
    
    Args:
        products_file: Path to products JSON file
        
    Returns:
        Filtered list of products based on user selection
    """
    try:
        # Load products data
        with open(products_file, 'r', encoding='utf-8') as f:
            products_data = json.load(f)
        
        # Initialize selector
        selector = CategorySelector(products_data)
        
        # Get user selection
        selected_categories = selector.get_user_selection()
        
        # Filter and return products
        return selector.filter_products(selected_categories)
        
    except FileNotFoundError:
        print(f"❌ Error: Products file '{products_file}' not found.")
        exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON in '{products_file}'.")
        exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        exit(1)


if __name__ == "__main__":
    # Test the category selector
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python category_selector.py <products_file>")
        sys.exit(1)
    
    products_file = sys.argv[1]
    filtered_products = select_categories_interactive(products_file)
    print(f"\n✅ Successfully filtered {len(filtered_products)} products.")