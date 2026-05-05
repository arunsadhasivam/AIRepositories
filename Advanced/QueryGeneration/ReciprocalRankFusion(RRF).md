
RRF:
=====

- Solr returns BM25 ranked results
- pgvector returns semantic ranked results
- RRF merges both by rank position

Formula:
=========
      score = Σ 1 / (k + rank)


- k is a smoothing constant that prevents top-ranked documents from dominating too heavily.


# Reciprocal Rank Fusion (RRF)

## Formula

```
score = 1 / (k + rank)
```

`k` is a **smoothing constant** (default = 60) that prevents top-ranked documents from dominating too heavily.

---

## What happens without k (k=0)

| Rank | Score (no k)     |
|------|------------------|
| 1    | 1/1 = **1.0**    |
| 2    | 1/2 = 0.5        |
| 10   | 1/10 = 0.1       |

> Rank 1 scores **10x** more than rank 10 — too aggressive. Small rank differences cause huge score gaps.

---

## What happens with k=60

| Rank | Score (k=60)  |
|------|---------------|
| 1    | 1/61 = 0.0163 |
| 2    | 1/62 = 0.0161 |
| 10   | 1/70 = 0.0142 |

> Scores are **close together** — rank differences are smoothed out. A rank 10 doc still has a fair chance if the other retriever also ranked it highly.

---

## How RRF is Calculated (Step by Step)

### Setup
- **Solr BM25 results** → `[doc7, doc3, doc22, doc11]`
- **pgvector semantic results** → `[doc3, doc7, doc55, doc22]`
- `k = 60`

---

### Step 1 — Assign RRF score from Solr ranks

| DocId | Solr Rank | Calculation      | Score  |
|-------|-----------|------------------|--------|
| doc7  | 1         | 1 / (60 + 1)     | 0.0164 |
| doc3  | 2         | 1 / (60 + 2)     | 0.0161 |
| doc22 | 3         | 1 / (60 + 3)     | 0.0159 |
| doc11 | 4         | 1 / (60 + 4)     | 0.0156 |

---

### Step 2 — Assign RRF score from pgvector ranks

| DocId | Vector Rank | Calculation      | Score  |
|-------|-------------|------------------|--------|
| doc3  | 1           | 1 / (60 + 1)     | 0.0164 |
| doc7  | 2           | 1 / (60 + 2)     | 0.0161 |
| doc55 | 3           | 1 / (60 + 3)     | 0.0159 |
| doc22 | 4           | 1 / (60 + 4)     | 0.0156 |

---

### Step 3 — Sum scores per docId (fusion)

| DocId | Solr Score | Vector Score | **Final RRF Score**  |
|-------|------------|--------------|----------------------|
| doc3  | 0.0161     | 0.0164       | **0.0325** ✅ Winner |
| doc7  | 0.0164     | 0.0161       | **0.0325** ✅        |
| doc22 | 0.0159     | 0.0156       | **0.0315**           |
| doc11 | 0.0156     | —            | 0.0156               |
| doc55 | —          | 0.0159       | 0.0159               |

---

### Step 4 — Final Ranking (sorted by RRF score descending)

```
1. doc3  → 0.0325
2. doc7  → 0.0325
3. doc22 → 0.0315
4. doc55 → 0.0159  (only in vector results)
5. doc11 → 0.0156  (only in Solr results)
```

> **Key insight:** Docs appearing in **both** retrievers dominate.  
> `doc55` and `doc11` — found by only one retriever — rank low regardless of their individual rank.

---

## Why k=60?

Empirically determined in the **original RRF research paper (Cormack, 2009)** to work well across many IR datasets. Not tunable in practice — just use 60.


CODE:
======

```
from langchain.schema import BaseRetriever, Document
from pydantic import Field
import requests

class SolrRetriever(BaseRetriever):
    
    solr_url: str = Field(...)  # e.g. http://localhost:8983/solr/clinical
    top_k: int = Field(default=10)

    def _get_relevant_documents(self, query: str) -> list[Document]:
        
        # call Solr via HTTP
        response = requests.get(self.solr_url + "/select", params={
            "q": query,
            "defType": "edismax",       # extended dismax parser
            "qf": "title^10 body^1",   # field boost
            "rows": self.top_k,
            "wt": "json"
        })
        
        docs = []
        for hit in response.json()["response"]["docs"]:
            docs.append(Document(
                page_content=hit.get("body", ""),
                metadata={"id": hit.get("id"), "title": hit.get("title")}
            ))
        return docs

# plug Solr into EnsembleRetriever
solr_retriever = SolrRetriever(solr_url="http://localhost:8983/solr/clinical")

hybrid_retriever = EnsembleRetriever(
    retrievers=[solr_retriever, vector_retriever],
    weights=[0.5, 0.5]
)

```
