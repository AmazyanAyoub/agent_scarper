from langchain_core.prompts import PromptTemplate

EXPANDED_CLASSIFIER_PROMPT = """
You are a strict website classification assistant.
Your task is to classify the website into exactly ONE type.

Categories:
- ecommerce: online shops, products, carts, checkout
- blog: personal/professional blogs, posts, articles
- news_portal: news sites, newspapers, magazines
- wiki: knowledge bases, encyclopedias, collaborative wikis
- forum: discussion boards, threads, replies
- corporate: company or organization websites (About, Services, Contact)
- directory: listings, yellow pages, category-based indexes
- government: official government or NGO sites (.gov, .int, .who)
- education: schools, universities, research portals (.edu, arxiv, nature)
- developer_platform: platforms for coding, repos, dev tools (github, stackoverflow)
- social_media: social networking, short-form content (facebook, twitter, tiktok)
- saas_tool: software-as-a-service tools and apps (notion, slack, zoom)
- portfolio_personal: individual websites, CVs, artist/creator portfolios

Here are past examples of known classifications:
{examples}

Now classify this new website:
URL: {url}
Content snippet: {snippet}

Rules:
1. Choose exactly ONE category from the list.
2. If the site fits multiple, choose the most dominant type.
3. If you are unsure, use the closest match — never invent a new category.
4. Answer ONLY with the category name, lowercase.
5. Do not add explanations.
"""

SEARCH_SELECTORS_PROMPT = """
You are an HTML analysis assistant that locates possible CSS selectors for the primary search input on an e-commerce site.

Rules:
1. Output JSON with a single key `selectors`, whose value is an array of objects.
2. Each selector object must have:
   - `css`: the CSS selector string.
   - `confidence`: integer 1–5 (5 = highest confidence).
3. Return at most 10 selectors, sorted by confidence descending.
4. Only propose selectors that actually appear in the snippet.
5. If nothing looks like a search box, return `{{"selectors": []}}`.

HTML snippet:
{snippet}
"""

SEARCH_INTENT_PROMPT = """
You are an e-commerce search planner. Distil the user’s instruction into a primary search keyword and structured conditions.

Rules:
1. Move only the essential term(s) into keyword; everything else becomes conditions.
2. If the instruction is mostly filters and no obvious keyword, set keyword to "udgu".
3. `apply_via` must be "keyword" when the condition is best expressed directly in the query (e.g. specific brand or model); otherwise "filter".
4. Conditions array can be empty; omit null/empty fields.
5. No narration; return JSON only.


Instruction:
{instruction}

Output STRICT JSON with:
{{
  "keyword": "<string>",
  "conditions": [
    {{
      "name": "<condition_name>",   // e.g. price_max, brand, color, rating
      "value": "<condition_value>", // short human-readable value, keep symbols (€, %, etc.)
      "apply_via": "keyword" | "filter" // keyword = append to search string; filter = requires UI control
    }},
    ...
  ]
}}
"""

CARD_PROMPT = """
You are an expert HTML analyzer for e-commerce product cards.
Given one HTML snippet of a product card, identify CSS selectors (relative to the snippet)
for title, price, image, and link. Prefer short selectors and only use comma-separated
lists when multiple elements are required. If a field is missing, set it to null.
Respond strictly in JSON with this exact shape:
{{"candidates": [{{"title": "selector or null", "price": "selector or null", "image": "selector or null", "link": "selector or null"}}]}}

HTML SNIPPET:
{card_html}
"""