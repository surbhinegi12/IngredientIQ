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
- **AI**: Google Gemini for ingredient analysis and natural language generation
- **Web Scraping**: BeautifulSoup for ingredient data extraction

## API Endpoints

### POST /analyze_product/

Analyze a skincare or makeup product for ingredient safety.(lower safety score, means lower risk ingredients/product)

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
