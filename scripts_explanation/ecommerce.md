# ecommerce_strategy.py — High-Level Logic Explanation

## 1. What is this file doing overall?

This module coordinates the **full ecommerce scraping flow**.

Given:
- a **`url`** (e.g. an ecommerce homepage),
- an **`instruction`** (e.g. “search for iphone 15 128gb and get products”),

the main logic:

1. Converts the instruction into a **search keyword**.
2. Finds or reuses the **search bar selector** for that domain.
3. Uses a validator to **type the keyword and submit the search**.
4. Gets back the **search results HTML**.
5. Extracts **product cards** (title, price, link…) from that HTML.
6. Saves the products to disk.
7. Returns an **`EcommerceContext`** object containing all useful data (HTMLs, selectors, products, output path, etc.).

Goal:

> Turn “URL + instruction” into **structured product data**, using Playwright, smart selector detection, validation, and caching.

---

## 2. `EcommerceContext` — shared state for the whole flow

`EcommerceContext` is a dataclass carrying all state across steps:

- `url`: starting ecommerce URL.
- `instruction`: user’s natural language request.
- `html`: initial HTML of the page (if fetched).
- `selector_candidates`: list of candidate CSS selectors for the search input.
- `validated_selector`: the final **working** search input selector.
- `result_html`: HTML of the **search results page** after submitting the keyword.
- `search_keyword`: keyword string derived from the instruction via `build_search_keyword`.
- `products`: list of `Cards` objects (structured products extracted from the result page).
- `output_path`: path where products were saved (e.g. JSON/CSV).

Role:

> `EcommerceContext` is the **state container** for the whole flow: from the original URL and instruction, through selectors and HTML, to final extracted products and where they’re saved.

---

## 3. `EcommerceStrategy` — the orchestration class

This class is the **high-level coordinator** for ecommerce-specific steps.

### Constructor: `__init__`

- Accepts optional:
  - `validator` (a `SelectorValidator`),
  - `selector_store` (a `SelectorStore`).

If they’re not provided, it creates default instances.

Responsibilities of its collaborators:

- `SelectorValidator`:  
  - Tests candidate selectors on a live page,  
  - Types the search keyword,  
  - Submits the form,  
  - Checks if resulting HTML is valid search results.

- `SelectorStore`:  
  - Stores known selectors (search input, product cards) **per domain**,  
  - Returns them later so we don’t have to rediscover them.

Role:

> `EcommerceStrategy` does not do low-level scraping itself; it **delegates** to services like `fetch_html`, `detect_search_selectors`, `SelectorValidator`, `extract_cards_from_html`, and `save_cards`, and just coordinates the whole pipeline.

---

## 4. `run(url, instruction)` — main ecommerce pipeline

This is the core method that executes the full flow.

### Step 1: Initialize context and build keyword

- Creates an `EcommerceContext` with `url` and `instruction`.
- Uses `build_search_keyword(instruction)` to transform the user’s instruction into a **clean search keyword** (e.g. “iphone 15 128gb”).
- Extracts the **domain** from the URL via a helper (`_domain`).

Role:

> Prepares a consistent context object and a focused search keyword to use on the website.

---

### Step 2: Fast path — reuse cached search selector (if available)

- Queries `SelectorStore` for the given domain.
- Looks for a stored `"search"` selector.

If a cached `search_selector` exists:

1. Logs that it will reuse it.
2. Calls `SelectorValidator.validate_and_submit` with:
   - `selectors=[search_selector]`,
   - `keyword=ctx.search_keyword`,
   - `skip_validation=True` (trust the cached selector, just use it).

If this returns a valid result:

- Stores:
  - `ctx.validated_selector` = working search selector,
  - `ctx.result_html` = HTML of search results.
- Calls `_populate_cards(ctx, domain)` to extract and save product cards.
- Sets `ctx.selector_candidates = [search_selector]`.
- Returns the context.

If the cached selector fails:

- Logs a warning.
- Falls back to full detection.

Role:

> This is the **optimized path**:  
> for known domains, we skip detection and directly use the previously discovered selector.  
> If the site changed and the selector stops working, the system automatically falls back to discovery mode.

---

### Step 3: Slow path — fetch HTML and detect search selectors

If there is no working cached selector:

1. **Fetch initial HTML** using `fetch_html`:
   - Uses Playwright with stealth, captcha handling, etc.
   - Waits a bit to ensure page is loaded.

   If fetching fails (no HTML), it logs an error and returns the context.

2. **Detect search selectors** with `detect_search_selectors`:
   - Analyzes the HTML to find likely search input elements.
   - Produces a list of candidate selectors (e.g. up to 10).

   If no candidates are found, it logs an error and returns the context.

