
from fastapi import FastAPI
import requests
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta

app = FastAPI()


@app.get("/")
def home():
    return {"message": "It works on Railway!!"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://testingmarmorkrafts.store"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# For DEv
WC_API_URL = "https://testingmarmorkrafts.store/wp-json/wc/v3"
WC_CONSUMER_KEY = "ck_fb05462837d9679c0f6c8b11ccbac57d09c79638"
WC_CONSUMER_SECRET = "cs_cd485ed45fc41da284d567e0d49cb8a272fbe4f1"

# # For Prod
# WC_API_URL = "https://marmorkrafts.com/wp-json/wc/v3"
# WC_CONSUMER_KEY = "ck_fb05462837d9679c0f6c8b11ccbac57d09c79638"
# WC_CONSUMER_SECRET = "cs_cd485ed45fc41da284d567e0d49cb8a272fbe4f1"

@app.get("/products/new-arrivals")
def get_new_arrivals():
    url = f"{WC_API_URL}/products?orderby=modified&order=desc&per_page=8"
    response = requests.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))

    if response.status_code != 200:
        return JSONResponse(
            status_code=response.status_code,
            content={"error": "Failed to fetch new arrivals"}
        )

    data = response.json()

    formatted = {
        "@context": "https://schema.org",
        "@type": "Collection",
        "name": "New Arrivals",
        "members": []
    }

    for item in data:
        formatted["members"].append({
            "@type": "Product",
            "name": item["name"],
            "url": item["permalink"],
            "image": {
                "@type": "ImageObject",
                "url": item["images"][0]["src"] if item.get("images") and item["images"] else ""
            },
            "price": item.get("price"),
            "description": item.get("short_description", "")
        })

    return JSONResponse(content=formatted)

@app.get("/products/trending")
def get_trending_products():
    
    thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()

   
    orders_url = f"{WC_API_URL}/orders?after={thirty_days_ago}&per_page=100"
    orders_response = requests.get(orders_url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))

    if orders_response.status_code != 200:
        return JSONResponse(
            status_code=orders_response.status_code,
            content={"error": "Failed to fetch recent orders"}
        )

    orders = orders_response.json()

    
    product_ids = set()
    for order in orders:
        for item in order.get("line_items", []):
            product_ids.add(str(item.get("product_id")))

    if not product_ids:
        return JSONResponse(content={"message": "No trending products found"})

    
    ids_str = ",".join(product_ids)
    products_url = f"{WC_API_URL}/products?include={ids_str}&per_page=100"
    products_response = requests.get(products_url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))

    if products_response.status_code != 200:
        return JSONResponse(
            status_code=products_response.status_code,
            content={"error": "Failed to fetch trending products"}
        )

    products = products_response.json()

    formatted = {
        "@context": "https://schema.org",
        "@type": "Collection",
        "name": "Trending Products",
        "members": []
    }

    for item in products:
        formatted["members"].append({
            "@type": "Product",
            "name": item["name"],
            "url": item["permalink"],
            "image": {
                "@type": "ImageObject",
                "url": item["images"][0]["src"] if item.get("images") and item["images"] else ""
            },
            "price": item.get("price"),
            "description": item.get("short_description", "")
        })

    return JSONResponse(content=formatted)
