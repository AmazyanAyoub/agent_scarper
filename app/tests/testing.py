import asyncio

from app.services.classify_website import build_hybrid_classifier
from app.strategies.ecommerce import run_ecommerce_flow


async def main():
    url = "https://www.ebay.com"
    instruction = "I want the iphone 15 with 256go new or old"

    site_type = await asyncio.to_thread(build_hybrid_classifier, url)
    print(f"classifier -> {site_type}")

    if site_type != "ecommerce":
        print("not an ecommerce site, skipping ecommerce flow")
        return

    context = await run_ecommerce_flow(url, instruction)
    # print(context.instruction)
    # print(context.search_keyword)
    # print(context.url)
    # print(context.validated_selector)
    

if __name__ == "__main__":
    asyncio.run(main())