3. **Validate and submit selectors** using `SelectorValidator.validate_and_submit`:
   - Tries each candidate selector live:
     - Open the page,
     - Type the keyword,
     - Submit search,
     - Check if the resulting page looks like valid search results.
   - Returns `(validated_selector, result_html)` if one candidate works.

If validation returns a result:

- Store the selector and results HTML in the context.
- Call `_populate_cards(ctx, domain)` to extract product cards.
- Save the **validated search selector** in `SelectorStore` for this domain.

If it fails:

- Log that no valid search input selector was found.

Finally, return the context.

Role:

> This is the **discovery mode**: the system learns how to interact with a brand-new ecommerce site by detecting and testing search input candidates, and then caches what works.

---

## 5. `_domain(url)` — domain normalizer

- Extracts the domain from the URL (e.g. `www.amazon.com`) and lowercases it.

Role:

> Ensures that selector caching is done consistently **per domain**, so that “Amazon.com” and “amazon.com” are treated the same.

---

## 6. `_populate_cards(ctx, domain)` — extract and save product cards

This method is called once we have `ctx.result_html` (i.e. the search results page HTML).

### Step 1: Safety check

- If `ctx.result_html` is missing, logs a warning and returns.

### Step 2: Load cached card selector/mapping (if any)

- Looks into `SelectorStore` for the current domain.
- Fetches any cached `"card"` configuration:
  - `selector`: CSS selector for product cards.
  - `mapping`: how to map HTML elements to the `Cards` fields (title, price, link, etc.).

Role:

> Reuse previously discovered card layout for this domain if possible, so we don’t have to rediscover the product card structure every time.

### Step 3: Extract cards with `extract_cards_from_html`

- Calls `extract_cards_from_html` with:
  - `ctx.result_html`,
  - The base URL,
  - A limit on the number of cards (e.g. 10),
  - Cached card selector/mapping (if available),
  - A flag that it can reuse cached configuration.

- The extractor returns:
  - A list of `Cards` objects (structured product info),
  - Possibly the selector and mapping it used/discovered.

- `ctx.products` is populated with the extracted cards (or an empty list).

Role:

> This step converts the raw HTML of the search results page into **structured product objects** you can use programmatically.

### Step 4: Save new card selector/mapping if discovered

- If the extractor provides `selector` and `mapping`:
  - Save them back into `SelectorStore` under `"card"` for the domain.

Role:

> Over time, the system **learns the product card layout** per site and caches it for faster, more robust future runs.

### Step 5: Save products to disk with `save_cards`

- If products are present:
  - Calls `save_cards(domain, ctx.products)` to persist them (e.g. JSON/CSV).
  - Stores the returned path into `ctx.output_path`.
- If no products:
  - Sets `ctx.output_path` to `None`.

Role:

> This final step makes the extracted product data **persistent** and records where it was stored.

---

## 7. `run_ecommerce_flow(url, instruction)` — convenience entry point

- Instantiates an `EcommerceStrategy`.
- Calls `strategy.run(url, instruction)`.
- Returns the resulting `EcommerceContext`.

Role:

> Provides a **simple one-call interface** to run the entire ecommerce pipeline:
> ```python
> ctx = await run_ecommerce_flow("https://example.com", "search for gaming laptop under 1000")
> ```

---

## 8. Mental model / summary

This module is the **ecommerce orchestration layer** of your system.

Key ideas:

- **Memory of sites**:
  - It remembers **search input selectors** and **product card selectors/mappings** per domain via `SelectorStore`.
- **Validation over guessing**:
  - It does not just guess selectors; it **tests them live** using `SelectorValidator` to ensure real search results are obtained.
- **Context as a single object**:
  - `EcommerceContext` keeps all relevant inputs and outputs of the flow in one place.

Main roles:

- **`EcommerceContext`**  
  → Carries everything: instruction, keywords, HTMLs, selectors, extracted products, output path.

- **`EcommerceStrategy.run()`**  
  → Full pipeline for a domain:
  > 1. Build search keyword.  
  > 2. Reuse cached search selector if possible; otherwise detect and validate one.  
  > 3. Once search results HTML is obtained, extract product cards.  
  > 4. Cache selectors/mappings and save products.

- **`_populate_cards()`**  
  → Turns the result page HTML into **structured product data**, and teaches the system how to recognize product cards next time.

Overall:

> This module turns your scraper into a **learning ecommerce agent**: the more sites it touches, the more it learns their search fields and product layouts, making future runs faster, cheaper, and more reliable.
