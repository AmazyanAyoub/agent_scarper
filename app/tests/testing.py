import asyncio

from app.services.classify_website import build_hybrid_classifier
from app.strategies.ecommerce import run_ecommerce_flow


async def main():
    url = "https://www.ebay.com"
    instruction = ""

    site_type = await asyncio.to_thread(build_hybrid_classifier, url)
    print(f"classifier -> {site_type}")

    if site_type != "ecommerce":
        print("not an ecommerce site, skipping ecommerce flow")
        return

    context = await run_ecommerce_flow(url, instruction)
    print(context.result_html[2000:3000])


if __name__ == "__main__":
    asyncio.run(main())
