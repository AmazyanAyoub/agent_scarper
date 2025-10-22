
# from typing import Dict, Optional

# from pydantic import BaseModel, Field


# class Cards(BaseModel):
#     """Container for a generic product/offer card."""

#     name: str = Field(..., description="Primary title or headline")
#     url: Optional[str] = Field(None, description="Canonical URL for the item")
#     price_text: Optional[str] = Field(None, description="Price as displayed in the page")
#     price_value: Optional[float] = Field(None, description="Numeric price when parsed")
#     currency: Optional[str] = Field(None, description="ISO currency code or symbol")
#     rating_value: Optional[float] = Field(None, description="Average rating value")
#     reviews_count: Optional[int] = Field(None, description="Number of reviews or votes")
#     description: Optional[str] = Field(None, description="Short descriptive snippet")
#     image: Optional[str] = Field(None, description="Primary image URL if available")
#     attributes: Dict[str, str] = Field(default_factory=dict, description="Extra site-specific attributes")

# models/venues.py
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class Cards(BaseModel):
    """
    Generic listing 'card' that fits products, venues, jobs, etc.
    All fields are optional; we keep it flexible.
    """
    # Core identity
    title: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None

    # Commerce-ish
    price: Optional[str] = None
    currency: Optional[str] = None
    availability: Optional[str] = None
    location: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    category: Optional[str] = None

    # Quality / social proof
    rating: Optional[float] = None
    reviews_count: Optional[int] = Field(default=None, alias="reviews")

    # Seller / meta
    seller: Optional[str] = None
    seller_rating: Optional[float] = None

    # Arbitrary attributes/specs
    specs: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True  # let "reviews" map into reviews_count
