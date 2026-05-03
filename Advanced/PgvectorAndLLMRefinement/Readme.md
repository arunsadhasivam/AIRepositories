# Clinical RAG Pipeline — pgvector & LLM Calls Reference

## Overview

All techniques grouped by whether they hit **pgvector** or **LLM**.
Each call listed with input, output, and optimization notes.

---

## GROUP 1 — pgvector Calls

### 1. HybridRetriever — Main Retrieval

**When:** Every user query, core retrieval step.

**Input:** Embedded user query vector (768 dim, nomic-embed-text)

**Output:** Top 5 ranked chunks via RRF (pgvector cosine + Solr BM25)

```python
def hybrid_retrieve(query: str) -> list:
    # Embed the query using nomic-embed-text
    query_vector = embed_model.encode(query)

    # pgvector cosine similarity search
    pg_results = pg_conn.execute("""
        SELECT chunk_id, content, 1 - (embedding <=> %s::vector) AS score
        FROM clinical_documents
        ORDER BY embedding <=> %s::vector
        LIMIT 10
    """, (query_vector.tolist(), query_vector.tolist()))

    # Solr BM25 search runs in parallel
    solr_results = solr_client.search(query, rows=10)

    # Reciprocal Rank Fusion to merge both result sets
    return reciprocal_rank_fusion(pg_results, solr_results, top_k=5)
```

**Optimization:**
- Use HNSW index on pgvector (not IVFFlat) for low-latency ANN search
- Limit to top 10 from each source before RRF, not top 50

---

### 2. Crisis Page Routing — pgvector Lookup

**When:** Input guardrail detects suicidal/crisis intent.

**Input:** Fixed query string — "suicide self-harm crisis helpline resources"

**Output:** Production URL of closest matching crisis page

```python
def find_crisis_page() -> dict:
    # Use fixed query — crisis routing is not dynamic
    crisis_query = "suicide self-harm crisis helpline resources"
    query_vector = embed_model.encode(crisis_query)

    # Find closest pre-indexed crisis page
    result = pg_conn.execute("""
        SELECT page_url, page_title, content
        FROM crisis_pages
        WHERE embedding <=> %s::vector < 0.3   -- threshold filter
        ORDER BY embedding <=> %s::vector
        LIMIT 1
    """, (query_vector.tolist(), query_vector.tolist()))

    return result.fetchone()
```

**Optimization:**
- Pre-index crisis pages at deploy time, not at query time
- Use threshold filter (`< 0.3`) to avoid false matches
- Cache result in Redis — crisis page URLs rarely change

---

### pgvector Similarity Search — Two Approaches

Instead of writing raw SQL every time, wrap into reusable similarity search methods.

---

#### Option 1 — LangChain PGVector (recommended — you already use LangChain)

```python
from langchain_community.vectorstores import PGVector
from langchain_community.embeddings import OllamaEmbeddings

# One time setup at app startup
embed_model = OllamaEmbeddings(model="nomic-embed-text")

vector_store = PGVector(
    connection_string="postgresql://user:pass@localhost:5432/clinical_db",
    embedding_function=embed_model,
    collection_name="clinical_documents"
)

# Simple similarity search — no raw SQL needed
def similarity_search(query: str, k: int = 5) -> list:
    # LangChain handles embedding + cosine search internally
    return vector_store.similarity_search(query, k=k)

# With score — returns (Document, score) tuples
def similarity_search_with_score(query: str, k: int = 5) -> list:
    # Score is cosine similarity — higher is better
    return vector_store.similarity_search_with_score(query, k=k)

# Usage in HybridRetriever
pg_results = similarity_search(rewritten_query, k=10)
pg_results_scored = similarity_search_with_score(rewritten_query, k=10)
```

---

#### Option 2 — Your Own Wrapper (full SQL control)

