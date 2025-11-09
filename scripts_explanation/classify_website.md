# classifier.py — High-Level Logic Explanation

## 1. What is this file doing overall?

This module is a **website classifier with memory**.

Given a `url`, the main function **`build_hybrid_classifier(url)`**:

1. Checks if this URL was already classified before (using a **local JSON file**).
2. If yes → **returns the stored label immediately** (no network / no LLM).
3. If not:
   - Fetches the HTML of the page using **`fetch_html`** (the smart browser+captcha fetcher).
   - Cleans that HTML into a text snippet.
   - Builds a **few-shot context** from previously saved, labeled examples.
   - Uses an **LLM chain** (`build_site_classifier_chain`) to classify the site.
   - Saves the new labeled example to disk for future reuse.
   - Returns the predicted label.

So the goal of this module is:

> Turn the LLM into a **progressively smarter and cheaper classifier** that remembers past decisions and uses them as examples for new websites.

---

## 2. Global caches: `_examples_cache` and `_label_cache`

- **`_examples_cache`**: a list of all stored examples loaded from the JSON file (`DATA_FILE`).  
  Each example looks like: `{ "url": ..., "label": ..., "snippet": ... }`.

- **`_label_cache`**: a dict mapping `url -> label` for **fast lookups**.

Design idea:

- The JSON file is read **once**, and the data is kept in memory.
- `_label_cache` allows the system to quickly answer:  
  “Have we already classified this URL? If yes, what label did we give it?”

Role:

> These caches make the classifier a **stateful system with memory**: the more you use it, the more knowledge it accumulates and can reuse.

---

## 3. `load_examples()` — load and initialize memory

**Logic:**

1. If `_examples_cache` is already set:
   - Return it directly (no extra disk reads).
2. If the data file (`DATA_FILE`) does **not** exist:
   - Initialize memory as empty:
     - `_examples_cache = []`
     - `_label_cache = {}`
   - Return the empty list.
3. If the file exists:
   - Open and `json.load` it.
   - Store its content in `_examples_cache`.
   - Build `_label_cache` from these examples: `{ e["url"]: e["label"] }`.
   - Return the examples list.

**Role:**

> This function **prepares the classifier’s memory** (examples and label map) so other functions can work only with in-memory data and not worry about file handling.

---

## 4. `save_example(url, label, snippet)` — add a new labeled example

**Logic:**

1. Call `load_examples()` to ensure the in-memory data is initialized.
2. If `_label_cache` exists and already contains `url`:
   - Return immediately → avoid duplicate entries for the same URL.
3. Otherwise:
   - Create an entry: `{ "url": url, "label": label, "snippet": snippet }`.
   - Append it to the in-memory examples list.
   - Update `_label_cache[url] = label` (if `_label_cache` exists).
   - Write the entire updated list back to `DATA_FILE` using `json.dump`.

**Role:**

> This function is how the classifier **learns from new classifications**: every time `build_hybrid_classifier` predicts a label, `save_example` stores it so it can be reused as:
> - Cached result (for that exact URL),
> - Few-shot example (for similar future URLs).

---

## 5. `select_examples(data, max_per_label=2, max_total=30)` — build a compact, balanced few-shot set

**Goal:**

> Build a **balanced and globally limited** list of examples to feed to the LLM:
> - Up to `max_per_label` examples per label,
> - At most `max_total` examples overall,
> - Each example short and cleaned.

### Step 1: Group examples per label with a per-label cap

- Uses a `defaultdict(list)` called `grouped`.
- Iterates over all `data` entries:
  - For each entry, looks at `entry["label"]` and gets its bucket: `grouped[label]`.
  - Adds the entry to that bucket **only if** the bucket size is still `< max_per_label`.

**Meaning:**

- Each label gets **at most `max_per_label` examples**.
- This maintains **balance across labels**, so one label cannot dominate the training examples.

### Step 2: Flatten into lines with a global cap

- Initializes an empty list `lines` and a counter `count = 0`.
- Loops through each label and its entries in `grouped`.
- For each entry:
  - If `count >= max_total`, stop adding more examples.
  - Builds `snippet_short` from the entry:
    - Uses only the first 160 characters.
    - Replaces newlines with spaces.
  - Appends a formatted line:  
    `url → label | snippet_short...`
  - Increments `count`.

