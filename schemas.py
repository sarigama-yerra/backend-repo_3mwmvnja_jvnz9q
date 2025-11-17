"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price_cents: int = Field(..., ge=0, description="Price in cents")
    currency: str = Field("eur", description="ISO currency code")
    category: str = Field("T-Shirts", description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")
    slug: str = Field(..., description="URL-friendly unique identifier")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    colors: List[str] = Field(default_factory=list, description="Available colors")
    sizes: List[str] = Field(default_factory=lambda: ["S","M","L","XL"], description="Available sizes")
    sku: Optional[str] = Field(None, description="Stock keeping unit")

class Order(BaseModel):
    """Orders collection schema"""
    email: str = Field(..., description="Customer email")
    items: list = Field(..., description="List of purchased items")
    amount_total: int = Field(..., ge=0, description="Total amount in cents")
    currency: str = Field("eur", description="Currency")
    stripe_session_id: Optional[str] = Field(None, description="Stripe checkout session id")
