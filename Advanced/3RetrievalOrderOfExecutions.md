# RAG Retrieval Strategies - Intuition Guide

## Intuitive Analogy - Job Search

| Strategy | Job Search Analogy |
|---|---|
| **Normal RAG** | You search LinkedIn directly with your exact job title |
| **HyDE** | You first write a **fake job description** of your dream job, then search for jobs matching that description |
| **MultiQueryRetriever** | You search LinkedIn with **multiple titles** — "Software Engineer", "Java Developer", "Backend Engineer" — merge all results |

**Core intuition:**
- Normal RAG → **You know exactly what to search**
- HyDE → **You imagine the answer first, then find it**
- MultiQueryRetriever → **You cast a wider net with different wordings**

---

## Order of Operations

### Normal RAG
Vector first, LLM last.

| Step | Action |
|---|---|
| 1 | User query → Embed query |
| 2 | Embed → Vector DB search |
| 3 | Retrieved docs → LLM → Answer |

---

### HyDE
LLM first to generate hypothesis, then Vector search, then LLM again for answer.

| Step | Action |
|---|---|
| 1 | User query → LLM → Generate hypothesis |
| 2 | Hypothesis → Embed → Vector DB search |
| 3 | Retrieved docs + Original query → LLM → Answer |

---

### MultiQueryRetriever
LLM first to generate variations, then Vector search for each, then LLM for answer.

| Step | Action |
|---|---|
| 1 | User query → LLM → Generate N query variations |
| 2 | Each variation → Embed → Vector DB search |
| 3 | Merge + Deduplicate all results |
| 4 | Merged docs + Original query → LLM → Answer |

---

## Summary

| | Normal RAG | HyDE | MultiQueryRetriever |
|---|---|---|---|
| **Order** | Vector first, LLM last | LLM first, Vector second, LLM last | LLM first, Vector second, LLM last |
| **Extra LLM calls** | 0 | 1 | 1 |
| **Vector DB searches** | 1 | 1 | N |
| **Result merging** | No | No | Yes |
| **Cost** | Low | Medium | Medium-High |
