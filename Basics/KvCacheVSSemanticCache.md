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
cache = []                                             # list of dicts acting as our vector cache: [{vector, query, answer}]

def check_cache(query, threshold=0.9):
    query_vec = model.encode(query, convert_to_tensor=True)              # embed the new query into a vector
    for entry in cache:                                                   # loop through existing cache entries
        similarity = util.cos_sim(query_vec, entry["vector"]).item()      # compare similarity to each stored vector
        if similarity > threshold:                                       # crosses match threshold
            return entry["answer"]                                       # match found -> return cached answer (cache HIT)
    return None                                                          # no match found -> cache MISS

def store_in_cache(query, answer):
    query_vec = model.encode(query, convert_to_tensor=True)   # embed the query into a vector (this becomes the KEY)
    entry = {
        "vector": query_vec,       # KEY -> used for similarity search on future lookups
        "query": query,            # stored for reference/debugging only, not used in matching
        "answer": answer           # VALUE -> what gets returned on a cache HIT
    }
    cache.append(entry)            # persist the new entry into the cache (in production this would be a vector DB insert)
```

**Usage (cache miss → call LLM → store using store_in_cache):**

```python
query = "Tell me France's capital city"

answer = check_cache(query)          # check if a similar query already exists

if answer is None:                    # cache MISS
    answer = call_llm(query)          # call LLM to get a fresh answer
    store_in_cache(query, answer)     # store the new query-vector -> answer pair for future lookups
    print("MISS - called LLM:", answer)
else:                                 # cache HIT
    print("HIT - reused cached answer:", answer)
```

---

## 3. Layered caching — normalized/sorted cache and semantic cache

Normalized/sorted deterministic cache and semantic cache are typically **layered together**, checked in order of cost, before ever calling the LLM.

**Order of checks:**

```
New query arrives
   ↓
1. Check NORMALIZED/SORTED cache (lowercase, strip stopwords, sort tokens -> use as key)
   → HIT? return instantly (no embedding needed)
   → MISS? go to step 2
   ↓
2. Check SEMANTIC cache (embed query, cosine similarity search)
   → HIT? return cached answer (still cheaper than an LLM call)
   → MISS? go to step 3
   ↓
3. Call the LLM (most expensive, last resort)
   → store result in normalized cache AND semantic cache for next time
```

### 3.1 Normalized / sorted deterministic cache

A cheap first layer: normalize the query (lowercase, remove stopwords/punctuation, sort remaining tokens alphabetically), then use that normalized string as an exact-match key. Catches reordered phrasing cheaply, without needing embeddings.

**Example:**

```
Query A: "What is capital of France"
Query B: "What is France capital"

Normalize both:
  -> lowercase
  -> remove stopwords ("is", "of")
  -> sort remaining tokens alphabetically

Query A tokens: ["capital", "france"]  (sorted)
Query B tokens: ["capital", "france"]  (sorted)

Normalized key for both: "capital_france"   -> SAME KEY -> cache HIT, no embedding needed
```

**What it CANNOT catch (still needs semantic cache):**

```
"What is capital of France"  vs  "Tell me France's capital city"

Normalized tokens A: ["capital", "france"]
Normalized tokens B: ["capital", "citys", "france", "tell"]   -> different vocabulary, NO overlap match
```
Different words, not just different order — normalized/sorted cache misses this. Only semantic cache (embeddings) catches true paraphrases with different vocabulary.

**Comparison:**

| Technique | "capital of France" vs "France capital" | "capital of France" vs "tell me France's capital city" | Cost |
|---|---|---|---|
| Normalized/sorted cache | **Match** (same sorted tokens) | No match (different vocabulary) | Cheap (no embedding) |
| Semantic cache | Match | Match | Higher (embedding + similarity search) |

**Interview line:** "A normalized/sorted deterministic cache is a lightweight first layer — it catches queries using the same words in different order, cheaply, without embeddings. But it can't catch true paraphrases with different vocabulary — that's still semantic cache's job. So the layering becomes: normalized/sorted cache -> semantic cache -> LLM."

**Code (Python):**

```python
normalized_cache = {}   # plain dict, key = normalized sorted string, value = answer

def normalize(query):
    words = query.lower().split()                              # lowercase and split into words
    words = [w for w in words if w not in ("what", "is", "of", "the")]  # strip common stopwords
    return "_".join(sorted(words))                              # sort tokens, join into one key string

def check_normalized_cache(query):
    key = normalize(query)          # build the normalized key -> e.g. "capital_france"
    return normalized_cache.get(key)  # exact-match lookup on the normalized key (dict.get = normal exact-match cache)

def store_in_normalized_cache(query, answer):
    key = normalize(query)          # same normalization used for lookup
    normalized_cache[key] = answer  # store answer under the normalized key
```

**Usage:**

```python
query = "What is France capital"

answer = check_normalized_cache(query)   # try normalized cache first (cheap, no embedding)
if answer is None:
    answer = call_llm(query)              # cache miss -> call LLM
    store_in_normalized_cache(query, answer)  # store for next time
    print("MISS:", answer)
else:
    print("HIT:", answer)
```

---

## 4. Side-by-side comparison

| | KV Cache | Semantic Cache |
|---|---|---|
| Layer | Inside the transformer, during generation | Application/API layer, before calling the LLM |
| What it avoids | Recomputing attention for already-processed tokens | Recalling the LLM for a semantically repeated question |
| Storage | GPU memory (temporary, per-request) | Vector DB (persistent, across users/requests) |
| Analogy | Dynamic programming / memoized Fibonacci | Cache lookup by meaning, not exact string |
| Who implements it | Model-serving infrastructure (already built-in) | Application developer (custom build) |
| Match type | Exact — reuses only already-computed tokens in current sequence | Similarity-based (cosine similarity), across different sessions/users |
