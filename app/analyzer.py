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
        """Analyze a product with comprehensive error handling and fallback mechanisms."""
        if not product_name or not isinstance(product_name, str):
            raise ValueError("Product name must be a non-empty string")
        
        product_name = product_name.strip()
        if len(product_name) < 2:
            raise ValueError("Product name too short")
        
        try:
            # Check if product already exists in database
            cached_product = None
            try:
                cached_product = self.product_db.get_product(product_name)
            except Exception as e:
                print(f"Warning: Database lookup failed: {e}")
            
            if cached_product:
                print(f"Found cached data for {product_name}")
                ingredients_list = cached_product['ingredients']
                # Clear any old cache to get fresh table data
                if hasattr(self.scraper, 'ingredient_ratings_cache'):
                    delattr(self.scraper, 'ingredient_ratings_cache')
            else:
                print(f"Scraping ingredients for {product_name}")
                # Extract ingredients using web scraping with error handling
                try:
                    ingredients_list = self.scraper.extract_ingredients_from_product(product_name)
                except Exception as e:
                    print(f"Scraping failed: {e}")
                    # Provide fallback response
                    return self._create_fallback_analysis(product_name, f"Ingredient extraction failed: {str(e)}")
            
            # Analyze each ingredient
            ingredients_analysis = []
            safety_scores = []
            allergen_warnings = []
            
            # Enhanced validation of ingredients list
            if not ingredients_list or not isinstance(ingredients_list, list):
                print(f"No valid ingredients found for {product_name}")
                return self._create_fallback_analysis(product_name, "No ingredient data available for analysis")
            
            # Filter out invalid ingredients early
            valid_ingredients = [ing for ing in ingredients_list if self._is_valid_ingredient(ing)]
            
            if not valid_ingredients:
                print(f"No valid ingredients found after filtering for {product_name}")
                return self._create_fallback_analysis(product_name, "No valid ingredients found after filtering")
            
            print(f"Analyzing {len(valid_ingredients)} valid ingredients for {product_name}")
            
            # Process each valid ingredient with error handling
            for ingredient_name in valid_ingredients:
                try:
                    # Use INCIdecoder table data when available, otherwise use other sources
                    ingredient_data = self.scraper.get_comprehensive_ingredient_data(ingredient_name)
                    if not ingredient_data:
                        print(f"Warning: No data found for ingredient {ingredient_name}")
                        continue
                    
                    ingredient_data["name"] = ingredient_name
                    
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
                        
                except Exception as e:
                    print(f"Error analyzing ingredient {ingredient_name}: {e}")
                    # Continue with other ingredients instead of failing completely
                    continue
            
            # Ensure we have at least some analysis results
            if not ingredients_analysis:
                print(f"No ingredient analysis results for {product_name}")
                return self._create_fallback_analysis(product_name, "Unable to analyze any ingredients successfully")
            
            # Calculate overall safety score
            overall_safety = statistics.mean(safety_scores) if safety_scores else 5.0
            
            # Cache the product if not already cached
            if not cached_product:
                try:
                    self.product_db.add_product({
                        "name": product_name,
                        "ingredients": valid_ingredients,
                        "safety_score": round(overall_safety, 2),
                        "category": "skincare"
                    })
                    print(f"Cached product data for {product_name}")
                except Exception as e:
                    print(f"Warning: Failed to cache product data: {e}")
            
            # Generate risk summary using Gemini with error handling
            risk_summary = "Analysis complete"
            try:
                risk_summary = self.gemini_client.generate_product_summary(
                    product_name, valid_ingredients, overall_safety
                )
            except Exception as e:
                print(f"Warning: Gemini risk summary failed: {e}")
                risk_summary = f"Product safety score: {overall_safety:.1f}/10. Manual review recommended."
            
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
            
            # Use Gemini to suggest better alternatives with error handling
            gemini_alternatives = []
            try:
                gemini_alternatives = self.gemini_client.suggest_alternatives(preliminary_analysis)
            except Exception as e:
                print(f"Warning: Gemini alternatives failed: {e}")
            
            # Also find alternatives from database (fallback) - exclude current product
            db_alternatives = []
            try:
                db_alternatives = self.product_db.find_alternatives(
                    safety_threshold=overall_safety, 
                    exclude_product=product_name
                )
            except Exception as e:
                print(f"Warning: Database alternatives failed: {e}")
            
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
            
        except Exception as e:
            print(f"Critical error in product analysis: {e}")
            return self._create_fallback_analysis(product_name, f"Analysis failed: {str(e)}")
    
    def _create_fallback_analysis(self, product_name: str, error_message: str) -> ProductAnalysis:
        """Create a fallback analysis when normal analysis fails."""
        return ProductAnalysis(
            product_name=product_name,
            ingredients_analysis=[],
            overall_safety_score=5.0,  # Neutral score
            risk_summary=f"Unable to complete analysis: {error_message}",
            allergen_warnings=[],
            alternatives=[]
        )
    
    def _is_valid_ingredient(self, ingredient_name: str) -> bool:
        """Check if an ingredient name is valid and not scraped text artifacts."""
        if not ingredient_name or not isinstance(ingredient_name, str):
            return False
            
        ingredient_lower = ingredient_name.lower().strip()
        
        # Filter out common web scraping artifacts and partial sentences
        invalid_patterns = [
            'click here', 'know more', 'read more', 'see more', 'view all', 'show more',
            'expand', 'collapse', 'full list', 'ingredients:', 'http', 'www.', '.com',
            'in this case', 'such as', 'if this sentence', 'another peptide', 'for example',
            'as mentioned', 'see above', 'note that', 'please note', 'important',
            'disclaimer', 'warning', 'caution', 'may contain', 'does not contain',
            'free from', 'without', 'includes', 'contains', 'made with', 'formulated with'
        ]
        
        # Check for invalid patterns
        for pattern in invalid_patterns:
            if pattern in ingredient_lower:
                return False
        
        # Check for sentence-like structures (contains common sentence words)
        sentence_indicators = [
            ' is ', ' are ', ' was ', ' were ', ' the ', ' and ', ' or ', ' but ',
            ' if ', ' when ', ' where ', ' what ', ' how ', ' why ', ' because ',
            ' since ', ' although ', ' however ', ' therefore ', ' moreover '
        ]
        
        for indicator in sentence_indicators:
            if indicator in ingredient_lower:
                return False
        
        # Check length (too short or too long is likely invalid)
        if len(ingredient_name) < 3 or len(ingredient_name) > 80:
            return False
        
        # Reject if it contains incomplete parentheses or brackets
        if ingredient_name.count('(') != ingredient_name.count(')'):
            return False
        if ingredient_name.count('[') != ingredient_name.count(']'):
            return False
        
        # Check if it's mostly numbers or special characters (but allow chemical names)
        alphanumeric_chars = len([c for c in ingredient_name if c.isalnum()])
        if alphanumeric_chars < len(ingredient_name) * 0.4:
            return False
        
        # Reject if it starts or ends with common non-ingredient words
        invalid_starts = ['and ', 'or ', 'but ', 'if ', 'when ', 'the ', 'a ', 'an ']
        invalid_ends = [' and', ' or', ' but', ' if', ' when', ' the', ' is', ' are']
        
        for start in invalid_starts:
            if ingredient_lower.startswith(start):
                return False
        
        for end in invalid_ends:
            if ingredient_lower.endswith(end):
                return False
        
        # Accept if it looks like a valid chemical/ingredient name
        # Common ingredient patterns: contains letters, may have numbers, hyphens, spaces
        import re
        if re.match(r'^[a-zA-Z][a-zA-Z0-9\s\-\(\)\.]*[a-zA-Z0-9\)]$', ingredient_name):
            return True
        
        return False
    
