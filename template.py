import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s]: %(message)s:')

project_name = "llm_scraper"

list_of_files = [
    # Core folders
    "app/__init__.py",
    "app/models/__init__.py",
    "app/models/extraction.py",
    "app/models/state.py",
    "app/services/__init__.py",
    "app/services/fetcher.py",
    "app/services/cleaner.py",
    "app/services/exporter.py",
    "app/services/llm_engine.py",
    "app/services/parser.py",
    "app/routes/__init__.py",
    "app/routes/cli.py",

    "core/__init__.py",
    "core/config.py",
    "core/logger.py",

    "pipeline/__init__.py",
    "pipeline/graph.py",

    "frontend/.gitkeep",  # empty for now

    "tests/__init__.py",
    "tests/test_pipeline.py",
    "tests/test_urls.json",

    "outputs/.gitkeep",

    # Root-level files
    ".env",
    ".gitignore",
    "requirements.txt",
    "environment.yml",
    "README.md",
    "main.py",
    "setup.py",
    "researches.ipynb",
]

for filepath in list_of_files:
    filepath = Path(filepath)
    filedir, filename = os.path.split(filepath)

    if filedir != "":
        os.makedirs(filedir, exist_ok=True)
        logging.info(f"Creating directory: {filedir} for the file: {filename}")

    if (not os.path.exists(filepath)) or (os.path.getsize(filepath) == 0):
        with open(filepath, "w") as f:
            pass
        logging.info(f"Creating empty file: {filepath}")
    else:
        logging.info(f"{filename} already exists")
