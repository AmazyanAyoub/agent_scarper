
from typing import Dict, Optional

from pydantic import BaseModel, Field


class Cards(BaseModel):
    """Container for a generic product/offer card."""

    name: str = Field(..., description="Primary title or headline")
    url: Optional[str] = Field(None, description="Canonical URL for the item")
    price_text: Optional[str] = Field(None, description="Price as displayed in the page")
    price_value: Optional[float] = Field(None, description="Numeric price when parsed")
    currency: Optional[str] = Field(None, description="ISO currency code or symbol")
    rating_value: Optional[float] = Field(None, description="Average rating value")
    reviews_count: Optional[int] = Field(None, description="Number of reviews or votes")
    description: Optional[str] = Field(None, description="Short descriptive snippet")
    image: Optional[str] = Field(None, description="Primary image URL if available")
    attributes: Dict[str, str] = Field(default_factory=dict, description="Extra site-specific attributes")
