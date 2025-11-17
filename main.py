import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Product, Order

# Stripe
import stripe

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CartItem(BaseModel):
    slug: str
    quantity: int
    size: Optional[str] = None
    color: Optional[str] = None


@app.get("/")
def read_root():
    return {"message": "Duck Tees API ready"}


# Seed some demo products if none exist
SEED_PRODUCTS = [
    Product(
        title="Happy Duck Tee",
        description="Weiches Bio-T-Shirt mit fröhlicher Enten-Illustration.",
        price_cents=2499,
        category="T-Shirts",
        in_stock=True,
        slug="happy-duck-tee",
        images=[
            "https://images.unsplash.com/photo-1520975916090-3105956dac38?q=80&w=1200&auto=format&fit=crop",
        ],
        colors=["Forest Green", "Sky Blue", "Sunshine Yellow"],
        sizes=["S", "M", "L", "XL"],
        sku="DUCK-001",
    ),
    Product(
        title="Skater Duck Tee",
        description="Lässige Ente auf dem Skateboard – Style trifft Humor.",
        price_cents=2799,
        category="T-Shirts",
        in_stock=True,
        slug="skater-duck-tee",
        images=[
            "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?q=80&w=1200&auto=format&fit=crop",
        ],
        colors=["Charcoal", "Ocean", "Moss"],
        sizes=["S", "M", "L", "XL"],
        sku="DUCK-002",
    ),
    Product(
        title="Explorer Duck Tee",
        description="Abenteuerlustige Ente im Natur-Look.",
        price_cents=2999,
        category="T-Shirts",
        in_stock=True,
        slug="explorer-duck-tee",
        images=[
            "https://images.unsplash.com/photo-1503342452485-86ff0a8befe1?q=80&w=1200&auto=format&fit=crop",
        ],
        colors=["Leaf", "Stone", "Cloud"],
        sizes=["S", "M", "L", "XL"],
        sku="DUCK-003",
    ),
]


def ensure_seed_products():
    if db is None:
        return
    try:
        count = db["product"].count_documents({})
        if count == 0:
            for p in SEED_PRODUCTS:
                create_document("product", p)
    except Exception:
        pass


@app.get("/api/products")
def list_products():
    ensure_seed_products()
    products = get_documents("product")
    # Convert ObjectId to string if present
    for p in products:
        if "_id" in p:
            p["id"] = str(p.pop("_id"))
    return {"products": products}


@app.get("/api/products/{slug}")
def get_product(slug: str):
    prod = db["product"].find_one({"slug": slug}) if db else None
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    prod["id"] = str(prod.pop("_id"))
    return prod


@app.post("/api/create-checkout-session")
def create_checkout_session(items: List[CartItem]):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    line_items = []
    computed_total = 0
    order_items = []

    for item in items:
        prod = db["product"].find_one({"slug": item.slug}) if db else None
        if not prod:
            raise HTTPException(status_code=404, detail=f"Product {item.slug} not found")
        price_cents = int(prod.get("price_cents", 0))
        qty = max(1, int(item.quantity))
        computed_total += price_cents * qty
        order_items.append({
            "slug": item.slug,
            "title": prod.get("title"),
            "quantity": qty,
            "price_cents": price_cents,
            "size": item.size,
            "color": item.color,
        })
        line_items.append({
            "quantity": qty,
            "price_data": {
                "currency": prod.get("currency", "eur"),
                "unit_amount": price_cents,
                "product_data": {
                    "name": prod.get("title", "Duck Tee"),
                    "images": prod.get("images", [])[:1],
                },
            },
        })

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=line_items,
            success_url=f"{FRONTEND_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/cart",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # store order as pending
    try:
        create_document("order", Order(
            email="unknown",
            items=order_items,
            amount_total=computed_total,
            currency="eur",
            stripe_session_id=session.id,
        ))
    except Exception:
        pass

    return {"id": session.id, "url": session.url}


@app.get("/api/stripe/session/{session_id}")
def get_session_status(session_id: str):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return {
            "id": session.id,
            "payment_status": session.payment_status,
            "status": session.status,
            "amount_total": session.amount_total,
            "currency": session.currency,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db as _db
        if _db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = _db.name if hasattr(_db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = _db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