**Meaning:**

- You still respect **per-label limits** but also have a **hard global limit** (`max_total`, default 30).
- This keeps the few-shot context:
  - **Balanced** (each label contributes up to N examples),
  - **Compact** (no more than `max_total` examples, short snippets).

### Step 3: Return as a single string

- Joins all `lines` with newline characters and returns one big string.

**Role:**

> `select_examples` converts raw stored examples into a **compact, balanced text block** suitable for including in the LLM prompt or chain.  
> It protects the prompt from becoming too large while still capturing diversity across labels.

---

## 6. `build_hybrid_classifier(url: str) -> str` — main orchestrator

This is the **public API** of the module.

### 6.1 Check memory / cache first

- Calls `load_examples()` to ensure `_examples_cache` and `_label_cache` are ready.
- If `_label_cache` exists:
  - Tries `label = _label_cache.get(url)`.
  - If a label is found:
    - Returns that label immediately.

**Role:**

> This is the **fast path**: if we’ve seen the URL before, we **reuse the existing label** without hitting the network or the LLM.

---

### 6.2 Fetch and process HTML for new URLs

If the URL is **not** in `_label_cache`:

1. Calls `fetch_html(url)` wrapped in `asyncio.run(...)`:
   - Uses the advanced Playwright-based fetcher with stealth, sessions, and captcha handling.
2. Parses the HTML with `BeautifulSoup`:
   - Uses `.get_text(" ", strip=True)` to extract a clean text representation of the page.
   - Trims the text to the first 1000 characters → this becomes the **snippet**.

**Role:**

> This step transforms the raw website into a **compact text snippet** that the LLM can understand and classify.

---

### 6.3 Select few-shot examples

- Calls `select_examples(data)` using all stored examples (`data` from `load_examples()`).
- Receives a string `examples_str` containing multiple lines like:  
  `url → label | snippet...`

**Role:**

> This builds a **few-shot context** for the LLM, made of real past decisions, balanced across labels and size-limited.

---

### 6.4 Build the LLM classifier chain

- Calls `build_site_classifier_chain(url, snippet, examples_str)`:
  - This function likely:
    - Builds the prompt (possibly using `EXPANDED_CLASSIFIER_PROMPT`),
    - Configures which model to use,
    - Returns an object (`classifier_chain`) that can be invoked.

**Role:**

> This isolates all prompt/model configuration logic away from this module, so `build_hybrid_classifier` only has to say:
> “Here is the URL, snippet, and examples. Build me a classifier chain.”

---

### 6.5 Run the classification

- Calls `classifier_chain.invoke()` with no arguments (context is already baked in).
- Stores the result in `result`, which is expected to be the **predicted label** for the URL.

**Role:**

> This is where the LLM **actually decides the category** of the website, using:
> - The page snippet,
> - The URL,
> - The few-shot example block.

---

### 6.6 Save the result as a new example

- Calls `save_example(url, result, snippet[:500])`:
  - Saves the URL,
  - The predicted label (`result`),
  - A shortened version of the snippet (first 500 characters).

**Role:**

> This step **teaches the classifier from its own decisions**:
> - The next time the same URL appears, the result is instant.
> - The URL + snippet + label can be reused as a few-shot example for other URLs.

Finally, it returns `result`.

---

## 7. Mental model / summary

This module is a **self-improving website classifier**:

- At first:
  - It may have no examples and rely only on generic LLM knowledge.
- Over time:
  - Every classification is **remembered** and saved as structured data.
  - These examples form a **small internal dataset** for few-shot learning.
  - Classification becomes:
    - More **consistent**,
    - More **adapted to your domain**,
    - **Cheaper and faster** for URLs already seen.

Main components in terms of roles:

- **`load_examples()`**  
  → Initialize and access the classifier’s **memory** (examples + URL→label map).

- **`save_example()`**  
  → Add a new experience (URL + label + snippet) to this memory.

- **`select_examples()`**  
  → Build a **balanced, size-limited few-shot context** from the memory to guide the LLM.

- **`build_hybrid_classifier(url)`**  
  → Orchestrator:
  > “If I already know this URL, answer from memory.  
  > If I don’t, fetch the page, summarize it, compare it with past examples using an LLM,  
  > then remember the result for later.”
