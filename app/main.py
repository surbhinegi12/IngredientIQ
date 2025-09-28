from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import ProductRequest, ProductAnalysis, ClearCacheRequest
from .analyzer import SkincareAnalyzer
import os

app = FastAPI(
    title="AI-Powered Skincare & Makeup Ingredient Analyzer",
    description="Analyze skincare and makeup products for ingredient safety and get better alternatives",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = SkincareAnalyzer()

@app.get("/")
async def root():
    return {"message": "AI-Powered Skincare & Makeup Ingredient Analyzer API"}

@app.post("/analyze_product/", response_model=ProductAnalysis)
async def analyze_product(request: ProductRequest):
    """
    Analyze a skincare or makeup product for ingredient safety.
    
    - **product_name**: Name of the product to analyze
    
    Returns detailed analysis including:
    - Individual ingredient analysis with safety scores
    - Overall product safety score
    - Risk summary and allergen warnings
    - Alternative product recommendations
    """
    try:
        analysis = analyzer.analyze_product(request.product_name)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")



@app.post("/clear_cache/")
async def clear_cache(request: ClearCacheRequest):
    """Clear all cached data and start fresh. Requires admin password."""
    # Get admin password from environment variable
    admin_password = os.getenv("ADMIN_PASSWORD")
    
    if not admin_password:
        raise HTTPException(status_code=500, detail="Admin password not configured")
    
    if request.password != admin_password:
        raise HTTPException(status_code=401, detail="Invalid password")
    
    success = analyzer.clear_all_cache()
    if success:
        return {"message": "All cache cleared successfully!"}
    else:
        raise HTTPException(status_code=500, detail="Failed to clear cache")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)