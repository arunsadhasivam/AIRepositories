# RAG KV Cache — Redis + Ollama Reference Guide
> Deterministic Chunk Ordering for KV Cache Prefix Stability

---

## What is KV Cache Prefix Stability?

When you send the same context chunks to Ollama in the **same order every time**, Ollama's internal KV cache (Key-Value attention cache) reuses computed attention tensors — skipping recomputation.

```
Same chunk order → same token prefix → KV cache hit → faster inference
Different order  → different prefix  → KV cache miss → full recompute
```

---

## Redis Cache — Key vs Value

| | What | How Generated | Purpose |
|---|---|---|---|
| **Key** | MD5 hash string | MD5 of sorted+joined chunk text | Same docs → same key → Redis hit |
| **Value** | Joined context string | Sorted chunks joined with `\n---\n` | Passed directly to Ollama as context |

### Example:

```
Redis Key:   "a3f2c1d4e5b6f7a8..."   ← MD5 hex digest
Redis Value: "chunk1 text\n---\nchunk2 text\n---\nchunk3 text"
```

---

## Why Sort by MD5?

Retriever returns chunks in **relevance score order** — this changes per query run.

```
Run 1: [chunk_B, chunk_A, chunk_C]   ← different order
Run 2: [chunk_A, chunk_C, chunk_B]   ← same docs, different order
```

Without sorting → different Redis key every time → always a cache miss.

MD5 sort gives each chunk a **deterministic position**:

```
chunk content → MD5 hex → sort position
Same content  → same MD5 → same position → every time, guaranteed
```

---

## getKVStableContext — Correct Implementation

```python
import hashlib

def getKVStableContext(retrieved_docs, top_k=2):
    # take only top_k chunks — prevent context overflow
    contents = [doc.page_content for doc in retrieved_docs[:top_k]]

    # sanitize: remove Jinja2 template-breaking characters
    # Mistral uses Jinja2 chat template internally — {{ }} {% %} breaks it
    def sanitize(text):
        text = text.replace("{{", "{ {")       # breaks Jinja2 template
        text = text.replace("}}", "} }")       # breaks Jinja2 template
        text = text.replace("{%", "{ %")       # breaks Jinja2 template
        text = text.replace("%}", "% }")       # breaks Jinja2 template
        text = text.replace("\x00", "")        # null bytes crash runner
        return text

    sanitized = [sanitize(c) for c in contents]

    # sort by MD5 hash of each chunk — deterministic order
    sorted_chunks = sorted(
        sanitized,
        key=lambda x: hashlib.md5(x.encode()).hexdigest()
    )

    # Redis KEY — MD5 of the full sorted+joined string
    cache_key = hashlib.md5(
        "\n---\n".join(sorted_chunks).encode()
    ).hexdigest()

    # Redis VALUE / Ollama context — sorted chunks joined
    context = "\n---\n".join(sorted_chunks)

    return cache_key, context
```

---

## RAG Chain — Correct Implementation

### Bug (original):
```python
# WRONG — RunnablePassthrough() passes entire dict to both context and question
{"context": RunnablePassthrough(), "question": RunnablePassthrough()}
```

Mistral receives `{"context": "...", "question": "..."}` dict as context → malformed input → Ollama runner crashes connection.

### Fix:
```python
from operator import itemgetter

rag_chain = (
    {
        "context": itemgetter("context"),    # extracts stable_context string only
        "question": itemgetter("question")   # extracts query string only
    }
    | prompt
    | llm
    | StrOutputParser()
)
```

---

## Full RAG Generation Flow

```python
import hashlib
import redis
import logging
from operator import itemgetter
from langchain_core.output_parsers import StrOutputParser

redis_client = redis.Redis(host="localhost", port=6379, db=0)
CACHE_TTL = 3600  # 1 hour

def rag_generate(query, retriever, prompt, llm):
    logging.debug("::::: OLLAMA RAG GENERATION :::::::::::::::")

    # Step 1: retrieve chunks from vector store
    retrieved_docs = retriever.invoke(query)

    # Step 2: stable context + cache key
    cache_key, stable_context = getKVStableContext(retrieved_docs, top_k=2)

    # Step 3: Redis cache check
    cached = redis_client.get(cache_key)
    if cached:
        logging.debug("::::: REDIS CACHE HIT :::::::::::::::::::::")
        return cached.decode("utf-8")

    # Step 4: build chain with itemgetter (not RunnablePassthrough)
    rag_chain = (
        {
            "context": itemgetter("context"),
            "question": itemgetter("question")
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    # Step 5: invoke Ollama
    response = rag_chain.invoke({
        "context": stable_context,
        "question": query
    })

    # Step 6: store in Redis
    redis_client.setex(cache_key, CACHE_TTL, response)

    return response
```

---

## Prompt Template

Must match `{context}` and `{question}` keys exactly:

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_template("""
Use the context below to answer the question.
Context: {context}
Question: {question}
Answer:""")
```

---

## Context Window Budget (RTX 2000 Ada — 8GB)

| Component | Approx Tokens | Notes |
|---|---|---|
| System prompt | ~200 | Fixed overhead |
| Question | ~50 | Per query |
| 1 chunk (512 chars) | ~128 | 1 token ≈ 4 chars |
| 2 chunks | ~256 | Recommended top_k |
| Response buffer | ~512 | Ollama needs headroom |
| **Total (safe)** | **~1000** | Well within 4096 |

### Why chunk_size=2048 crashes:
```
2048 chars ÷ 4 = 512 tokens per chunk
3 chunks    = 1536 tokens
+ overhead  = ~1800 tokens
+ response  = ~2300 tokens   ← safe

But 4-5 chunks + large system prompt → 4096+ → Ollama crashes connection
```

**Recommended chunk_size: 400–512 chars**

---

## Ollama Context Config

Set before starting Ollama to expand context window:

```bash
# Windows
set OLLAMA_CONTEXT_LENGTH=8192

# Linux/Mac
export OLLAMA_CONTEXT_LENGTH=8192
```

Your RTX 2000 Ada has ~3.2GB VRAM free after model load — 8192 context needs ~500MB more KV cache. Safe to set.

---

## Bug Summary

| Bug | Symptom | Fix |
|---|---|---|
| `RunnablePassthrough()` with dict input | Ollama connection abruptly terminates | Use `itemgetter("context")` and `itemgetter("question")` |
| Jinja2 chars in chunk content (`{{`, `}}`) | Ollama runner crashes | Sanitize chunks before passing |
| chunk_size too large × too many chunks | Context overflow → connection drop | Limit top_k=2, chunk_size=512 chars |
| Sorted string used as Ollama context directly | Semantic disorder → incoherent output | Separate cache key from context string |

---

## Your Setup Reference

| Property | Value |
|---|---|
| Model | Mistral-7B-Instruct-v0.3 Q4_K_M |
| GPU | NVIDIA RTX 2000 Ada 8GB |
| Ollama context | 4096 tokens (set to 8192 recommended) |
| Redis cache TTL | 3600 seconds |
| Recommended chunk_size | 400–512 chars |
| Recommended top_k | 2 chunks |
| Cache key | MD5 of sorted+joined chunks |
| Cache value | Sorted+joined context string |
