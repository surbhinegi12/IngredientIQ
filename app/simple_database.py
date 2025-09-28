from typing import List, Dict, Optional

class SimpleProductDatabase:
    def __init__(self):
        # Simple in-memory storage
        self.products = {}
        self._initialize_data()
    
    def _initialize_data(self):
        # No pre-loaded data - all products will be scraped dynamically
        pass
    
    def get_product(self, product_name: str) -> Optional[Dict]:
        """Get product from database if it exists."""
        return self.products.get(product_name.lower())
    
    def add_product(self, product_data: Dict):
        """Add or update product in database."""
        product_name = product_data["name"].lower()
        self.products[product_name] = product_data.copy()
    
    def find_alternatives(self, safety_threshold: float = 3.0, n_results: int = 3, exclude_product: str = None) -> List[Dict]:
        """Find alternative products with better safety scores."""
        alternatives = []
        
        for product_name, product_data in self.products.items():
            # Skip the current product
            if exclude_product and product_data.get('name', '').lower() == exclude_product.lower():
                continue
            
            # Filter by safety score
            if product_data.get('safety_score', float('inf')) <= safety_threshold:
                alternatives.append(product_data.copy())
        
        # Sort by safety score (lower is better)
        alternatives.sort(key=lambda x: x.get('safety_score', float('inf')))
        
        return alternatives[:n_results]
    
    def clear_all_products(self):
        """Clear all stored products."""
        self.products.clear()
    
    def get_product_count(self) -> int:
        """Get total number of stored products."""
        return len(self.products)
    
    def list_all_products(self) -> List[str]:
        """Get list of all product names."""
        return [data['name'] for data in self.products.values()]