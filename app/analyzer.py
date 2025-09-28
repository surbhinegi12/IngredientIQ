from typing import List, Dict
from .database import ProductDatabase
from .scraper import IngredientScraper
from .gemini_client import GeminiClient
from .models import Ingredient, ProductAnalysis
import statistics

class SkincareAnalyzer:
    def __init__(self):
        self.product_db = ProductDatabase()
        self.scraper = IngredientScraper()
        self.gemini_client = GeminiClient()
    
    def clear_all_cache(self):
        """Clear all cached data and start fresh."""
        try:
            # Delete all collections
            self.product_db.client.delete_collection("products")
            
            # Recreate collections
            self.product_db.collection = self.product_db.client.get_or_create_collection("products")
            
            print("✅ All cache cleared successfully!")
            return True
        except Exception as e:
            print(f"Cache clearing error: {e}")
            return False
    
    def analyze_product(self, product_name: str) -> ProductAnalysis:
        # Check if product already exists in database
        cached_product = self.product_db.get_product(product_name)
        
        if cached_product:
            print(f"Found cached data for {product_name}")
            ingredients_list = cached_product['ingredients']
            # Clear any old cache to get fresh table data
            if hasattr(self.scraper, 'ingredient_ratings_cache'):
                delattr(self.scraper, 'ingredient_ratings_cache')
        else:
            print(f"Scraping ingredients for {product_name}")
            # Extract ingredients using web scraping - this will also cache the ratings
            ingredients_list = self.scraper.extract_ingredients_from_product(product_name)
        
        # Analyze each ingredient
        ingredients_analysis = []
        safety_scores = []
        allergen_warnings = []
        
        # Skip analysis if no ingredients found
        if not ingredients_list:
            return ProductAnalysis(
                product_name=product_name,
                ingredients_analysis=[],
                overall_safety_score=0.0,
                risk_summary="No ingredient data available for analysis",
                allergen_warnings=[],
                alternatives=[]
            )
        
        for ingredient_name in ingredients_list:
            # Skip invalid ingredients (scraped text artifacts)
            if not self._is_valid_ingredient(ingredient_name):
                continue
            # Use INCIdecoder table data when available, otherwise use other sources
            ingredient_data = self.scraper.get_comprehensive_ingredient_data(ingredient_name)
            ingredient_data["name"] = ingredient_name
            
            if ingredient_data:
                ingredient = Ingredient(
                    name=ingredient_data["name"],
                    safety_score=ingredient_data["safety_score"],
                    risk_level=ingredient_data["risk_level"],
                    allergens=ingredient_data["allergens"],
                    benefits=ingredient_data["benefits"],
                    risks=ingredient_data["risks"],
                    skin_types=ingredient_data["skin_types"]
                )
                ingredients_analysis.append(ingredient)
                safety_scores.append(ingredient_data["safety_score"])
                
                if ingredient_data["allergens"]:
                    allergen_warnings.extend(ingredient_data["allergens"])
        
        # Calculate overall safety score
        overall_safety = statistics.mean(safety_scores) if safety_scores else 0
        
        # Cache the product if not already cached
        if not cached_product:
            self.product_db.add_product({
                "name": product_name,
                "ingredients": ingredients_list,
                "safety_score": round(overall_safety, 2),
                "category": "skincare"
            })
            print(f"Cached product data for {product_name}")
        
        # Generate risk summary using Gemini
        risk_summary = self.gemini_client.generate_product_summary(
            product_name, ingredients_list, overall_safety
        )
        
        # Create preliminary analysis object for alternatives generation
        preliminary_analysis = {
            "product_name": product_name,
            "ingredients_analysis": [
                {
                    "name": ing.name,
                    "safety_score": ing.safety_score,
                    "risk_level": ing.risk_level,
                    "allergens": ing.allergens,
                    "benefits": ing.benefits,
                    "risks": ing.risks,
                    "skin_types": ing.skin_types
                } for ing in ingredients_analysis
            ],
            "overall_safety_score": round(overall_safety, 2),
            "allergen_warnings": list(set(allergen_warnings))
        }
        
        # Use Gemini to suggest better alternatives
        gemini_alternatives = self.gemini_client.suggest_alternatives(preliminary_analysis)
        
        # Also find alternatives from database (fallback) - exclude current product
        db_alternatives = self.product_db.find_alternatives(
            safety_threshold=overall_safety, 
            exclude_product=product_name
        )
        
        # Combine alternatives (prioritize Gemini suggestions)
        all_alternatives = gemini_alternatives + db_alternatives[:2]  # Limit DB alternatives
        
        return ProductAnalysis(
            product_name=product_name,
            ingredients_analysis=ingredients_analysis,
            overall_safety_score=round(overall_safety, 2),
            risk_summary=risk_summary,
            allergen_warnings=list(set(allergen_warnings)),
            alternatives=all_alternatives
        )
    
    def _is_valid_ingredient(self, ingredient_name: str) -> bool:
        """Check if an ingredient name is valid and not scraped text artifacts."""
        ingredient_lower = ingredient_name.lower().strip()
        
        # Filter out common web scraping artifacts
        invalid_patterns = [
            'click here',
            'know more',
            'read more',
            'see more',
            '>>',
            '<<',
            'http',
            'www.',
            '.com',
            'ingredients:',
            'full list',
            'view all',
            'show more',
            'expand',
            'collapse'
        ]
        
        # Check for invalid patterns
        for pattern in invalid_patterns:
            if pattern in ingredient_lower:
                return False
        
        # Check length (too short or too long is likely invalid)
        if len(ingredient_name) < 3 or len(ingredient_name) > 60:
            return False
        
        # Check if it's mostly numbers or special characters
        if len([c for c in ingredient_name if c.isalnum()]) < len(ingredient_name) * 0.5:
            return False
        
        return True
    
