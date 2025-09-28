import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict

class ProductDatabase:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection("products")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self._initialize_data()
    
    def _initialize_data(self):
        # No pre-loaded data - all products will be scraped dynamically
        pass
    
    def get_product(self, product_name: str) -> Dict:
        """Get product from database if it exists."""
        try:
            results = self.collection.get(ids=[product_name])
            if results['metadatas']:
                product = results['metadatas'][0]
                product['ingredients'] = product['ingredients'].split(',') if product['ingredients'] else []
                return product
        except:
            pass
        return None
    
    def add_product(self, product_data: Dict):
        """Add or update product in database."""
        # Convert ingredients list to string for storage
        if isinstance(product_data.get('ingredients'), list):
            product_data['ingredients'] = ','.join(product_data['ingredients'])
        
        embedding = self.model.encode([product_data["name"]])
        
        # Try to update existing product first
        try:
            self.collection.delete(ids=[product_data["name"]])
        except:
            pass
        
        self.collection.add(
            embeddings=[embedding[0].tolist()],
            documents=[product_data["name"]],
            metadatas=[product_data],
            ids=[product_data["name"]]
        )
    
    def find_alternatives(self, safety_threshold: float = 3.0, n_results: int = 3, exclude_product: str = None) -> List[Dict]:
        results = self.collection.get()
        alternatives = []
        for metadata in results['metadatas']:
            # Skip the current product
            if exclude_product and metadata.get('name') == exclude_product:
                continue
                
            if metadata['safety_score'] <= safety_threshold:
                # Convert ingredients string back to list for response
                metadata['ingredients'] = metadata['ingredients'].split(',') if metadata['ingredients'] else []
                alternatives.append(metadata)
        return alternatives[:n_results]