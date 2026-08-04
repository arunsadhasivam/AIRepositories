# KV Cache vs Semantic Cache

## 1. KV Cache (Key-Value Cache)

**Layer:** Inference layer (inside the transformer, already built into LLM serving infra — vLLM, TensorRT-LLM, Hugging Face, provider inference servers).

**Purpose:** Avoid recomputing attention Key/Value vectors for tokens already processed in the current generation.

**Analogy:** Same as memoized Fibonacci in Dynamic Programming — reuse overlapping subproblems (already-computed token attention) instead of recomputing from scratch on every new token.

**Example:**
- User types "I love programming" token by token.
- Without KV cache: every new token forces recomputation of K/V for ALL previous tokens.
- With KV cache: K/V for "I", "love" are computed once and stored in GPU memory. When "programming" arrives, only its K/V is computed fresh — "I love" is reused from cache.

**Who implements it:** The model-serving infrastructure. Application developers do NOT build this themselves.

---

## 2. Semantic Cache

**Layer:** Application/API layer — sits between your app and the LLM API call.

**Purpose:** Avoid a full LLM call when a semantically similar question has already been asked before (even if worded differently).

**Analogy:** A cache lookup based on *meaning*, not exact key match — unlike Redis key-value cache, which requires exact string keys.

**How it works:**
1. New query arrives → embed it into a vector.
2. Compare (cosine similarity) against vectors already stored in the cache.
3. If similarity crosses a threshold (e.g., 0.9) → cache **HIT** → return the stored answer, skip the LLM call.
4. If no match → cache **MISS** → call the LLM → store the new (vector, answer) pair for future lookups.

**Important:** On a cache HIT, nothing new is stored — only a cache MISS results in a new entry.

**Who implements it:** You (application developer) — requires an embedding model, a vector DB, a similarity threshold, and cache read/write logic. Not provided automatically by the LLM provider.

### Example walkthrough

- Query 1: `"What's the capital of France?"` → cache empty → MISS → call LLM → answer = `"Paris"` → stored.
- Query 2: `"Tell me France's capital city"` → embedded → compared to Query 1's vector → similarity ≈ 0.96 → HIT → return `"Paris"` directly, no LLM call, nothing new stored.

Final cache state — only ONE entry exists:
```
KEY   = Vector of Query 1 (whichever query hit the LLM first)
VALUE = "Paris"
```

### Code (Python)

```python
from sentence_transformers import SentenceTransformer, util  # embedding model + cosine similarity util

model = SentenceTransformer('all-MiniLM-L6-v2')      # load a lightweight embedding model
cache = {}                                             # simple dict acting as our vector cache: {vector: answer}

def check_cache(query, threshold=0.9):
    query_vec = model.encode(query, convert_to_tensor=True)          # embed the new query into a vector
    for cached_vec, answer in cache.items():                         # loop through existing cached vectors
        if util.cos_sim(query_vec, cached_vec).item() > threshold:   # compare similarity to each stored vector
            return answer                                            # match found -> return cached answer (cache HIT)
    return None                                                      # no match found -> cache MISS, caller should call LLM next
```

**Usage (cache miss → store new entry):**

```python
answer = check_cache("Tell me France's capital city")   # check if a similar query already exists
if answer is None:                                        # cache miss
    answer = call_llm("Tell me France's capital city")     # call LLM to get fresh answer
    cache[model.encode("Tell me France's capital city", convert_to_tensor=True)] = answer  # store new entry
```

---

## 3. Side-by-side comparison

| | KV Cache | Semantic Cache |
|---|---|---|
| Layer | Inside the transformer, during generation | Application/API layer, before calling the LLM |
| What it avoids | Recomputing attention for already-processed tokens | Recalling the LLM for a semantically repeated question |
| Storage | GPU memory (temporary, per-request) | Vector DB (persistent, across users/requests) |
| Analogy | Dynamic programming / memoized Fibonacci | Cache lookup by meaning, not exact string |
| Who implements it | Model-serving infrastructure (already built-in) | Application developer (custom build) |
| Match type | Exact — reuses only already-computed tokens in current sequence | Similarity-based (cosine similarity), across different sessions/users |
