from __future__ import annotations

from typing import List, Optional
from typing import Literal
from pydantic import BaseModel, Field

class WebsiteTypeClassifier(BaseModel):
    """Schema for website classification"""
    site_type: Literal[
        "ecommerce",
        "blog",
        "news_portal",
        "wiki",
        "forum",
        "corporate",
        "directory",
        "government",
        "education",
        "developer_platform",
        "social_media",
        "saas_tool",
        "portfolio_personal"
    ]
    """The type of the website."""


class CardMapping(BaseModel):
    title: Optional[str] = Field(
        default=None,
        description="Relative selector(s) for the card title (comma-separated allowed).",
    )
    price: Optional[str] = Field(
        default=None,
        description="Relative selector(s) for the card price (comma-separated allowed).",
    )
    image: Optional[str] = Field(
        default=None,
        description="Relative selector(s) for the card image (comma-separated allowed).",
    )
    link: Optional[str] = Field(
        default=None,
        description="Relative selector(s) for the primary link (comma-separated allowed).",
    )


class CardMappingResult(BaseModel):
    candidates: List[CardMapping] = Field(
        default_factory=list,
        description="Ordered mapping candidates returned by the LLM.",
    )


class SearchConditionModel(BaseModel):
    name: str = Field(..., description="Machine friendly condition name, e.g. price_max, brand.")
    value: str = Field(..., description="Human readable value to apply.")
    apply_via: str = Field(..., description='"keyword" or "filter".')


class SearchIntentSchema(BaseModel):
    keyword: str = Field(default="udgu")
    conditions: List[SearchConditionModel] = Field(default_factory=list)
