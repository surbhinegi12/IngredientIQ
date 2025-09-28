import google.generativeai as genai
import os
from typing import Dict, List
class GeminiClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        else:
            self.model = None
    

    
    def _enhance_with_gemini(self, ingredient_name: str, base_data: Dict) -> Dict:
        """Enhance ingredient data with Gemini analysis."""
        prompt = f"""
        Provide cosmetic benefits and risks for the ingredient "{ingredient_name}".
        Current safety score: {base_data['safety_score']}
        
        Respond with:
        Benefits: [specific cosmetic benefits]
        Risks: [potential risks or side effects]
        """
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Parse Gemini response and update base_data
            if "Benefits:" in response_text:
                benefits_match = response_text.split("Benefits:")[1].split("Risks:")[0].strip()
                if benefits_match and len(benefits_match) > 10:
                    base_data["benefits"] = benefits_match
            
            if "Risks:" in response_text:
                risks_match = response_text.split("Risks:")[1].strip()
                if risks_match and len(risks_match) > 5:
                    base_data["risks"] = risks_match
                    
        except Exception as e:
            print(f"Gemini enhancement error: {e}")
        
        return base_data
    
    def suggest_alternatives(self, product_analysis: Dict) -> List[Dict]:
        """Use Gemini to suggest alternative products with similar ingredients but better safety."""
        if not self.model:
            print("⚠️  Gemini API not configured - skipping AI alternatives")
            return []
        
        # Extract key information from the analysis
        product_name = product_analysis.get("product_name", "")
        ingredients_analysis = product_analysis.get("ingredients_analysis", [])
        overall_safety_score = product_analysis.get("overall_safety_score", 0)
        allergen_warnings = product_analysis.get("allergen_warnings", [])
        
        # Categorize ingredients by safety
        safe_ingredients = [ing for ing in ingredients_analysis if ing["safety_score"] <= 3]
        risky_ingredients = [ing for ing in ingredients_analysis if ing["safety_score"] >= 6]
        
        # Create a detailed prompt for Gemini
        prompt = f"""
        Analyze this skincare product and suggest 3 better alternatives:

        **Current Product:** {product_name}
        **Overall Safety Score:** {overall_safety_score}/10 (lower is safer)
        **Main Concerns:** {', '.join(allergen_warnings) if allergen_warnings else 'None'}

        **Safe Ingredients (keep these):**
        {self._format_ingredients_for_prompt(safe_ingredients)}

        **Risky Ingredients (avoid these):**
        {self._format_ingredients_for_prompt(risky_ingredients)}

        **Product Function:** Based on the ingredients, this appears to be a {self._determine_product_type(ingredients_analysis)}

        Please suggest 3 alternative products that:
        1. Serve the same purpose as the original product
        2. Include similar beneficial ingredients from the "safe" list
        3. Avoid or minimize the risky ingredients
        4. Have better overall safety profiles
        5. Are actual commercial products available in the market

        Format each suggestion as:
        **Product Name:** [Actual product name]
        **Brand:** [Brand name]
        **Why it's better:** [Brief explanation of why it's safer]
        **Key safe ingredients:** [List 3-4 main beneficial ingredients]
        **Safety improvement:** [What risky ingredients it avoids]

        Only suggest real, commercially available products that you're confident exist.
        """
        
        try:
            print(f"🤖 Generating alternatives for {product_name}...")
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            print(f"📝 Gemini response length: {len(response_text)} characters")
            print(f"🔍 First 200 chars of response: {response_text[:200]}")
            
            # Parse the response into structured alternatives
            alternatives = self._parse_alternatives_response(response_text)
            print(f"✅ Parsed {len(alternatives)} alternatives from Gemini")
            
            if len(alternatives) == 0 and len(response_text) > 100:
                print("⚠️  Response has content but no alternatives parsed - checking format...")
                print(f"🔍 Response preview: {response_text[:500]}")
                
                # Create simple fallback alternatives from the response text
                alternatives = self._create_fallback_alternatives(response_text, product_analysis)
            
            return alternatives
            
        except Exception as e:
            print(f"❌ Error generating alternatives: {e}")
            return []
    
    def _format_ingredients_for_prompt(self, ingredients_list: List[Dict]) -> str:
        """Format ingredients list for the Gemini prompt."""
        if not ingredients_list:
            return "None"
        
        formatted = []
        for ing in ingredients_list[:5]:  # Limit to top 5 to avoid prompt bloat
            formatted.append(f"- {ing['name']} (Score: {ing['safety_score']}/10) - {ing['benefits']}")
        
        return '\n'.join(formatted)
    
    def _determine_product_type(self, ingredients_analysis: List[Dict]) -> str:
        """Determine the type of product based on ingredients."""
        ingredient_names = [ing['name'].lower() for ing in ingredients_analysis]
        
        # Check for product type indicators
        if any('oil' in name for name in ingredient_names):
            if any('sunflower' in name or 'jojoba' in name or 'argan' in name for name in ingredient_names):
                return "facial or body oil/serum"
        
        if any('acid' in name for name in ingredient_names):
            return "exfoliating treatment or serum"
        
        if any('sunscreen' in name or 'spf' in name for name in ingredient_names):
            return "sunscreen or UV protection product"
        
        if 'glycerin' in ingredient_names and any('cream' in name or 'moistur' in name for name in ingredient_names):
            return "moisturizer or hydrating cream"
        
        # Default based on common ingredients
        if 'fragrance' in ingredient_names or 'parfum' in ingredient_names:
            return "scented cosmetic product"
        
        return "skincare product"
    
    def _parse_alternatives_response(self, response_text: str) -> List[Dict]:
        """Parse Gemini's response into structured alternative product data."""
        alternatives = []
        
        try:
            # Try multiple parsing strategies
            
            # Strategy 1: Look for **Product Name:** pattern
            sections = response_text.split('**Product Name:**')
            if len(sections) > 1:
                alternatives = self._parse_structured_format(sections)
            
            # Strategy 2: Look for numbered list format (1., 2., 3.)
            if not alternatives:
                alternatives = self._parse_numbered_format(response_text)
            
            # Strategy 3: Look for product names in bold or other formats
            if not alternatives:
                alternatives = self._parse_flexible_format(response_text)
            
        except Exception as e:
            print(f"Error parsing alternatives response: {e}")
        
        return alternatives[:3]  # Return max 3 alternatives

    def _parse_structured_format(self, sections: List[str]) -> List[Dict]:
        """Parse structured format with **Field:** markers."""
        alternatives = []
        
        for section in sections[1:]:  # Skip first empty section
            try:
                alternative = {}
                lines = section.strip().split('\n')
                
                # Extract product name (first line)
                product_name = lines[0].strip().replace('*', '').strip()
                alternative['name'] = product_name
                
                # Extract other fields
                current_field = None
                current_content = []
                
                for line in lines[1:]:
                    line = line.strip()
                    if line.startswith('**') and (':**' in line or line.endswith('**')):
                        # Save previous field
                        if current_field and current_content:
                            alternative[current_field] = ' '.join(current_content).strip()
                        # Start new field
                        field_name = line.replace('**', '').replace(':', '').lower().replace(' ', '_')
                        current_field = field_name
                        current_content = []
                    elif line and current_field:
                        current_content.append(line)
                
                # Save last field
                if current_field and current_content:
                    alternative[current_field] = ' '.join(current_content).strip()
                
                # Only add if we have a name
                if alternative.get('name') and len(alternative.get('name', '')) > 3:
                    alternatives.append(alternative)
                    
            except Exception as e:
                print(f"Error parsing structured alternative: {e}")
                continue
        
        return alternatives

    def _parse_numbered_format(self, response_text: str) -> List[Dict]:
        """Parse numbered list format (1. Product Name, 2. Product Name, etc.)."""
        alternatives = []
        
        try:
            # Split by numbered items
            import re
            pattern = r'\d+\.\s*([^\n]+)'
            matches = re.findall(pattern, response_text)
            
            for match in matches:
                product_name = match.strip().replace('**', '').strip()
                if len(product_name) > 3:
                    alternatives.append({
                        'name': product_name,
                        'brand': 'Various',
                        'why_it_s_better': 'Recommended alternative with better safety profile',
                        'source': 'gemini_numbered'
                    })
        
        except Exception as e:
            print(f"Error parsing numbered format: {e}")
        
        return alternatives

    def _parse_flexible_format(self, response_text: str) -> List[Dict]:
        """Parse flexible format by looking for product names and brands."""
        alternatives = []
        
        try:
            # Look for common brand names and product patterns
            lines = response_text.split('\n')
            
            for line in lines:
                line = line.strip()
                # Skip empty lines or lines that are too short
                if len(line) < 10:
                    continue
                
                # Look for lines that might contain product names
                if any(indicator in line.lower() for indicator in ['cream', 'serum', 'moisturizer', 'lotion', 'cleanser']):
                    # Clean up the line
                    product_line = line.replace('*', '').replace('-', '').strip()
                    
                    # Try to extract brand and product name
                    if any(brand in product_line for brand in ['CeraVe', 'Neutrogena', 'Olay', 'Cetaphil', 'La Roche', 'Eucerin']):
                        alternatives.append({
                            'name': product_line,
                            'brand': 'Various',
                            'why_it_s_better': 'Alternative with potentially better safety profile',
                            'source': 'gemini_flexible'
                        })
        
        except Exception as e:
            print(f"Error parsing flexible format: {e}")
        
        return alternatives

    def _create_fallback_alternatives(self, response_text: str, product_analysis: Dict) -> List[Dict]:
        """Create fallback alternatives when parsing fails but we have a response."""
        alternatives = []
        
        try:
            # Extract any product names mentioned in the response
            import re
            
            # Common skincare brands to look for
            brands = ['CeraVe', 'Neutrogena', 'Olay', 'Cetaphil', 'La Roche-Posay', 'Eucerin', 
                     'Aveeno', 'Vanicream', 'First Aid Beauty', 'Paula\'s Choice']
            
            # Look for brand mentions
            found_products = []
            for brand in brands:
                if brand.lower() in response_text.lower():
                    # Try to find the product name near the brand
                    pattern = rf'{re.escape(brand)}[^.]*?(?:cream|lotion|serum|moisturizer|cleanser)'
                    matches = re.findall(pattern, response_text, re.IGNORECASE)
                    for match in matches:
                        if len(match) < 100:  # Reasonable product name length
                            found_products.append(match.strip())
            
            # Create alternatives from found products
            for i, product in enumerate(found_products[:3]):
                alternatives.append({
                    'name': product,
                    'brand': 'Various',
                    'why_it_s_better': f'Alternative #{i+1} suggested by AI for better safety profile',
                    'source': 'gemini_fallback'
                })
            
            # If still no alternatives, create generic ones based on product type
            if not alternatives:
                product_type = self._determine_product_type(product_analysis.get('ingredients_analysis', []))
                alternatives = self._create_generic_alternatives(product_type)
        
        except Exception as e:
            print(f"Error creating fallback alternatives: {e}")
        
        return alternatives

    def _create_generic_alternatives(self, product_type: str) -> List[Dict]:
        """Create generic alternatives based on product type."""
        generic_alternatives = {
            'moisturizer or hydrating cream': [
                {'name': 'CeraVe Daily Moisturizing Lotion', 'brand': 'CeraVe'},
                {'name': 'Neutrogena Hydro Boost Water Gel', 'brand': 'Neutrogena'},
                {'name': 'Cetaphil Daily Facial Moisturizer', 'brand': 'Cetaphil'}
            ],
            'facial or body oil/serum': [
                {'name': 'The Ordinary Squalane Oil', 'brand': 'The Ordinary'},
                {'name': 'Neutrogena Ultra Sheer Body Oil', 'brand': 'Neutrogena'},
                {'name': 'Olay Regenerist Micro-Sculpting Serum', 'brand': 'Olay'}
            ],
            'scented cosmetic product': [
                {'name': 'Unscented Alternative Body Lotion', 'brand': 'Various'},
                {'name': 'Fragrance-Free Moisturizer', 'brand': 'Various'},
                {'name': 'Sensitive Skin Formula', 'brand': 'Various'}
            ]
        }
        
        alternatives_list = generic_alternatives.get(product_type, generic_alternatives['moisturizer or hydrating cream'])
        
        for alt in alternatives_list:
            alt['why_it_s_better'] = 'Commonly recommended alternative with better safety profile'
            alt['source'] = 'generic_recommendation'
        
        return alternatives_list
    
    def generate_product_summary(self, product_name: str, ingredients: List[str], safety_score: float) -> str:
        """Generate a natural language summary of the product analysis."""
        if not self.model:
            return f"Analysis complete for {product_name}. Overall safety score: {safety_score}"
        
        prompt = f"""
        Create a brief, user-friendly summary for the skincare product "{product_name}" with these ingredients: {', '.join(ingredients)}.
        The overall safety score is {safety_score} (0-10 scale, lower is safer).
        
        Provide practical advice in 2-3 sentences about whether this product is recommended and why.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Product analyzed: {product_name}. Safety score: {safety_score}. Consider ingredients carefully."
    
