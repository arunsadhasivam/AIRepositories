# RAG Strategies - Comprehensive Comparison

---

## Quick Decision Guide - When to Use What

| Scenario | Use This |
|---|---|
| Query is specific and well-formed | Normal RAG |
| Query is short or sparse — "404 error" | HyDE |
| Query is vague or ambiguous | MultiQueryRetriever |
| First retrieval returns noisy results | Query Rewriting |
| Vague query + precision needed | MultiQueryRetriever + Query Rewriting |

---

## Detailed Comparison Table

| | **Normal RAG** | **HyDE** | **MultiQueryRetriever** | **Query Rewriting** | **MultiQuery + Rewriting** |
|---|---|---|---|---|---|
| **What it does** | Direct query → vector search | Generates hypothesis → vector search | Generates N query variations → N searches → merge | Uses first retrieved docs to rewrite query → search again | Broad coverage first → rewrite for precision |
| **Problem it solves** | Basic retrieval | Sparse/short query weak embedding | Single query misses relevant docs | First retrieval too noisy or vague | Vague query + noisy first retrieval |
| **When to use** | Specific well-formed queries | Short/sparse queries like error codes | Vague/ambiguous queries | Complex multi-part questions | High precision clinical/legal RAG |
| **Why it alone solves** | Query is already good enough | Hypothesis bridges vocabulary gap | Multiple phrasings cover more docs | Retrieved context guides better query | Combines coverage and precision |
| **LLM calls** | 1 | 2 | 2 | 3 | 4 |
| **Vector DB searches** | 1 | 1 | N | 2 | N + 1 |
| **Extra LLM calls** | 0 | 1 (hypothesis) | 1 (query variations) | 2 (rewriter + answer) | 3 (variations + rewriter + answer) |
| **Result merging** | No | No | Yes — deduplicates | No | Yes — deduplicates first pass |
| **Retrieval quality** | Base | Better embedding match | Broader coverage | More precise second retrieval | Broadest coverage + most precise |
| **Advantages** | Fast, cheap, simple | Bridges vocabulary gap, no special class | Covers more docs, auto dedup | Precision improves with context | Best of both — coverage + precision |
| **Disadvantages** | Misses conceptually related docs | Wrong hypothesis = worse results | High latency, costly at scale | 2 vector searches + 3 LLM calls | Most expensive, highest latency |
| **Cost** | Low | Medium | Medium-High | High | Very High |
| **Latency** | Low | Medium | High | High | Very High |
| **LLM hallucination risk** | Low | Medium — hypothesis may be wrong | Low — just rephrasing | Low — context guides rewrite | Low |
| **Special class needed** | No | No | Yes — `MultiQueryRetriever` | No | Yes — `MultiQueryRetriever` |
| **Prompt controls behavior** | No | Yes — hypothesis style | Yes — restrict query count | Yes — rewrite instruction | Yes — both |
| **Best domain** | General | Error codes, sparse queries | Medical, legal, broad topics | Clinical, legal, complex questions | Production clinical/legal RAG |
| **Recursive/infinite risk** | No | No | No — one level deep | No | No |
| **Order of operations** | Vector → LLM | LLM → Vector → LLM | LLM → N×Vector → LLM | Vector → LLM → Vector → LLM | LLM → N×Vector → LLM → Vector → LLM |

---

## Cost Summary

| Strategy | LLM Calls | Vector Searches | Relative Cost |
|---|---|---|---|
| Normal RAG | 1 | 1 | ⭐ Lowest |
| HyDE | 2 | 1 | ⭐⭐ Low-Medium |
| MultiQueryRetriever | 2 | N | ⭐⭐⭐ Medium-High |
| Query Rewriting | 3 | 2 | ⭐⭐⭐ High |
| MultiQuery + Rewriting | 4 | N+1 | ⭐⭐⭐⭐ Highest |

> **Note:** If using local Ollama/Mistral, LLM calls are free.
> Cost matters only with paid APIs like OpenAI.
> Vector DB search (pgvector) is always cheap — just a math operation.

---

## Issue Solved Summary

| Strategy | Core Issue Solved |
|---|---|
| Normal RAG | No issue — baseline retrieval |
| HyDE | Weak embedding from short/sparse queries |
| MultiQueryRetriever | Single query phrasing misses relevant docs |
| Query Rewriting | First retrieval too noisy — needs refinement |
| MultiQuery + Rewriting | Vague query needs both wide coverage and precision |

---

## Retrieval Quality vs Cost Tradeoff

```
Retrieval Quality
      ↑
High  |                                    ★ MultiQuery + Rewriting
      |                          ★ Query Rewriting
      |               ★ MultiQueryRetriever
      |     ★ HyDE
Low   | ★ Normal RAG
      +------------------------------------------------→ Cost / LLM Calls
           Low          Medium         High        Very High
```
