
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime, timezone
import requests
# from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()


@app.get("/")
def home():
    return {"message": "It works on Railway!!"}


# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["https://testingmarmorkrafts.store"],  
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # For DEv
# WC_API_URL = "https://testingmarmorkrafts.store/wp-json/wc/v3"
# WC_CONSUMER_KEY = "ck_fb05462837d9679c0f6c8b11ccbac57d09c79638"
# WC_CONSUMER_SECRET = "cs_cd485ed45fc41da284d567e0d49cb8a272fbe4f1"

# For Prod
WC_API_URL = "https://marmorkrafts.com/wp-json/wc/v3"
WC_CONSUMER_KEY = "ck_fb05462837d9679c0f6c8b11ccbac57d09c79638"
WC_CONSUMER_SECRET = "cs_cd485ed45fc41da284d567e0d49cb8a272fbe4f1"

# === Unified lookup endpoint ===
@app.get("/order-status/lookup/")
def lookup_order(input: str = Query(..., description="Order ID, Tracking Number, or Email")):
    input_str = input.strip()

    if input_str.isdigit():
        if len(input_str) > 10:
            return fetch_order_by_tracking_number(input_str)
        else:
            return fetch_order_by_id(int(input_str))
    elif "@" in input_str:
        return fetch_orders_by_email(input_str)
    else:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid input. Provide order ID, tracking number, or email address."}
        )

# === Original endpoint (optional) ===
@app.get("/order-status/")
def get_order_status(
    order_id: Optional[int] = Query(None),
    tracking_number: Optional[str] = Query(None),
    email: Optional[str] = Query(None)
):
    if order_id:
        return fetch_order_by_id(order_id)
    elif tracking_number:
        return fetch_order_by_tracking_number(tracking_number)
    elif email:
        return fetch_orders_by_email(email)
    else:
        return JSONResponse(
            status_code=400,
            content={"error": "Provide order_id, tracking_number, or email"}
        )

# === Fetch by order ID ===
def fetch_order_by_id(order_id: int):
    url = f"{WC_API_URL}/orders/{order_id}"
    response = requests.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))

    if response.status_code == 404:
        return JSONResponse(
            status_code=200,
            content={"status": "not_found", "message": "No order found with this order ID."}
        )

    elif response.status_code != 200:
        return JSONResponse(
            status_code=response.status_code,
            content={"error": "Failed to fetch order details"}
        )

    return format_order_response(response.json())

# === Search by tracking number ===
def fetch_order_by_tracking_number(tracking_number: str):
    per_page = 20
    page = 1
    max_pages = 10

    while page <= max_pages:
        url = f"{WC_API_URL}/orders?per_page={per_page}&page={page}"
        response = requests.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))

        if response.status_code != 200:
            return JSONResponse(
                status_code=response.status_code,
                content={"error": "Failed to fetch orders"}
            )

        orders = response.json()
        if not orders:
            break

        for order in orders:
            for meta in order.get("meta_data", []):
                if meta.get("key") == "_wc_shipment_tracking_items":
                    tracking_items = meta.get("value", [])
                    for item in tracking_items:
                        if item.get("tracking_number") == tracking_number:
                            return format_order_response(order)

        page += 1

    return JSONResponse(
        status_code=200,
        content={"status": "not_found", "message": "No order found with this tracking number."}
    )

# === Fetch by email ===
def fetch_orders_by_email(email: str):
    per_page = 20
    page = 1
    max_pages = 10
    matched_orders = []

    while page <= max_pages:
        url = f"{WC_API_URL}/orders?per_page={per_page}&page={page}"
        response = requests.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))

        if response.status_code != 200:
            return JSONResponse(
                status_code=response.status_code,
                content={"error": "Failed to fetch orders"}
            )

        orders = response.json()
        if not orders:
            break

        for order in orders:
            billing_email = order.get("billing", {}).get("email", "").lower()
            if billing_email == email.lower():
                matched_orders.append(format_order_object(order))

        page += 1

    if not matched_orders:
        return JSONResponse(
            status_code=200,
            content={"status": "not_found", "message": "No orders found for this email."}
        )

    return JSONResponse(content={"orders": matched_orders})

# === Format response for single order ===
def format_order_response(order_data):
    return JSONResponse(content=format_order_object(order_data))

# === Format structure (reusable) ===
def format_order_object(order_data):
    tracking_number = "Not available"
    for meta in order_data.get("meta_data", []):
        if meta.get("key") == "_wc_shipment_tracking_items":
            tracking_items = meta.get("value", [])
            if tracking_items:
                tracking_number = tracking_items[0].get("tracking_number", "Not available")
            break

    return {
        "@context": "https://schema.org",
        "@type": "Order",
        "order_number": order_data["number"],
        "status": order_data["status"],
        "currency": order_data["currency"],
        "total": order_data["total"],
        "shipping_method": order_data["shipping_lines"][0]["method_title"] if order_data["shipping_lines"] else "N/A",
        "billing_address": order_data["billing"],
        "shipping_address": order_data["shipping"],
        "tracking_number": tracking_number,
        "order_date": order_data["date_created"],
        "line_items": [
            {
                "name": item["name"],
                "quantity": item["quantity"],
                "price": item["price"],
                "sku": item.get("sku"),
                "image": item.get("image", {}).get("src")
            } for item in order_data["line_items"]
        ],
    }