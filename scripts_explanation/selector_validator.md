# selector_validator.py — High-Level Logic Explanation (Updated)

## 1) What does this module do?

It **validates candidate CSS selectors for a site’s search input** on a live page (Playwright), then:
- **types the keyword**, **submits the search**, waits for results,
- **scrolls** to trigger lazy loading, captures the **result HTML**,
- **saves session state** (cookies/localStorage) for reuse,
- returns **(validated_selector, html)**, or `None` if none work.

---

## 2) Key components

- **`SelectorValidator` (dataclass)**  
  Tunable timeouts:
  - `wait_for_selector`: max wait for the search input to become visible.
  - `navigation_timeout`: page navigation budget.
  - `post_submit_wait`: post-submit wait budget for results and network idle.

  Creates a **`SessionStore`** on init to persist/restore sessions automatically.

- **Playwright integration**  
  Uses a cached Playwright instance + **stealth context** (`_get_playwright`, `_create_stealth_context`) with optional `storage_state` for the URL.

---

## 3) Main flow — `validate_and_submit(url, selectors, keyword, skip_validation)`

**Goal:** Find the **first working selector** that can submit a keyword and yield a results page.

**Steps:**

1. **Session-aware setup**
   - Compute `storage_state_path` via `SessionStore`.
   - Open a stealth context, **loading prior session** for the URL if available (reduces captchas/logins).

2. **Navigate**
   - `page.goto(url)` with `navigation_timeout`.

3. **Try selectors (deduped)**
   - Iterate `dict.fromkeys(selectors)` to avoid duplicate work.
   - For each selector:
     - **Skip-validation path (`skip_validation=True`)**:
       - `page.wait_for_selector(selector)`; if it appears, use that handle.
     - **Validation path**:
       - Call **`_get_valid_handle(page, selector)`**:
         - Uses **`page.locator(selector).first`**,
         - Waits until **visible** within `wait_for_selector`,
         - Verifies **enabled**,
         - Returns a **`Locator`** if usable; otherwise `None`.

4. **Submit the search**
   - With a valid handle, call **`_fill_and_submit(handle, keyword)`**:
     - Click, **fill** the keyword, **press Enter**.

5. **Wait for results & load more**
   - **`_await_results(page)`**:
     - Races several **result-like selectors** (e.g., `.s-item`, Amazon’s `[data-component-type='s-search-result']`),
     - Briefly attempts `networkidle` for stabilization (best effort).
   - **`_scroll_results(page)`**:
     - Controlled wheel scrolls + pauses to trigger **lazy-loaded listings**.

6. **Capture output & persist session**
   - Get `html = page.content()`.
   - Save `storage_state` to `storage_state_path`.
   - Return `(selector, html)`.

7. **Cleanup**
   - Always close the context in `finally`.

If all candidates fail, return `None`.

---

## 4) Helpers (updated)

- **`_get_valid_handle(page, selector) -> Optional[Locator]`**  
  - Uses **`Locator`** API (`page.locator(selector).first`),
  - Waits for **visible**; checks **enabled**,
  - No pre-fill here (filling happens only in `_fill_and_submit`),
  - Returns a ready-to-use **`Locator`** or `None`.

- **`_fill_and_submit(handle, keyword)`**  
  - Operates on a **`Locator`**: click → fill → press Enter,
  - Ensures proper input events fire (as opposed to just setting value).

- **`_await_results(page)`**  
  - Concurrently waits for **any** of multiple result selectors; cancels the rest,
  - Tries `networkidle` within `post_submit_wait`; logs a warning if it times out.

- **`_scroll_results(page, step_px=1200, repeats=4, pause_ms=800)`**  
  - Scrolls in steps with pauses to allow rendering/lazy loading,
  - Final short wait to settle.

---

## 5) Why this design?

- **Real validation over assumptions**: ensure a selector is **visible & enabled** and actually submits.
- **Resilience & speed**:
  - **Deduped** selector trials,
  - **Session reuse** to avoid repeated friction,
  - **Multi-selector race** to detect results fast across different DOMs,
  - **Scroll** to surface lazy content.
- **Clean separation**:
  - Validation (find a usable input) vs. Submission (fill & Enter) vs. Results handling (await + scroll).

---
