# parser.py — High-Level Logic Explanation

## 1) What does this module do?
It **guesses CSS selectors for a site’s search input** by combining:
- a fast **heuristic detector** (HTML scan),
- an **LLM-based detector** (prompted on a page snippet).

It then **merges, ranks (by confidence), dedupes, and returns** the top selectors.

---

## 2) Core flow — `detect_search_selectors(html, limit=10)`
1. Calls **`_detect_search_selectors_heuristic`** → quick, local guesses.
2. Calls **`_detect_search_selectors_llm`** → LLM-suggested guesses.
3. **Merges** both lists into `SelectorCandidate(css, confidence, source)`.
4. **Sorts** by `confidence` (desc), **dedupes by CSS**, returns up to `limit`.
5. Logs the final candidate list.

**Goal:** Provide a **compact, high-quality shortlist** of selectors to try first.

---

## 3) Heuristic engine — `_detect_search_selectors_heuristic(html, limit)`
- Parses the HTML with BeautifulSoup.
- Finds `<input>` elements whose `type` matches **“search” or “text”**.
- Starts each candidate at **score 3** and **boosts +2** if any attribute from **`SEARCH_ATTRS`** contains a token matching **`SEARCH_TERMS`** (e.g., “q”, “search”, “keyword”…).
- Builds a readable CSS via **`build_selector`** and caps confidence at **5**.
- Stops when it reaches `limit`.

**Why:** Very fast, high-precision on typical search boxes (id/class/name/placeholder give strong signals).

---

## 4) LLM engine — `_detect_search_selectors_llm(html, limit)`
- Takes the first **`SNIPPET_LIMIT`** chars of the HTML (to keep prompts small).
- Runs a **prompted chain**: `PromptTemplate(SEARCH_SELECTORS_PROMPT)` → `get_llm()` → `StrOutputParser`.
- Expects a **JSON payload** with a `selectors` array `[{ css, confidence }, ...]`.
- Uses **`clean_json_text`** to strip backticks/```json fences if present, then `json.loads`.
- On JSON parse failure: logs a warning and returns no LLM candidates.

**Why:** Catches **non-obvious** patterns the heuristic may miss (deeply nested inputs, atypical attributes, framework-generated DOMs).

---

## 5) Selector synthesis — `build_selector(tag)`
Order of preference to create a **stable, readable** CSS:
1. If the input has an **`id`** → `input#id`.
2. Else if it has **classes** → `input.class1.class2.class3` (up to 3 classes).
3. Else if it has **`name` / `placeholder` / `aria-label`** → `input[attr='value']`.
4. Else fallback → `input`.

**Why:** Prefer short and robust selectors that are easy to debug and reuse.

---

## 6) Utilities
- **`_attr_tokens(value)`**  
  Normalizes attribute values into **list of strings** (handles scalars and lists), making it easy to scan across `SEARCH_ATTRS`.

- **`clean_json_text(text)`**  
  Removes Markdown fences (``` / ```json) so LLM output becomes valid JSON.

---

## 7) LLM chain caching — `_get_selector_chain()`
Builds the prompt→LLM→string pipeline **once** and **reuses** it (singleton).  
**Benefit:** lower latency and cost; consistent behavior across calls.

---

## 8) Config knobs
- **`SEARCH_ATTRS`**: which attributes to inspect for heuristic boosts (e.g., `["id","name","class","placeholder","aria-label"]`).
- **`SEARCH_TERMS`**: terms/regex that signal “search” semantics; compiled to `SEARCH_TERMS_RE`.
- **`SNIPPET_LIMIT`**: size limit for the HTML chunk sent to the LLM (keeps prompts lean).

---

## 9) Robustness & logging
- If the LLM returns non-JSON, the module **fails soft** (heuristics still work).
- Final candidates are **logged** for transparency and debugging.
- Confidence is **normalized** (heuristics capped at 5; LLM confidence respected with sane default).

---

## 10) Mental model
Think of it as a **two-engine selector scout**:
- **Heuristic** = fast, deterministic first pass.
- **LLM** = creative backup to catch tricky layouts.
- **Merger** = ranks, dedupes, and hands you the **best few selectors** to try.
