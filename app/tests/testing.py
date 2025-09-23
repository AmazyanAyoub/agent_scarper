
from app.services.classify_website import build_hybrid_classifier

if __name__ == "__main__":
    url = "https://www.tripadvisor.com"
    label = build_hybrid_classifier(url)
    print(f"{url} -> {label}")