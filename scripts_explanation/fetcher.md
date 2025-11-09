# fetcher.py — High-Level Logic Explanation

## 1. What is this file doing overall?

This module is a **smart HTML fetcher with captcha handling**.

You call **`fetch_html(url)`**, and it:

1. Opens a **stealth Playwright browser**.
2. **Reuses previous cookies/sessions** if they exist (to avoid captchas / logins).
3. If a **captcha is detected**, it decides:
   - Try again with a stored session,
   - Or open a **manual window** where a human solves the captcha once,
   - Then **saves that session** for next time.
4. Returns the **page HTML** (or `""` if it failed).

So the goal is:  
> _Hide all the Playwright / captcha / sessions pain behind one simple function: `fetch_html`._

---

## 2. Global services & singletons

Names involved: `stealth`, `captcha_manager`, `session_store`, `_playwright`, `_browser`

- **`stealth`**: used to make the Playwright page look more like a real human browser (avoid anti-bot detection).
- **`captcha_manager`**: analyzes HTML and decides if there's a captcha and what to do about it.
- **`session_store`**: saves and loads browser sessions (cookies + localStorage) per URL/domain, so we can reuse them later.
- **`_playwright` / `_browser`**: global variables to **reuse** a single Playwright instance and browser across calls → avoids reopening a browser on every request (performance optimization).

These globals mean:
> The module behaves like a **service**: it keeps a browser and remembers sessions between calls.

---

## 3. `_get_playwright()` — ensure a single Playwright instance

- First time it runs: starts Playwright and stores the instance in the global `_playwright`.
- Next times: just returns the already started instance.

Role in the system:

> This function makes sure the whole app **doesn’t create a new Playwright engine each time**, which would be slow and heavy.

---

## 4. `_create_stealth_context()` — prepare a stealth browser tab with optional session

- Reuses or launches a Chromium `_browser` via Playwright.
- Creates a **new browser context** with:
  - `VIEWPORT`, `USER_AGENT`, `locale`, `timezone_id` to look like a real browser.
  - Optionally a **stored session** (`storage_state`) if a file exists for that URL (cookies + localStorage).
- Creates a **new page** from that context.
- Applies **stealth** on the page to remove typical bot fingerprints.
- Returns `(browser, context, page)`.

Role:

> This function builds a *ready-to-use, stealthy Playwright page* that optionally **continues a previous logged-in / captcha-bypassed session**.

It’s a **setup helper** used by `fetch_html`.

---

## 5. `wait_until_done_or_timeout()` — human-interaction helper

- Asks the user in the terminal: _“Press Enter when done:”_ in a background thread.
- Waits up to `seconds` (async timeout).
- Returns:
  - `True` if the human pressed Enter (they are done solving the captcha),
  - `False` if the timeout is reached or an error occurs.

Role:

> This is a **blocking point** used when the user is manually solving a captcha in a real browser. It gives them some time, then continues.

---

## 6. `_manual_solve()` — manual captcha solving + session capture

Main idea:

1. Opens a **nodriver / undetected browser** (`uc`) instead of Playwright:
   - This behaves more like a real human Chrome, so it’s less likely to be blocked.
2. Navigates to the target `url`.
3. Gives the human some time (`wait` seconds) to:
   - Solve the captcha,
   - Log in,
   - Do whatever is needed.
4. After waiting, it collects:
   - **All cookies** from the browser,
   - **All localStorage items** from the page,
   - **The origin** of the page.
5. Converts that data into a **Playwright-compatible `storage_state`** structure.
6. Calls `session_store.import_storage_state(url, storage_state)` to save that session.

Role:

> This is the **“nuclear option”**: when automation fails, the system asks a human to solve the captcha once, then **converts that solved session into a reusable Playwright session** for future automated calls.

So next `fetch_html()` calls can pass through without seeing the captcha again.

---

## 7. `_apply_solver_service()` — future hook for automatic captcha solving

Currently:

- Logs a warning saying that no solver service is configured.
- Does not perform any actual solving yet.

Design-wise, it’s a hook for plugging an **external captcha-solving API**.

Role:

