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

Now classify this new site:
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
   - `reason`: short explanation (<= 80 chars).
3. Return at most 10 selectors, sorted by confidence descending.
4. Only propose selectors that actually appear in the snippet.
5. If nothing looks like a search box, return `{"selectors": []}`.

HTML snippet:
{snippet}
"""

INTENT_PROMPT = """You extract e-commerce search intent.

Instruction:
{instruction}

Return JSON with:
- keyword: the single best search term to type into the site (lowercase, 2–4 words max).
- conditions: array of short bullet strings capturing any filters, constraints, or preferences that do NOT belong in the keyword (empty array if none).

If the instruction is mostly filters with no obvious keyword, set keyword to "udgu" and push the details into conditions.
"""