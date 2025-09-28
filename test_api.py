import requests
import json

def test_api():
    base_url = "http://localhost:8000"
    
    # Test root endpoint
    print("Testing root endpoint...")
    response = requests.get(f"{base_url}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    
    # Test product analysis
    print("Testing product analysis...")
    test_product = {"product_name": "Neutrogena Hydro Boost Water Gel"}
    response = requests.post(f"{base_url}/analyze_product/", json=test_product)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        analysis = response.json()
        print(f"Product: {analysis['product_name']}")
        print(f"Safety Score: {analysis['overall_safety_score']}")
        print(f"Risk Summary: {analysis['risk_summary']}")
        print(f"Allergen Warnings: {analysis['allergen_warnings']}")
        print(f"Alternatives: {len(analysis['alternatives'])} found\n")
    else:
        print(f"Error: {response.text}\n")
    
    # Test ingredient lookup
    print("Testing ingredient lookup...")
    response = requests.get(f"{base_url}/ingredients/Water")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Ingredient data: {response.json()}\n")
    
    # Test alternatives
    print("Testing alternatives...")
    response = requests.get(f"{base_url}/alternatives/")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        alternatives = response.json()
        print(f"Found {len(alternatives['alternatives'])} alternatives")

if __name__ == "__main__":
    test_api()