> Future-proofing: the code is ready to support an **automatic captcha solver**, but it’s not wired yet.

---

## 8. `fetch_html()` — main public API & orchestrator

### Normal flow (no captcha)

Steps:

1. Computes the **session file path** for this `url` via `session_store.storage_state_path(url)`.
2. Gets or starts Playwright via `_get_playwright()`.
3. Calls `_create_stealth_context()` with the possible `storage_state_path`:
   - This may reuse a previous session (e.g. cookies where captcha is already passed).
4. Uses the `page` to:
   - `goto(url)` and wait until `domcontentloaded`.
   - `wait_for_timeout(wait)` to let dynamic content load.
5. Reads the **HTML** via `page.content()`.
6. Reads the **context storage state** (cookies + localStorage).
7. Closes the browser context (but keeps the browser globally).
8. Calls `captcha_manager.handle(url, html)`:
   - If no captcha → nothing happens.
   - If captcha → it raises `CaptchaDetected` with a decision.
9. If all is good, saves the `storage_state` via `session_store.save(url, storage_state)`.
10. Returns the HTML string.

Role:

> This is the **one function the rest of your app should use**. All the complexity (stealth, sessions, captcha detection, manual solving) is hidden inside.

---

### Captcha flow inside `fetch_html()`

When `captcha_manager.handle(url, html)` raises `CaptchaDetected`, we enter a special branch:

- The exception carries a **`decision`** attribute (from `CaptchaDecision`), which drives the behavior:
  - `CaptchaDecision.reuse_session`
  - `CaptchaDecision.manual_solve`
  - (Commented/future) `CaptchaDecision.solver_service`

**Case 1: `CaptchaDecision.reuse_session`**

- If a session file exists and this is the **first attempt** (`attempt == 0`):
  - Log “Retrying with stored session”.
  - Recursively call `fetch_html(...)` with `attempt + 1`.
- If we already tried reuse (`attempt > 0`):
  - Log that reuse failed and **escalate to manual solve**:
    - Call `_manual_solve(url, wait)`.
    - Then re-call `fetch_html(...)` with `attempt + 1`.

**Case 2: `CaptchaDecision.manual_solve`**

- Directly call `_manual_solve(url, wait)` to:
  - Open a real browser,
  - Let a human solve the captcha,
  - Save the resulting session.
- Then retry `fetch_html(...)` again with `attempt + 1`.

**(Future) Case 3: `CaptchaDecision.solver_service`**

- The code for this is currently commented out, but the intended flow is:
  - Call `_apply_solver_service(url)` to use an external captcha-solving API.
  - Retry `fetch_html(...)` after that.

If none of the cases are taken (or after failure), the function returns an empty string `""`.

Role:

> `fetch_html` is like a **controller**: it listens to what `captcha_manager` suggests (reuse session, manual solve, future solver API), then **routes the flow accordingly** and retries until it gets a clean HTML or decides to give up.

---

### Error handling in `fetch_html()`

For any unexpected `Exception`:

- Logs:
  - A summary message with the URL and error.
  - A full traceback (stack trace) for debugging.
- Returns `""` to signal failure to the caller.

Role:

> Ensures that the caller doesn’t crash the whole app, and instead receives a controlled “no result” value (`""`) when fetching fails.

---

## 9. Mental model / summary

Think of this module as a **specialized browser client**:

- **`fetch_html(url)`**  
  → “Give me the HTML of this URL, and deal with:
  - browser setup,
  - stealth anti-bot tricks,
  - captcha detection,
  - manual captcha solving,
  - session reuse.”

- **`SessionStore`** (external)  
  → the brain that remembers **which cookies/localStorage worked** last time for that site.

- **`CaptchaManager`** (external)  
  → the doctor that inspects HTML and says:  
  “There is a captcha. Try X: reuse session / manual solve / solver API.”

- **`_manual_solve()`**  
  → the emergency procedure: “Ask a human to fix it once, then convert that into an automated session.”

So the design goal is:

> **One simple entry point** (`fetch_html`) for the rest of your scraping/agent code, with a **smart, layered strategy for bypassing captchas and reusing sessions**.
