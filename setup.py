import os

# Define project structure
PROJECT_STRUCTURE = {
    "llm_scraper": {
        "files": ["main.py", "config.py"],
        "subdirs": {
            "utils": [
                "fetcher.py",
                "cleaner.py",
                "llm_engine.py",
                "parser.py",
                "exporter.py",
                "logger.py",
            ],
            "prompts": ["templates.py"],
            "interface": ["cli.py"],
            "tests": ["test_pipeline.py", "test_urls.json"],
        },
    },
    "root_files": ["requirements.txt", "README.md", ".gitignore"],
}

def create_files(base_path, files):
    """Helper to create files with boilerplate."""
    for f in files:
        path = os.path.join(base_path, f)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w") as file:
                if f.endswith(".py"):
                    file.write(f"# {f}\n")
                elif f.endswith(".md"):
                    file.write("# Project Documentation\n")
                elif f.endswith(".gitignore"):
                    file.write("__pycache__/\n.env\n.vscode/\n.DS_Store\n")
                elif f.endswith(".json"):
                    file.write("[]\n")
                else:
                    file.write("")

def create_structure(base_path="."):
    # Root project files
    create_files(base_path, PROJECT_STRUCTURE["root_files"])

    # Main project folder
    project_dir = os.path.join(base_path, "llm_scraper")
    os.makedirs(project_dir, exist_ok=True)

    # Files directly inside llm_scraper/
    create_files(project_dir, PROJECT_STRUCTURE["llm_scraper"]["files"])

    # Subdirectories inside llm_scraper/
    for subdir, files in PROJECT_STRUCTURE["llm_scraper"]["subdirs"].items():
        subdir_path = os.path.join(project_dir, subdir)
        os.makedirs(subdir_path, exist_ok=True)
        create_files(subdir_path, files)

if __name__ == "__main__":
    create_structure()
    print("✅ Project structure with files created successfully!")