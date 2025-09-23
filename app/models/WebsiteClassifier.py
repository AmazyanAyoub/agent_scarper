from typing import Literal
from pydantic import BaseModel

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