```python
def similarity_search(query: str, k: int = 5, threshold: float = None) -> list:
    # Embed query using nomic-embed-text
    query_vector = embed_model.encode(query).tolist()

    # Build query — optionally apply similarity threshold
    if threshold:
        # Only return results above similarity threshold
        results = pg_conn.execute("""
            SELECT chunk_id, content,
                   1 - (embedding <=> %s::vector) AS similarity_score
            FROM clinical_documents
            WHERE 1 - (embedding <=> %s::vector) >= %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_vector, query_vector, threshold, query_vector, k))
    else:
        # Return top k regardless of score
        results = pg_conn.execute("""
            SELECT chunk_id, content,
                   1 - (embedding <=> %s::vector) AS similarity_score
            FROM clinical_documents
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_vector, query_vector, k))

    return results.fetchall()

# Usage — clean single line calls
pg_results          = similarity_search(rewritten_query, k=10)
pg_results_filtered = similarity_search(rewritten_query, k=10, threshold=0.75)
crisis_page         = similarity_search(crisis_query, k=1, threshold=0.70)
```

---

#### Which to Use

| | LangChain PGVector | Your Own Wrapper |
|---|---|---|
| Code simplicity | Cleanest — 1 line | Moderate |
| SQL control | Hidden | Full control |
| Threshold filtering | Not built-in | Built-in |
| Works with HybridRetriever | Needs customization | Direct plug-in |
| Already in your stack | Yes — LangChain imported | Extra wrapper code |

**Recommendation for your pipeline:** Use LangChain for standard retrieval. Use your own wrapper for crisis routing where threshold filtering is mandatory.

---

## GROUP 2 — LLM Calls

### 3. Input Guardrail — Crisis Classifier

**When:** Every user message, runs first before anything else.

**Input:** Raw user message

**Output:** JSON — intent (normal/suicidal), confidence, action

```python
def input_guardrail(user_message: str) -> dict:
    prompt = f"""
    You are a clinical input safety evaluator.

    User Message: {user_message}

    Does this message indicate suicidal or self-harm intent?

    Reply only in JSON, no extra text:
    {{
        "intent": "normal" or "suicidal",
        "confidence": 0.0-1.0,
        "action": "proceed" or "crisis_route"
    }}
    """

    # temperature=0 — deterministic, no randomness in safety checks
    response = ollama.chat(
        model="mistral",
        options={"temperature": 0},
        messages=[{"role": "user", "content": prompt}]
    )

    return json.loads(response['message']['content'].strip())
```

**Optimization:**
- Run keyword/regex check FIRST (zero latency) — if obvious, skip LLM call entirely
- LLM classifier only fires if regex does not match

---

### 4. Query Rewriting — Improve Retrieval Quality

**When:** Before HybridRetriever, after guardrail passes.

**Input:** Raw vague user query

**Output:** Rewritten clinical query string

```python
def rewrite_query(user_query: str) -> str:
    prompt = f"""
    You are a clinical query optimizer.

    Original Query: {user_query}

    Rewrite this query to be more specific for medical document search.
    Return only the rewritten query, no explanation.
    """

    response = ollama.chat(
        model="mistral",
        options={"temperature": 0},
        messages=[{"role": "user", "content": prompt}]
    )

    return response['message']['content'].strip()
```

**Optimization:**
- Skip rewriting for queries already > 8 words (likely specific enough)
- Cache rewritten queries in Redis by original query hash

---

### 5. Primary LLM — Answer Generation

**When:** After HybridRetriever returns top chunks.

**Input:** Rewritten query + top 5 retrieved chunks

**Output:** Streaming answer text to user

```python
def generate_answer(query: str, chunks: list) -> str:
    context = "\n".join([f"Chunk {i+1}: {c}" for i, c in enumerate(chunks)])

    prompt = f"""
    You are a clinical assistant at Stanford Children's Health.
    Answer using only the provided context. Do not hallucinate.

    Question: {query}

    Context:
    {context}

    Answer:
    """

    # Stream response to user
    response = ollama.chat(
        model="mistral",
        options={"temperature": 0.3},   # slight creativity for natural language
        messages=[{"role": "user", "content": prompt}],
        stream=True
    )

    return response
```

