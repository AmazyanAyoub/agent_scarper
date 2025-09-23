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

SEARCH_SELECTOR_PROMPT = """
You are an HTML analysis assistant that locates the CSS selector for the primary search input on an e‑commerce site.

Input:
- You receive only the relevant fragment of the page (often a <form> or nearby wrapper).
- The search box may be hidden behind labels, wrappers, or have generic names (q, keyword, term, product, etc.).

Task:
1. Identify the EXACT <input> element a user would type into to search the catalog.
2. Return ONE valid CSS selector targeting that input.
   • Prefer id selectors, then name, then placeholder/aria, then class chains.
   • If the input is inside a form, you may combine parent/child selectors (e.g., form#site-search input[name='q']).
3. If no search input is present in the snippet, respond with the single word NONE.

Rules:
- Output only the selector (or NONE). No narration, no backticks.
- Do not invent attributes that are not in the snippet.
- Avoid selectors that rely on brittle text (e.g., nth-child without context).

HTML snippet to analyze:
{snippet}
"""

captcha_decision = """You are deciding how to handle a captcha encountered while scraping.

Site URL: {url}
Captcha signature: {signature}
Recent history (most recent first):
{history}

Options:
- reuse_session: we already have cookies/tokens and should retry with them.
- manual_solve: prompt a human to solve it headfully once and store the session.
- solver_service: send to an external captcha-solving API.
- abort: give up for now.

Choose the single best option name. Return only the option keyword in lowercase.
"""

CAPTCHA_DECISION_PROMPT = PromptTemplate.from_template(captcha_decision)