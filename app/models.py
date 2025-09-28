from pydantic import BaseModel
from typing import List, Optional

class Ingredient(BaseModel):
    name: str
    safety_score: int
    risk_level: str
    allergens: List[str]
    benefits: str
    risks: str
    skin_types: List[str]


class ProductAnalysis(BaseModel):
    product_name: str
    ingredients_analysis: List[Ingredient]
    overall_safety_score: float
    risk_summary: str
    allergen_warnings: List[str]
    alternatives: List[dict]

class ProductRequest(BaseModel):
    product_name: str

class ClearCacheRequest(BaseModel):
    password: str