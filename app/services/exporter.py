# exporter.py

import json 
import os
import pandas as pd

from loguru import logger
from app.core.config import OUTPUT_DIR

os.makedirs(OUTPUT_DIR, exist_ok=True)

def save_to_json(data: str, filename: str = "result.json"):
    """
    Save data to a JSON file inside outputs/.
    """
    try:
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Results saved to {path}")
    except Exception as e:
        logger.error(f"❌ Failed to save JSON: {e}")
        return ""
    
def save_to_csv(data: dict, filename: str = "result.csv") -> str:
    """
    Save data to a CSV file inside outputs/.
    Expects data like {"data": [ {...}, {...} ]}
    """
    path = os.path.join(OUTPUT_DIR, filename)
    try:
        if "data" in data and isinstance(data["data"], list):
            df = pd.DataFrame(data["data"])
            df.to_csv(path, index=False, encoding="utf-8")
            logger.info(f"✅ Results saved to {path}")
            return path
        else:
            logger.warning("⚠️ No 'data' key found in result, skipping CSV export.")
            return ""
    except Exception as e:
        logger.error(f"❌ Failed to save CSV: {e}")
        return ""