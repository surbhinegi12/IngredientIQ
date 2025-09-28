# AI-Powered Skincare & Makeup Ingredient Analyzer

An AI-powered web application that analyzes skincare and makeup products for ingredient safety, provides detailed ingredient analysis, and suggests safer alternatives.

## Features

- **Ingredient Extraction**: Extract ingredients from product names
- **Safety Analysis**: Categorize ingredients by risk level and safety scores
- **Allergen Detection**: Identify common allergens and irritants
- **Product Alternatives**: Suggest safer products with better ingredient profiles
- **RESTful API**: FastAPI-based backend with Swagger documentation

## Tech Stack

- **Backend**: FastAPI
- **Database**: ChromaDB for vector storage
- **AI**: Google Gemini for ingredient analysis and natural language generation
- **NLP**: Sentence-Transformers for semantic search
- **Web Scraping**: BeautifulSoup for ingredient data extraction

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd skincare-analyzer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your Gemini API key
```

4. Run the application:
```bash
python run.py
```

4. Access the API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### POST /analyze_product/
Analyze a skincare or makeup product for ingredient safety.

**Request Body:**
```json
{
  "product_name": "Neutrogena Hydro Boost Water Gel"
}
```

**Response:**
```json
{
  "product_name": "Neutrogena Hydro Boost Water Gel",
  "ingredients_analysis": [
    {
      "name": "Water",
      "safety_score": 0,
      "risk_level": "Safe",
      "allergens": [],
      "benefits": "Hydrating base",
      "risks": "None",
      "skin_types": ["all"]
    }
  ],
  "overall_safety_score": 3.4,
  "risk_summary": "High-risk ingredients detected: Fragrance, Alcohol Denat. Consider alternatives.",
  "allergen_warnings": ["fragrance"],
  "alternatives": [
    {
      "name": "CeraVe Hydrating Cream",
      "safety_score": 1.0,
      "category": "moisturizer"
    }
  ]
}
```

### GET /ingredients/{ingredient_name}
Get detailed information about a specific ingredient.

### GET /alternatives/
Get product alternatives with safety scores below a threshold.

## Example Usage

```python
import requests

# Analyze a product
response = requests.post(
    "http://localhost:8000/analyze_product/",
    json={"product_name": "Neutrogena Hydro Boost"}
)
analysis = response.json()
print(f"Safety Score: {analysis['overall_safety_score']}")
```

## Project Structure

```
skincare-analyzer/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── models.py        # Pydantic models
│   ├── database.py      # ChromaDB integration
│   ├── scraper.py       # Web scraping utilities
│   └── analyzer.py      # Core analysis logic
├── requirements.txt
├── run.py
└── README.md
```

## Configuration

### Gemini API Setup
1. Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Add it to your `.env` file:
```
GEMINI_API_KEY=your_api_key_here
```

### Testing
Run the test script to verify everything works:
```bash
python test_api.py
```

## Future Enhancements

- Integration with real ingredient databases (EWG, CosDNA)
- Enhanced Gemini prompts for more accurate analysis
- User authentication and personalized recommendations
- Mobile app interface
- Batch product analysis