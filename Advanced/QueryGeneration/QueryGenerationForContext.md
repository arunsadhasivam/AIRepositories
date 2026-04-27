# Query Generation Strategies - Complete Guide

Query generation is the technique of using an LLM to **automatically generate the right query format**
for different data stores from a plain user question.

---

## 1. Vector DB Query Generation

### What is it?
LLM rewrites the user question into a **better semantic search query** optimized for vector similarity search.

### Why use it?
- User questions are often conversational and wordy
- Vector DB needs **dense, focused semantic text** to embed well
- Rewritten query produces better embedding match against stored documents

### When to use it?
- Searching **unstructured documents** — clinical notes, manuals, help docs
- User query is vague or conversational
- Documents are stored as embeddings in pgvector, ChromaDB, Pinecone

### Why this alone solves it?
- Unstructured text cannot be queried with SQL or keywords
- Only semantic similarity search can find **conceptually related** content
- LLM rewriting bridges gap between user language and document language

### Advantages
- Handles natural language queries
- Finds conceptually related docs even if exact words don't match
- No schema knowledge needed

### Disadvantages
- Cannot do exact lookups — no `WHERE id = 123`
- Results are approximate — ranked by similarity, not exact match
- Quality depends on embedding model quality

### Example
```
User: "What happens if I take too much aspirin?"
Rewritten: "aspirin overdose symptoms side effects toxicity"
→ Hits pgvector similarity_search()
```

---

## 2. SQL Query Generation (Text-to-SQL)

### What is it?
LLM converts a plain user question into a valid **SQL query** to run against a relational database.

### Why use it?
- Business users cannot write SQL
- Data lives in structured relational tables — orders, patients, sales
- Need **exact, aggregated, filtered** results from structured data

### When to use it?
- Data is in PostgreSQL, MySQL, Oracle, SQLite
- Questions involve **counts, sums, filters, joins** — "How many patients were admitted last month?"
- Exact answers needed, not approximate similarity

### Why this alone solves it?
- Structured data has **exact values** — names, dates, amounts
- SQL can filter, aggregate, join across tables precisely
- Vector search cannot do `GROUP BY` or `SUM()` operations

### Advantages
- Exact results — no approximation
- Can aggregate, filter, sort, join across tables
- Works on existing databases — no re-indexing needed

### Disadvantages
- LLM can generate **wrong SQL** — hallucinated table/column names
- Requires LLM to know the **DB schema** upfront
- Fails on complex multi-join queries
- SQL injection risk if not sanitized

### Example
```
User: "How many patients were admitted in January 2025?"
Generated: SELECT COUNT(*) FROM admissions WHERE admission_date BETWEEN '2025-01-01' AND '2025-01-31'
→ Runs against PostgreSQL
```

---

## 3. Knowledge Graph Query Generation (SPARQL / Cypher)

### What is it?
LLM converts user question into a **graph query** (SPARQL for RDF graphs, Cypher for Neo4j)
to traverse relationships between entities.

### Why use it?
- Data has complex **entity relationships** — doctor treats patient, patient has condition, condition has drug
- Need to traverse **multi-hop relationships** — "Which doctors treated patients who have both diabetes and hypertension?"
- Graph structure captures relationships SQL cannot express naturally

### When to use it?
- Data is in Neo4j, Amazon Neptune, or RDF triple stores
- Questions involve **relationship traversal** — "Who is connected to whom through what?"
- Domain is knowledge-heavy — medical ontologies, legal relationships, org charts

### Why this alone solves it?
- Relational DBs struggle with **recursive or multi-hop** relationship queries
- Vector DB cannot answer **exact relationship** questions
- Graph queries naturally express — "Find all paths between A and B"

### Advantages
- Best for relationship-heavy domains
- Multi-hop traversal is natural and efficient
- Captures ontology and hierarchy well

### Disadvantages
- SPARQL/Cypher are complex — LLM hallucination risk is high
- Requires well-structured knowledge graph upfront
- Not suitable for unstructured or flat data
- Small community, fewer tools than SQL

### Example
```
User: "Which drugs interact with aspirin for diabetic patients?"
Generated Cypher:
MATCH (d:Drug {name: "aspirin"})-[:INTERACTS_WITH]->(d2:Drug)
      <-[:PRESCRIBED_TO]-(p:Patient)-[:HAS_CONDITION]->(c:Condition {name: "diabetes"})
RETURN d2.name
→ Runs against Neo4j
```

---

## 4. Document Query Generation

### What is it?
LLM generates a **structured extraction query** to pull specific fields or sections
from semi-structured documents — PDF, Word, JSON, XML, HTML.

### Why use it?
- Documents have **mixed structure** — tables, paragraphs, headers, metadata
- Need to extract **specific fields** — patient name, date, diagnosis from a clinical PDF
- Cannot use SQL (not a DB) or vector search (need exact field, not similarity)

### When to use it?
- Data is in PDFs, Word docs, JSON files, XML feeds
- Need **targeted extraction** — not full document retrieval
- Documents follow a **known template or schema** — insurance forms, lab reports

### Why this alone solves it?
- PDFs and Word docs are not queryable by SQL
- Vector search returns whole chunks — not specific fields
- LLM can understand document structure and extract precisely

### Advantages
- Works on any document format
- Can extract structured data from unstructured documents
- Handles templates and forms well with Apache Tika or similar

### Disadvantages
- Depends heavily on **document quality** — scanned PDFs fail without OCR
- LLM may misidentify fields in inconsistent formats
- Slow for large document volumes
- Not suitable for real-time querying

### Example
```
User: "What is the patient diagnosis in this lab report?"
LLM extracts: { "patient": "John Doe", "diagnosis": "Type 2 Diabetes", "date": "2025-01-15" }
→ From uploaded PDF via Apache Tika
```

---

## Comparison Table

| | Vector DB Query | SQL Query | Knowledge Graph Query | Document Query |
|---|---|---|---|---|
| **What it does** | Rewrites query for semantic search | Generates SQL for relational DB | Generates SPARQL/Cypher for graph DB | Extracts fields from documents |
| **Data store** | pgvector, ChromaDB, Pinecone | PostgreSQL, MySQL, Oracle | Neo4j, Neptune, RDF | PDF, Word, JSON, XML |
| **When to use** | Unstructured text search | Structured exact/aggregated data | Relationship traversal | Field extraction from docs |
| **Why it alone solves** | Only way to search unstructured text | Only way to aggregate/filter structured data | Only way to traverse multi-hop relationships | Only way to extract fields from mixed format docs |
| **Result type** | Approximate — ranked similarity | Exact — filtered/aggregated rows | Exact — relationship paths | Exact — extracted fields |
| **Expected context** | Clinical notes, manuals, help docs | Orders, patients, sales tables | Medical ontologies, org charts, legal graphs | Lab reports, insurance forms, invoices |
| **Advantages** | Natural language, conceptual match | Exact results, aggregation, joins | Multi-hop relationships, ontology | Works on any doc format |
| **Disadvantages** | No exact lookup, approximate only | LLM hallucates wrong schema | Complex query, high hallucination risk | OCR dependency, slow at scale |
| **Trade-off** | Coverage vs precision | Precision vs schema knowledge needed | Relationship depth vs query complexity | Extraction accuracy vs document consistency |
| **LLM hallucination risk** | Low | Medium | High | Medium |
| **Extra setup needed** | Embed and index documents | Provide DB schema to LLM | Build knowledge graph first | OCR pipeline for scanned docs |
