# config.py

from dotenv import load_dotenv
import os
from loguru import logger

# Load .env file
load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Project Settings
DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_PROVIDER = "groq"

# Debug check
if not GROQ_API_KEY:
    logger.warning("⚠️ GROQ_API_KEY not found in .env")