import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow browser access (important)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Backend is running"}

# -------------------------
# 1) Find purchase ID by PO number
# -------------------------
@app.get("/orders")
def get_orders(po_number: str):
    ACCOUNT_ID = os.getenv("DEAR_ACCOUNT_ID")
    APPLICATION_KEY = os.getenv("DEAR_APPLICATION_KEY")

    if not ACCOUNT_ID or not APPLICATION_KEY:
        raise HTTPException(status_code=500, detail="API keys not configured")

    url = "https://inventory.dearsystems.com/ExternalApi/v2/PurchaseList"
    params = {"Page": 1, "Limit": 500}

    headers = {
        "api-auth-accountid": ACCOUNT_ID,
        "api-auth-applicationkey": APPLICATION_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    data = response.json()

    for purchase in data.get("PurchaseList", []):
        if purchase.get("OrderNumber") == po_number:
            return {"purchase_id": purchase.get("ID")}

    return {"error": "Purchase order not found"}

# -------------------------
# 2) Get full order details by purchase ID
# -------------------------
@app.get("/order-details")
def order_details(purchase_id: str):
    ACCOUNT_ID = os.getenv("DEAR_ACCOUNT_ID")
    APPLICATION_KEY = os.getenv("DEAR_APPLICATION_KEY")

    if not ACCOUNT_ID or not APPLICATION_KEY:
        raise HTTPException(status_code=500, detail="API keys not configured")

    url = f"https://inventory.dearsystems.com/ExternalApi/v2/advanced-purchase?ID={purchase_id}"

    headers = {
        "api-auth-accountid": ACCOUNT_ID,
        "api-auth-applicationkey": APPLICATION_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    data = response.json()

    # Build combined order + received quantities
    items = {}

    # Ordered quantities
    if "Order" in data and "Lines" in data["Order"]:
        for line in data["Order"]["Lines"]:
            sku = line.get("SKU")
            items[sku] = {
                "sku": sku,
                "name": line.get("Name"),
                "ordered": line.get("Quantity", 0),
                "received": 0
            }

    # Received / PutAway quantities
    if "PutAway" in data:
        for putaway in data["PutAway"]:
            for line in putaway.get("Lines", []):
                sku = line.get("SKU")
                if sku in items:
                    items[sku]["received"] += line.get("Quantity", 0)

    return list(items.values())