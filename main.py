import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="Gamers Heaven API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Models ----------
class ProductIn(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    category: str
    platform: str
    image_url: Optional[str] = None
    rating: Optional[float] = Field(4.5, ge=0, le=5)
    stock: int = Field(100, ge=0)


class ProductOut(ProductIn):
    id: str


# ---------- Helpers ----------

def _doc_to_product(doc) -> ProductOut:
    return ProductOut(
        id=str(doc.get("_id")),
        title=doc.get("title"),
        description=doc.get("description"),
        price=doc.get("price"),
        category=doc.get("category"),
        platform=doc.get("platform"),
        image_url=doc.get("image_url"),
        rating=doc.get("rating", 4.5),
        stock=doc.get("stock", 0),
    )


# ---------- Routes ----------
@app.get("/")
def read_root():
    return {"message": "Gamers Heaven API running"}


@app.get("/test")
def test_database():
    status = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "collections": []
    }
    try:
        if db is None:
            status["database"] = "❌ Not Connected"
        else:
            status["database"] = "✅ Connected"
            status["collections"] = db.list_collection_names()
    except Exception as e:
        status["database"] = f"⚠️ {str(e)[:80]}"
    return status


@app.get("/api/products", response_model=List[ProductOut])
def list_products(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    filter_q = {}
    if q:
        filter_q["title"] = {"$regex": q, "$options": "i"}
    if category:
        filter_q["category"] = category
    if platform:
        filter_q["platform"] = platform

    docs = get_documents("product", filter_q, limit)
    return [_doc_to_product(d) for d in docs]


@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(product_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        doc = db["product"].find_one({"_id": ObjectId(product_id)})
    except Exception:
        doc = None
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return _doc_to_product(doc)


@app.get("/api/categories", response_model=List[str])
def get_categories():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    cats = db["product"].distinct("category")
    return sorted([c for c in cats if c])


@app.get("/api/platforms", response_model=List[str])
def get_platforms():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    plats = db["product"].distinct("platform")
    return sorted([p for p in plats if p])


@app.post("/api/products", response_model=str)
def create_product(product: ProductIn):
    new_id = create_document("product", product)
    return new_id


# ---------- Seed sample data on startup if empty ----------
@app.on_event("startup")
def seed_products():
    if db is None:
        return
    count = db["product"].count_documents({})
    if count > 0:
        return

    samples = [
        {
            "title": "Elden Ring Runes",
            "description": "Fast delivery of in-game currency to boost your journey across the Lands Between.",
            "price": 19.99,
            "category": "Currency",
            "platform": "PC",
            "image_url": "https://images.unsplash.com/photo-1605901309584-818e25960a8f?q=80&w=1200&auto=format&fit=crop",
            "rating": 4.9,
            "stock": 999,
        },
        {
            "title": "GTA Online Money",
            "description": "Top up your GTA$ balance with trusted, secure delivery.",
            "price": 24.99,
            "category": "Currency",
            "platform": "PS5",
            "image_url": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?q=80&w=1200&auto=format&fit=crop",
            "rating": 4.7,
            "stock": 800,
        },
        {
            "title": "FIFA Ultimate Team Coins",
            "description": "Build your dream squad with instant coin delivery.",
            "price": 14.99,
            "category": "Coins",
            "platform": "Xbox",
            "image_url": "https://images.unsplash.com/photo-1543326727-cf6c39b4479f?q=80&w=1200&auto=format&fit=crop",
            "rating": 4.6,
            "stock": 1200,
        },
        {
            "title": "Valorant Points Top-up",
            "description": "Secure VP top-up for skins and battle passes.",
            "price": 9.99,
            "category": "Top-up",
            "platform": "PC",
            "image_url": "https://images.unsplash.com/photo-1607252650355-f7fd0460ccdb?q=80&w=1200&auto=format&fit=crop",
            "rating": 4.8,
            "stock": 500,
        },
    ]

    for s in samples:
        db["product"].insert_one(s)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
