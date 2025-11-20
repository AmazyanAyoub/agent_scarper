# search_intent.py — High-Level Logic Explanation

## 1) What does this module do?

It turns a **natural-language instruction** (e.g., “find iPhone 15 128GB under €800 in Paris”) into:
- a structured **SearchIntent** (keyword + conditions) using an **LLM chain**, then
- a final **search keyword string** suitable for plugging into a site’s search input.

It also **caches the LLM chain** so we don’t rebuild it on every call.

---

## 2) Key building blocks

- **`_get_search_intent_chain()`**  
  A simple **singleton** accessor. It builds the LLM chain once via `build_search_intent_chain()` and reuses it.  
  *Why?* Faster, cheaper, avoids repeated initialization.

- **`SearchCondition` (dataclass)**  
  Structured condition with `name` and `value`.

- **`SearchIntent` (dataclass)**  
  Holds the **primary keyword** and a list of `SearchCondition`s inferred from the instruction by the LLM.

---

## 3) Flow A — `build_search_intent(instruction)`

**Goal:** Ask the LLM to interpret the user instruction and return a structured intent.

**Logic:**
1. Get the cached chain with **`_get_search_intent_chain()`**.
2. Clean the input (`instruction.strip()`).
3. **Invoke** the chain with `{"instruction": clean_instruction}`.
4. **On failure** (LLM/parse error), return a **fallback** intent:
   - `keyword="udgu"` (sentinel meaning “unknown / don’t guess”),
   - `conditions=[clean_instruction]` (so we still preserve some signal).

**Design idea:**  
Centralize intent parsing behind one LLM call; downstream code shouldn’t care how the intent is produced.


---

## 4) Flow B — `build_search_keyword(instruction)`

**Goal:** Produce the **final free-text query** to type into a site’s search box.

**Logic:**
1. Call **`build_search_intent`** to get the structured intent.
2. Start with an empty list `keyword_parts`.
3. If the intent has a **real keyword** (and not `"udgu"`), append it.
4. Iterate over **conditions**:
   - If a condition is a **string**, append it (backward compatibility).
   - If it’s a `SearchCondition` and it has a non-empty `value`, **append the value**.
5. **Join** all parts with spaces → final keyword string.

**Why this split?**  
Some constraints belong in the **typed query** (brand, model, free text). This function builds only the **textual query**.

---

## 5) Data flow & collaboration

- **Instruction → `build_search_intent`** (LLM):  
  produces `SearchIntent(keyword, conditions[])`.
- **`build_search_keyword`**:  
  converts that intent into a **single query string** by concatenating the primary keyword plus any useful condition values.

---

## 6) Error handling & fallback

- If the LLM call fails, we return a conservative intent (`keyword="udgu"`), log the error, and still pass along the raw instruction as a condition.  
- `build_search_keyword` then:
  - Skips `"udgu"`,
  - Falls back to concatenating condition strings and any condition `value`s.

This ensures the pipeline **degrades gracefully** rather than breaking.

---

## 7) Why this design?

- **Separation of concerns:** Parsing intent (LLM) vs. building a typed query.
- **Performance:** Chain is **cached** to avoid rebuilds.
- **Extensibility:** You can later refine how conditions contribute to the keyword without changing the LLM parsing step.

---