**Optimization:**
- Stream response — user sees tokens immediately, no full wait
- KV cache: sort chunks by MD5 hash for deterministic ordering — Ollama reuses KV cache

---

### 6. LLM-as-Judge — Faithfulness Evaluation

**When:** After primary LLM generates answer.

**Input:** Original query + same top 5 chunks + generated answer

**Output:** JSON — faithfulness score, relevance score, pass/fail, reason

```python
def llm_judge(query: str, chunks: list, generated_answer: str) -> dict:
    context = "\n".join([f"Chunk {i+1}: {c}" for i, c in enumerate(chunks)])

    prompt = f"""
    You are a clinical answer evaluator.

    Question: {query}

    Retrieved Context:
    {context}

    Generated Answer:
    {generated_answer}

    Score the answer against the retrieved context only.

    - faithfulness: Is every claim in the answer supported by context?
      1.0 = fully grounded, 0.0 = fully hallucinated

    - relevance: Does the answer address the question?
      1.0 = directly answers, 0.0 = off topic

    Reply only in JSON, no extra text:
    {{
        "faithfulness": 0.0-1.0,
        "relevance": 0.0-1.0,
        "pass": true/false,
        "reason": "one line reason"
    }}
    """

    # temperature=0 — deterministic scoring
    response = ollama.chat(
        model="mistral",
        options={"temperature": 0},
        messages=[{"role": "user", "content": prompt}]
    )

    return json.loads(response['message']['content'].strip())
```

**Optimization:**
- Run async for non-critical FAQ queries — user never waits
- Run inline (critical path) only for drug/diagnosis questions
- Sample 20% of traffic for async judge — not every request needs scoring
- Max 2 retries before hard fallback to avoid infinite loops

---

## Full Pipeline Summary

```
User Message
    |
    |-- [LLM Call 3] Input Guardrail (crisis check)
    |       |
    |       |-- crisis detected --> [pgvector Call 2] Crisis Page Lookup --> return URL
    |       |
    |       |-- normal --> continue
    |
    |-- [LLM Call 4] Query Rewriting
    |
    |-- [pgvector Call 1] HybridRetriever (pgvector + Solr + RRF)
    |
    |-- [LLM Call 5] Primary LLM Answer Generation (streaming)
    |
    |-- [LLM Call 6] LLM Judge (async or inline)
    |       |
    |       |-- pass --> return answer to user
    |       |-- fail --> retry (max 2) --> fallback message
```

---

## All Calls At a Glance

| # | Type | Call | Input | Output | Async? |
|---|------|------|-------|--------|--------|
| 1 | pgvector | HybridRetriever | query vector | top 5 chunks | No |
| 2 | pgvector | Crisis Page Lookup | fixed crisis vector | prod page URL | No |
| 3 | LLM | Input Guardrail | user message | intent JSON | No (blocks pipeline) |
| 4 | LLM | Query Rewriting | raw query | rewritten query string | No |
| 5 | LLM | Primary Generation | query + chunks | streaming answer | No (streamed) |
| 6 | LLM | LLM Judge | query + chunks + answer | score JSON | Yes (except critical) |

---

## Optimizations Summary

| Optimization | Applies To | Benefit |
|---|---|---|
| Regex before LLM guardrail | Call 3 | Saves full LLM call for obvious cases |
| Skip rewrite if query > 8 words | Call 4 | Saves LLM call for specific queries |
| Redis cache rewritten queries | Call 4 | Zero latency on repeated similar queries |
| MD5 chunk sort for KV cache | Call 5 | Ollama reuses KV cache, faster inference |
| Stream primary answer | Call 5 | User sees response immediately |
| Async judge on 20% sample | Call 6 | No latency added to user response |
| Pre-index crisis pages at deploy | Call 2 | Zero compute at query time |
| HNSW index on pgvector | Call 1 | Faster ANN search vs IVFFlat |
