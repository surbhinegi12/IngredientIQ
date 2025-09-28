import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import re
import time

class IngredientScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def extract_ingredients_from_product(self, product_name: str) -> List[str]:
        """Extract ingredients using INCIdecoder web scraping."""
        try:
            ingredients = self._scrape_incidecoder(product_name)
            if ingredients:
                return ingredients
                
        except Exception as e:
            print(f"INCIdecoder scraping failed: {e}")
        
        print(f"No ingredients found for {product_name}")
        return []
    
    def _scrape_incidecoder(self, product_name: str) -> List[str]:
        """Scrape ingredients from INCIdecoder."""
        try:
            # INCIdecoder search URL
            search_url = f"https://incidecoder.com/search?query={product_name.replace(' ', '+')}"
            print(f"Searching INCIdecoder: {search_url}")
            response = requests.get(search_url, headers=self.headers, timeout=15)
            
            print(f"INCIdecoder response status: {response.status_code}")
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for different types of product links
                product_links = soup.find_all('a', href=re.compile(r'/products/'))
                if not product_links:
                    product_links = soup.find_all('a', href=re.compile(r'/ingredient'))
                
                print(f"Found {len(product_links)} product links")
                
                for i, link in enumerate(product_links[:3]):
                    product_url = "https://incidecoder.com" + link['href']
                    print(f"Trying product URL {i+1}: {product_url}")
                    ingredients = self._extract_from_product_page(product_url)
                    if ingredients:
                        return ingredients
            
        except Exception as e:
            print(f"INCIdecoder search error: {e}")
        
        return []
    
    def _extract_from_product_page(self, product_url: str) -> List[str]:
        """Extract ingredients from INCIdecoder product page."""
        try:
            response = requests.get(product_url, headers=self.headers, timeout=15)
            print(f"Product page status: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for ingredients in multiple ways
                ingredients = []
                
                # Method 1: Look for structured ingredient lists (most reliable)
                ingredient_containers = soup.find_all(['div', 'section'], class_=re.compile(r'ingredient|inci|formula', re.I))
                for container in ingredient_containers:
                    # Look for ingredient links within containers
                    ingredient_links = container.find_all('a', href=re.compile(r'/ingredients/'))
                    for link in ingredient_links:
                        ingredient_name = self._clean_ingredient_name(link.get_text().strip())
                        if self._is_valid_ingredient_name(ingredient_name) and ingredient_name not in ingredients:
                            ingredients.append(ingredient_name)
                
                # Method 2: Look for ingredient links globally if container method failed
                if len(ingredients) < 3:
                    ingredient_links = soup.find_all('a', href=re.compile(r'/ingredients/'))
                    for link in ingredient_links:
                        ingredient_name = self._clean_ingredient_name(link.get_text().strip())
                        if self._is_valid_ingredient_name(ingredient_name) and ingredient_name not in ingredients:
                            ingredients.append(ingredient_name)
                
                # Method 3: Look for structured lists (ul, ol)
                if len(ingredients) < 3:
                    ingredient_lists = soup.find_all(['ul', 'ol'])
                    for ul in ingredient_lists:
                        # Check if this list contains ingredients (look for chemical-sounding names)
                        items = ul.find_all('li')
                        if len(items) > 3:  # Likely an ingredient list
                            for item in items:
                                ingredient_name = self._clean_ingredient_name(item.get_text().strip())
                                if self._is_valid_ingredient_name(ingredient_name) and ingredient_name not in ingredients:
                                    ingredients.append(ingredient_name)
                
                # Method 4: Look for comma-separated ingredient text (last resort)
                if len(ingredients) < 3:
                    text_blocks = soup.find_all(['p', 'div'], string=re.compile(r'aqua|water.*,.*', re.I))
                    for block in text_blocks:
                        text = block.get_text().strip()
                        if len(text) > 50 and ',' in text:  # Looks like ingredient list
                            text_ingredients = self._parse_ingredient_text_improved(text)
                            for ing in text_ingredients:
                                if self._is_valid_ingredient_name(ing) and ing not in ingredients:
                                    ingredients.append(ing)
                
                if len(ingredients) > 2:
                    print(f"Found {len(ingredients)} ingredients from product page")
                    return ingredients[:20]  # Return more ingredients but with better validation
                else:
                    print(f"Only found {len(ingredients)} ingredients, may need manual verification")
            
        except Exception as e:
            print(f"Product page extraction error: {e}")
        
        return []
    

    
    def _parse_ingredient_text(self, text: str) -> List[str]:
        """Parse ingredient list from text."""
        # Clean and split ingredient text
        text = re.sub(r'ingredients?:?\s*', '', text, flags=re.I)
        ingredients = [ing.strip() for ing in re.split(r'[,;]', text)]
        
        # Filter out empty strings and common non-ingredients
        filtered = []
        for ing in ingredients:
            ing = ing.strip()
            if (len(ing) > 2 and len(ing) < 50 and  # Reject very long strings
                not re.match(r'^\d+$', ing) and 
                'http' not in ing.lower() and  # Reject URLs
                'login' not in ing.lower() and  # Reject navigation
                'register' not in ing.lower() and
                'follow us' not in ing.lower() and
                'read all' not in ing.lower() and
                'explained' not in ing.lower() and
                ing.lower() not in ['and', 'or', 'may contain', 'products', 'decode inci']):
                filtered.append(ing)
        
        return filtered[:15]  # Limit to first 15 ingredients
    
    def _parse_ingredient_text_improved(self, text: str) -> List[str]:
        """Enhanced ingredient parsing from text with better validation."""
        if not text or len(text) < 20:
            return []
        
        # Clean the text
        text = re.sub(r'ingredients?:?\s*', '', text, flags=re.I)
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        
        # Split on common delimiters
        potential_ingredients = []
        for delimiter in [',', ';', '\n']:
            if delimiter in text:
                potential_ingredients = [ing.strip() for ing in text.split(delimiter)]
                break
        
        if not potential_ingredients:
            return []
        
        # Advanced filtering
        filtered = []
        for ing in potential_ingredients:
            cleaned = self._clean_ingredient_name(ing)
            if self._is_valid_ingredient_name(cleaned):
                filtered.append(cleaned)
        
        return filtered[:15]
    
    def _clean_ingredient_name(self, ingredient_name: str) -> str:
        """Clean and normalize ingredient name."""
        if not ingredient_name:
            return ""
        
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', ingredient_name.strip())
        
        # Remove common prefixes/suffixes that aren't part of ingredient name
        cleaned = re.sub(r'^(and\s+|or\s+|also\s+)', '', cleaned, flags=re.I)
        cleaned = re.sub(r'(\s+and|\s+or)$', '', cleaned, flags=re.I)
        
        # Remove parenthetical explanations that are too long
        if '(' in cleaned and ')' in cleaned:
            paren_content = re.search(r'\(([^)]+)\)', cleaned)
            if paren_content and len(paren_content.group(1)) > 30:
                cleaned = re.sub(r'\([^)]+\)', '', cleaned).strip()
        
        return cleaned
    
    def _is_valid_ingredient_name(self, ingredient_name: str) -> bool:
        """Check if a scraped ingredient name is actually a valid ingredient."""
        if not ingredient_name or len(ingredient_name) < 3:
            return False
        
        ingredient_lower = ingredient_name.lower().strip()
        
        # Reject if it's too long (likely a sentence)
        if len(ingredient_name) > 70:
            return False
        
        # Reject common non-ingredient phrases
        invalid_phrases = [
            'click here', 'read more', 'learn more', 'see full', 'view all',
            'ingredients list', 'full ingredients', 'complete list', 'product details',
            'how to use', 'directions', 'warnings', 'precautions', 'storage',
            'made in', 'manufactured', 'distributed by', 'net weight', 'volume',
            'expiry date', 'best before', 'use by', 'batch number', 'lot number'
        ]
        
        for phrase in invalid_phrases:
            if phrase in ingredient_lower:
                return False
        
        # Reject if it contains too many common English words (likely a sentence)
        common_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
        word_count = sum(1 for word in common_words if f' {word} ' in f' {ingredient_lower} ')
        if word_count > 2:
            return False
        
        # Must contain at least some letters
        if not re.search(r'[a-zA-Z]', ingredient_name):
            return False
        
        # Reject if it's mostly punctuation
        alpha_count = sum(1 for c in ingredient_name if c.isalpha())
        if alpha_count < len(ingredient_name) * 0.5:
            return False
        
        # Accept if it looks like a chemical name (contains typical patterns)
        chemical_patterns = [
            r'[a-z]+yl\b',  # -yl endings
            r'[a-z]+ate\b', # -ate endings
            r'[a-z]+ine\b', # -ine endings
            r'[a-z]+ol\b',  # -ol endings
            r'acid\b',      # acids
            r'sodium\b',    # sodium compounds
            r'potassium\b', # potassium compounds
            r'\b\d+\b',     # numbers (common in chemical names)
        ]
        
        for pattern in chemical_patterns:
            if re.search(pattern, ingredient_lower):
                return True
        
        # Accept common cosmetic ingredient names
        common_ingredients = [
            'aqua', 'water', 'glycerin', 'dimethicone', 'cyclopentasiloxane',
            'phenoxyethanol', 'tocopherol', 'retinol', 'niacinamide', 'ceramide'
        ]
        
        for common in common_ingredients:
            if common in ingredient_lower:
                return True
        
        # If it passes basic checks and looks chemical-ish, accept it
        return True
    

    

    
    def _get_fallback_safety_score(self, ingredient_name: str) -> int:
        """Get ingredient-specific safety scores based on cosmetic knowledge."""
        ingredient_lower = ingredient_name.lower()
        
        # Very safe ingredients (0-1)
        if any(safe in ingredient_lower for safe in ['water', 'aqua']):
            return 0
        if any(safe in ingredient_lower for safe in ['glycerin', 'hyaluronic', 'sodium hyaluronate', 'ceramide']):
            return 1
        
        # Safe moisturizing ingredients (1-2)
        if any(safe in ingredient_lower for safe in ['squalane', 'panthenol', 'allantoin', 'betaine']):
            return 1
        
        # Mild actives (2-3)
        if any(mild in ingredient_lower for mild in ['niacinamide', 'vitamin e', 'tocopherol']):
            return 2
        
        # Medium risk actives (3-4)
        if any(medium in ingredient_lower for medium in ['salicylic acid', 'lactic acid', 'glycolic acid']):
            return 3
        
        # Essential oils and plant extracts (3-4)
        if 'oil' in ingredient_lower or 'extract' in ingredient_lower:
            if any(gentle in ingredient_lower for gentle in ['chamomile', 'aloe', 'green tea']):
                return 3
            else:
                return 4
        
        # Retinoids (4-6)
        if any(retinoid in ingredient_lower for retinoid in ['retinol', 'retinyl', 'retinoic', 'tretinoin']):
            if 'palmitate' in ingredient_lower:
                return 4  # Gentler retinoid
            else:
                return 5  # Stronger retinoid
        
        # Preservatives (3-5)
        if any(preservative in ingredient_lower for preservative in ['phenoxyethanol', 'benzyl alcohol', 'potassium sorbate']):
            return 3
        if any(preservative in ingredient_lower for preservative in ['parabens', 'methylparaben', 'propylparaben']):
            return 4
        
        # High-risk ingredients (6-8)
        if any(risky in ingredient_lower for risky in ['fragrance', 'parfum', 'alcohol denat', 'denatured alcohol']):
            return 7
        if any(risky in ingredient_lower for risky in ['formaldehyde', 'dmdm hydantoin', 'quaternium-15']):
            return 8
        
        # Acids and strong actives (4-6)
        if any(acid in ingredient_lower for acid in ['benzoyl peroxide', 'hydrogen peroxide']):
            return 6
        
        # Default medium-low risk
        return 3
    

    
    def _extract_score(self, text: str) -> int:
        """Extract numeric score from text."""
        # Look for numbers in the text
        numbers = re.findall(r'\d+', text)
        if numbers:
            return min(int(numbers[0]), 10)  # Cap at 10
        return 5  # Default medium score
    

    

    

    

    
    def _check_known_allergens(self, ingredient_name: str) -> List[str]:
        """Check for known cosmetic allergens."""
        allergens = []
        known_allergens = {
            "fragrance": "fragrance",
            "parfum": "fragrance",
            "formaldehyde": "formaldehyde",
            "parabens": "parabens",
            "sulfates": "sulfates",
            "alcohol denat": "drying alcohol"
        }
        
        for allergen, category in known_allergens.items():
            if allergen in ingredient_name.lower():
                allergens.append(category)
        
        return allergens
    
    def scrape_incidecoder_ingredient_safety(self, ingredient_name: str) -> Dict:
        """Scrape ingredient safety data directly from INCIdecoder ingredient page."""
        try:
            # Clean ingredient name for URL
            clean_name = ingredient_name.lower().replace(' ', '-').replace('(', '').replace(')', '')
            ingredient_url = f"https://incidecoder.com/ingredients/{clean_name}"
            
            print(f"   Scraping INCIdecoder ingredient page: {ingredient_url}")
            response = requests.get(ingredient_url, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract safety information from INCIdecoder's ingredient page
                safety_data = self._extract_incidecoder_safety_data(soup, ingredient_name)
                
                if safety_data:
                    print(f"   Found INCIdecoder safety data: {safety_data}")
                    return safety_data
            else:
                print(f"   INCIdecoder ingredient page returned {response.status_code}")
                
        except Exception as e:
            print(f"   INCIdecoder ingredient scraping error: {e}")
        
        # Fallback to intelligent scoring if scraping fails
        return self._get_fallback_safety_score_dict(ingredient_name)
    
    def _extract_incidecoder_safety_data(self, soup, ingredient_name: str) -> Dict:
        """Extract safety data from INCIdecoder ingredient page structure."""
        safety_data = {
            "safety_score": 3,  # Default medium
            "risk_level": "Medium",
            "function": "Unknown",
            "benefits": "No data available",
            "risks": "Standard precautions apply",
            "allergens": [],
            "skin_types": ["normal"]
        }
        
        try:
            # Extract ingredient function/type
            function_elements = soup.find_all(['span', 'div'], class_=re.compile(r'function|type|category', re.I))
            for elem in function_elements:
                text = elem.get_text().strip()
                if text and len(text) < 100:
                    safety_data["function"] = text
                    break
            
            # Extract benefits/description
            description_elements = soup.find_all(['p', 'div'], class_=re.compile(r'description|benefit|what-it-does', re.I))
            for elem in description_elements:
                text = elem.get_text().strip()
                if text and len(text) > 20:
                    safety_data["benefits"] = text[:300]  # Limit length
                    break
            
            # Look for safety-related information in the page text
            page_text = soup.get_text().lower()
            
            # Check for risk indicators in the text
            risk_indicators = {
                "irritant": 2,
                "sensitizer": 2, 
                "allergen": 3,
                "comedogenic": 2,
                "fragrance": 3,
                "alcohol": 2,
                "preservative": 1,
                "safe": -1,
                "gentle": -1,
                "natural": -1
            }
            
            risk_adjustments = []
            for indicator, adjustment in risk_indicators.items():
                if indicator in page_text:
                    risk_adjustments.append(adjustment)
                    if indicator in ["irritant", "sensitizer", "allergen"]:
                        safety_data["allergens"].append(indicator)
            
            # Calculate safety score based on found indicators
            if risk_adjustments:
                avg_adjustment = sum(risk_adjustments) / len(risk_adjustments)
                safety_data["safety_score"] = int(max(0, min(10, 3 + avg_adjustment)))
            
            # Look for specific safety ratings or scores in tables
            incidecoder_irritancy = 0
            incidecoder_comedogenicity = 0
            incidecoder_overall = "Unknown"
            
            tables = soup.find_all('table')
            for table in tables:
                extracted_ratings = self._extract_incidecoder_ratings_from_table(table)
                if extracted_ratings:
                    incidecoder_irritancy = extracted_ratings.get('irritancy', 0)
                    incidecoder_comedogenicity = extracted_ratings.get('comedogenicity', 0)
                    incidecoder_overall = extracted_ratings.get('overall_rating', 'Unknown')
                    break
            
            # If we found INCIdecoder ratings, use them directly
            if incidecoder_irritancy > 0 or incidecoder_comedogenicity > 0 or incidecoder_overall != "Unknown":
                safety_data["safety_score"] = self._convert_incidecoder_to_safety_score(
                    incidecoder_irritancy, incidecoder_comedogenicity, incidecoder_overall, safety_data["function"]
                )
                safety_data["irritancy"] = incidecoder_irritancy
                safety_data["comedogenicity"] = incidecoder_comedogenicity
                safety_data["overall_rating"] = incidecoder_overall
                safety_data["source"] = "INCIdecoder_ratings"
            
            # Look for comedogenic rating
            comedogenic_match = re.search(r'comedogenic[^0-9]*([0-5])', page_text)
            if comedogenic_match:
                comedogenic_score = int(comedogenic_match.group(1))
                safety_data["safety_score"] = int(safety_data["safety_score"] + comedogenic_score * 0.5)
            
            # Extract skin type recommendations
            if "sensitive" in page_text and "good" in page_text:
                safety_data["skin_types"] = ["all", "sensitive"]
            elif "oily" in page_text or "acne" in page_text:
                safety_data["skin_types"] = ["oily", "combination"]
            elif "dry" in page_text:
                safety_data["skin_types"] = ["dry", "normal"]
            
            # Ensure safety score is an integer and determine risk level
            safety_data["safety_score"] = int(safety_data["safety_score"])
            final_score = safety_data["safety_score"]
            if final_score <= 2:
                safety_data["risk_level"] = "Safe"
            elif final_score <= 4:
                safety_data["risk_level"] = "Medium"
            else:
                safety_data["risk_level"] = "High"
            
            # Add INCIdecoder raw ratings if not already present
            if "irritancy" not in safety_data:
                safety_data["irritancy"] = 0
            if "comedogenicity" not in safety_data:
                safety_data["comedogenicity"] = 0
            if "overall_rating" not in safety_data:
                safety_data["overall_rating"] = "Unknown"
            if "source" not in safety_data:
                safety_data["source"] = "text_analysis"
            
            # Generate risks summary
            if safety_data["allergens"]:
                safety_data["risks"] = f"May cause {', '.join(safety_data['allergens'])}. Patch test recommended."
            elif final_score >= 6:
                safety_data["risks"] = "High risk ingredient. Use with caution."
            elif final_score >= 4:
                safety_data["risks"] = "Moderate risk. May not suit all skin types."
            else:
                safety_data["risks"] = "Generally well-tolerated ingredient."
            
            return safety_data
            
        except Exception as e:
            print(f"   Error extracting INCIdecoder safety data: {e}")
            return safety_data
    

    
    def _get_fallback_safety_score_dict(self, ingredient_name: str) -> Dict:
        """Enhanced fallback safety scoring with full data structure."""
        ingredient_lower = ingredient_name.lower()
        
        # Initialize with defaults
        safety_data = {
            "safety_score": 3,
            "risk_level": "Medium",
            "function": "Cosmetic ingredient",
            "benefits": self._get_cosmetic_benefits(ingredient_name),
            "risks": "Standard precautions apply",
            "allergens": [],
            "skin_types": ["normal"]
        }
        
        # Apply ingredient-specific scoring
        safety_score = self._get_fallback_safety_score(ingredient_name)
        safety_data["safety_score"] = int(safety_score)
        
        # Update other fields based on score
        if safety_score <= 2:
            safety_data["risk_level"] = "Safe"
            safety_data["risks"] = "Generally well-tolerated"
            safety_data["skin_types"] = ["all", "sensitive"]
        elif safety_score <= 4:
            safety_data["risk_level"] = "Medium"
            safety_data["risks"] = "May not suit all skin types"
            safety_data["skin_types"] = ["normal", "oily"]
        else:
            safety_data["risk_level"] = "High"
            safety_data["risks"] = "High risk - patch test recommended"
            safety_data["skin_types"] = ["normal"]
        
        # Add known allergens
        safety_data["allergens"] = self._check_known_allergens(ingredient_name)
        
        return safety_data
    
    def get_comprehensive_ingredient_data(self, ingredient_name: str) -> Dict:
        """Get comprehensive ingredient data using INCIdecoder as primary source."""
        print(f"\n🔬 Analyzing {ingredient_name} with INCIdecoder...")
        
        # First check if we have cached table data from the product analysis
        cached_data = self.get_ingredient_data_from_cache(ingredient_name)
        if cached_data:
            print(f"   Using cached INCIdecoder table data")
            return cached_data
        
        # Try to get data from INCIdecoder ingredient page
        incidecoder_data = self.scrape_incidecoder_ingredient_safety(ingredient_name)
        
        # Check if we got meaningful data from INCIdecoder (not just defaults)
        if incidecoder_data:
            # Debug print to see what we're checking
            print(f"   Checking data: score={incidecoder_data.get('safety_score')}, allergens={incidecoder_data.get('allergens')}, function={incidecoder_data.get('function')}")
            
            has_meaningful_data = (
                incidecoder_data.get("function") != "Unknown" or 
                incidecoder_data.get("benefits") != "No data available" or
                len(incidecoder_data.get("allergens", [])) > 0 or
                abs(incidecoder_data.get("safety_score", 3) - 3) > 0.1  # Check if score is meaningfully different from 3
            )
            
            if has_meaningful_data:
                print(f"   Using INCIdecoder data")
                # Ensure safety_score is always an integer
                incidecoder_data["safety_score"] = int(incidecoder_data["safety_score"])
                return incidecoder_data
        
        # Fallback to intelligent scoring
        print(f"   Using fallback intelligent scoring")
        fallback_data = self._get_fallback_safety_score_dict(ingredient_name)
        # Ensure safety_score is always an integer
        fallback_data["safety_score"] = int(fallback_data["safety_score"])
        return fallback_data

    def get_ingredient_data_from_cache(self, ingredient_name: str) -> Dict:
        """Get ingredient data from cached table data if available."""
        if hasattr(self, 'ingredient_ratings_cache') and ingredient_name in self.ingredient_ratings_cache:
            cached_data = self.ingredient_ratings_cache[ingredient_name]
            
            # Convert to standard format
            return {
                "safety_score": int(cached_data["safety_score"]),
                "risk_level": self._get_risk_level_from_score(cached_data["safety_score"]),
                "function": cached_data["function"],
                "benefits": self._get_benefits_from_function(cached_data["function"]),
                "risks": self._get_risks_from_ratings(cached_data["irritancy"], cached_data["comedogenicity"]),
                "allergens": self._get_allergens_from_ratings(cached_data["irritancy"], ingredient_name),
                "skin_types": self._get_skin_types_from_ratings(cached_data["comedogenicity"], cached_data["irritancy"]),
                # Include raw INCIdecoder ratings for transparency
                "irritancy": cached_data["irritancy"],
                "comedogenicity": cached_data["comedogenicity"], 
                "overall_rating": cached_data["overall_rating"],
                "source": cached_data.get("source", "INCIdecoder_table")
            }
        
        return None

    def _get_risk_level_from_score(self, score: int) -> str:
        """Convert numeric score to risk level."""
        if score <= 2:
            return "Safe"
        elif score <= 4:
            return "Medium"
        else:
            return "High"

    def _get_benefits_from_function(self, function: str) -> str:
        """Generate benefits description from function."""
        function_lower = function.lower()
        
        if 'sunscreen' in function_lower:
            return "Provides UV protection and prevents sun damage"
        elif 'moisturizer' in function_lower or 'humectant' in function_lower:
            return "Hydrates and moisturizes the skin"
        elif 'emollient' in function_lower:
            return "Softens and smooths skin texture"
        elif 'solvent' in function_lower:
            return "Helps dissolve other ingredients and improve texture"
        elif 'viscosity' in function_lower:
            return "Improves product texture and consistency"
        elif 'skin brightening' in function_lower:
            return "Helps brighten skin tone and reduce dark spots"
        elif 'anti-acne' in function_lower:
            return "Helps treat and prevent acne breakouts"
        else:
            return function

    def _get_risks_from_ratings(self, irritancy: int, comedogenicity: int) -> str:
        """Generate risk description from INCIdecoder's 0-5 ratings."""
        risks = []
        
        # Irritancy scale (0-5): 0=None, 1-2=Low, 3-4=Moderate, 5=High
        if irritancy >= 4:
            risks.append("high risk of skin irritation")
        elif irritancy >= 3:
            risks.append("moderate risk of skin irritation")
        elif irritancy >= 1:
            risks.append("low risk of skin irritation")
        
        # Comedogenicity scale (0-5): 0=Non-comedogenic, 1-2=Low, 3-4=Moderate, 5=High
        if comedogenicity >= 4:
            risks.append("high risk of clogging pores and causing acne")
        elif comedogenicity >= 3:
            risks.append("moderate risk of clogging pores")
        elif comedogenicity >= 1:
            risks.append("slight pore-clogging potential")
        
        if risks:
            return "INCIdecoder ratings indicate this ingredient " + " and ".join(risks) + "."
        else:
            return "INCIdecoder rates this ingredient as non-irritating and non-comedogenic."

    def _get_allergens_from_ratings(self, irritancy: int, ingredient_name: str) -> List[str]:
        """Determine allergens from ratings and ingredient name."""
        allergens = []
        
        if irritancy >= 3:
            allergens.append("irritant")
        
        # Add known allergens from ingredient name
        allergens.extend(self._check_known_allergens(ingredient_name))
        
        return list(set(allergens))

    def _get_skin_types_from_ratings(self, comedogenicity: int, irritancy: int) -> List[str]:
        """Determine suitable skin types from INCIdecoder's 0-5 ratings."""
        skin_types = []
        
        # Based on comedogenicity (pore-clogging potential)
        if comedogenicity >= 4:
            skin_types = ["dry"]  # Only suitable for very dry skin
        elif comedogenicity >= 3:
            skin_types = ["normal", "dry"]  # Avoid for oily/acne-prone
        elif comedogenicity >= 1:
            skin_types = ["normal", "combination"]  # Some caution for oily skin
        else:
            skin_types = ["all"]  # Non-comedogenic, suitable for all
        
        # Adjust based on irritancy
        if irritancy >= 4:
            skin_types = [st for st in skin_types if st != "sensitive"]  # Remove sensitive
            if not skin_types:
                skin_types = ["normal"]
        elif irritancy >= 3:
            skin_types = [st for st in skin_types if st not in ["sensitive", "all"]]
            if "all" in skin_types:
                skin_types = ["normal", "oily", "combination"]
        elif irritancy == 0 and comedogenicity == 0:
            skin_types = ["all", "sensitive"]  # Perfect for everyone
        
        return skin_types if skin_types else ["normal"]

    def _get_cosmetic_benefits(self, ingredient_name: str) -> str:
        """Get cosmetic benefits based on ingredient name."""
        ingredient_lower = ingredient_name.lower()
        
        if 'water' in ingredient_lower or 'aqua' in ingredient_lower:
            return "Base ingredient that provides hydration and helps dissolve other ingredients"
        elif 'glycerin' in ingredient_lower:
            return "Powerful humectant that attracts moisture to the skin"
        elif 'acid' in ingredient_lower:
            return "May help with exfoliation and skin renewal"
        elif 'oil' in ingredient_lower:
            return "Provides moisturization and may help strengthen skin barrier"
        elif 'extract' in ingredient_lower:
            return "Plant-derived ingredient that may provide antioxidant benefits"
        else:
            return "Cosmetic ingredient with specific formulation purposes"

    def _extract_ingredient_table_data(self, soup) -> Dict[str, Dict]:
        """Extract ingredient data from INCIdecoder's ingredient table."""
        ingredients_data = {}
        
        try:
            # Look for the main ingredient table
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                # Skip if not enough rows (header + data)
                if len(rows) < 2:
                    continue
                
                # Check if this looks like an ingredient table
                header_row = rows[0]
                headers = [th.get_text().strip().lower() for th in header_row.find_all(['th', 'td'])]
                
                # Look for expected column headers
                has_ingredient_col = any('ingredient' in h or 'name' in h for h in headers)
                has_function_col = any('what' in h or 'function' in h or 'does' in h for h in headers)
                has_rating_col = any('rating' in h or 'irr' in h or 'com' in h for h in headers)
                
                if has_ingredient_col or (has_function_col and has_rating_col):
                    print(f"Found ingredient table with headers: {headers}")
                    
                    # Process data rows
                    for row in rows[1:]:  # Skip header row
                        cells = row.find_all(['td', 'th'])
                        
                        if len(cells) >= 3:  # Need at least ingredient name + some data
                            ingredient_name = cells[0].get_text().strip()
                            
                            # Skip empty or invalid ingredient names
                            if not ingredient_name or len(ingredient_name) > 50:
                                continue
                            
                            # Extract function/what-it-does
                            function = cells[1].get_text().strip() if len(cells) > 1 else "Unknown"
                            
                            # Extract ratings from the remaining cells
                            irritancy = 0
                            comedogenicity = 0
                            overall_rating = "Unknown"
                            
                            # Look for numeric ratings in cells
                            for i, cell in enumerate(cells[2:], 2):  # Start from 3rd cell
                                cell_text = cell.get_text().strip()
                                
                                # Check for numeric ratings (0-5 scale typically)
                                numbers = re.findall(r'\b([0-5])\b', cell_text)
                                if numbers:
                                    if i == 2:  # Typically irritancy column
                                        irritancy = int(numbers[0])
                                    elif i == 3:  # Typically comedogenicity column
                                        comedogenicity = int(numbers[0])
                                
                                # Check for text ratings like "Goodie", "Superstar"
                                if any(word in cell_text.lower() for word in ['goodie', 'superstar', 'icky']):
                                    overall_rating = cell_text
                            
                            # Convert INCIdecoder's raw ratings to safety score
                            safety_score = self._convert_incidecoder_to_safety_score(
                                irritancy, comedogenicity, overall_rating, function
                            )
                            
                            ingredients_data[ingredient_name] = {
                                "function": function,
                                "irritancy": irritancy,  # INCIdecoder's raw 0-5 rating
                                "comedogenicity": comedogenicity,  # INCIdecoder's raw 0-5 rating
                                "overall_rating": overall_rating,  # INCIdecoder's text rating
                                "safety_score": safety_score,  # Converted to 0-10 scale
                                "source": "INCIdecoder_table"
                            }
                            
                            print(f"  {ingredient_name}: irr={irritancy}, com={comedogenicity}, rating={overall_rating}, safety={safety_score}")
                    
                    # If we found ingredient data, return it
                    if ingredients_data:
                        return ingredients_data
            
        except Exception as e:
            print(f"Table extraction error: {e}")
        
        return ingredients_data

    def _convert_incidecoder_to_safety_score(self, irritancy: int, comedogenicity: int, 
                                           overall_rating: str, function: str) -> int:
        """Convert INCIdecoder's raw ratings directly to our safety score scale."""
        
        # Use INCIdecoder's irritancy rating directly (0-5 scale)
        # Convert to our 0-10 scale: multiply by 2 for direct mapping
        irritancy_score = irritancy * 2  # 0->0, 1->2, 2->4, 3->6, 4->8, 5->10
        
        # Use INCIdecoder's comedogenicity rating directly (0-5 scale)  
        comedogenicity_score = comedogenicity * 2  # Same scaling
        
        # Take the higher of the two scores as base (worse rating determines safety)
        base_score = max(irritancy_score, comedogenicity_score)
        
        # Adjust based on INCIdecoder's overall rating
        rating_lower = overall_rating.lower()
        if 'superstar' in rating_lower:
            base_score = max(0, base_score - 2)  # Superstar ingredients are safer
        elif 'goodie' in rating_lower:
            base_score = max(0, base_score - 1)  # Good ingredients are safer
        elif 'icky' in rating_lower:
            base_score = min(10, base_score + 2)  # Icky ingredients are riskier
        
        # Ensure we stay in 0-10 range
        return max(0, min(10, base_score))

    def _extract_incidecoder_ratings_from_table(self, table) -> Dict:
        """Extract INCIdecoder's raw irritancy and comedogenicity ratings from table."""
        ratings = {}
        
        try:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    header = cells[0].get_text().lower().strip()
                    value_text = cells[1].get_text().strip()
                    
                    # Look for irritancy rating
                    if any(term in header for term in ['irritan', 'irrit']):
                        numbers = re.findall(r'\b([0-5])\b', value_text)
                        if numbers:
                            ratings['irritancy'] = int(numbers[0])
                    
                    # Look for comedogenic rating
                    elif any(term in header for term in ['comedogenic', 'acne', 'pore']):
                        numbers = re.findall(r'\b([0-5])\b', value_text)
                        if numbers:
                            ratings['comedogenicity'] = int(numbers[0])
                    
                    # Look for overall rating
                    elif any(term in header for term in ['rating', 'overall', 'assessment']):
                        if any(word in value_text.lower() for word in ['goodie', 'superstar', 'icky']):
                            ratings['overall_rating'] = value_text
        
        except Exception as e:
            print(f"   Error extracting INCIdecoder ratings from table: {e}")
        
        return ratings