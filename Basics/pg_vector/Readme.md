# pgvector SQL Guide for SQL Developers

A comprehensive guide to pgvector functions, operators, and query patterns for developers familiar with SQL.

---

## Table of Contents

- [Installation](#installation)
- [Vector Data Type](#vector-data-type)
- [Distance Operators](#distance-operators)
- [Vector Functions](#vector-functions)
- [Index Types](#index-types)
- [Common Query Patterns](#common-query-patterns)
- [Performance Tips](#performance-tips)
- [Common Gotchas](#common-gotchas)
- [Complete Examples](#complete-examples)

---

## Installation

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';
```

---

## Vector Data Type

### Creating Tables with Vectors

```sql
-- Create table with vector column
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500),
    content TEXT,
    category VARCHAR(100),
    embedding vector(1536),  -- 1536 dimensions (OpenAI standard)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Key Points**:
- `vector(N)` where N is the dimension size
- Must specify dimension at table creation
- Like `ARRAY` but optimized for similarity calculations

### Common Dimensions

| Embedding Model | Dimensions |
|----------------|------------|
| OpenAI text-embedding-ada-002 | 1536 |
| OpenAI text-embedding-3-small | 512 or 1536 |
| Sentence Transformers (all-MiniLM-L6-v2) | 384 |
| BERT base | 768 |

---

## Distance Operators

pgvector provides three special operators for calculating vector similarity:

### `<->` Euclidean Distance (L2)

**Calculates**: Straight-line distance between vectors

**Range**: 0 to ∞ (lower = more similar)

**Best for**: Images, spatial data

```sql
-- Find documents closest to query vector
SELECT 
    id, 
    title,
    embedding <-> '[0.1, 0.2, 0.3, ...]'::vector AS distance
FROM documents
ORDER BY embedding <-> '[0.1, 0.2, 0.3, ...]'::vector
LIMIT 5;
```

**SQL Analogy**: Like `ABS(column1 - column2)` but for multi-dimensional vectors

---

### `<=>` Cosine Distance

**Calculates**: 1 - cosine_similarity (measures angle between vectors)

**Range**: 0 to 2 (0 = identical direction, 2 = opposite)

**Best for**: Text, documents, semantic search **(MOST COMMON)**

```sql
-- Find documents with similar meaning
SELECT 
    id,
    title,
    embedding <=> '[0.1, 0.2, 0.3, ...]'::vector AS cosine_distance,
    1 - (embedding <=> '[0.1, 0.2, 0.3, ...]'::vector) AS similarity_score
FROM documents
ORDER BY embedding <=> '[0.1, 0.2, 0.3, ...]'::vector
LIMIT 5;
```

**Why cosine for text?**
- Ignores magnitude, focuses on direction
- "apple apple apple" and "apple" have similar vectors
- Captures meaning regardless of text length

---

### `<#>` Negative Inner Product (Dot Product)

**Calculates**: Negative dot product

**Range**: -∞ to ∞ (lower = more similar because negative)

**Best for**: Normalized vectors, fastest performance

```sql
-- Fast similarity search (requires normalized vectors)
SELECT 
    id,
    title,
    embedding <#> '[0.1, 0.2, 0.3, ...]'::vector AS neg_inner_product
FROM documents
ORDER BY embedding <#> '[0.1, 0.2, 0.3, ...]'::vector
LIMIT 5;
```

**Fastest operator** but vectors must be normalized first.

---

### Operator Comparison

| Operator | Name | Formula | Best For | Speed | Notes |
|----------|------|---------|----------|-------|-------|
| `<->` | L2 Distance | Euclidean | Images, spatial | Medium | Always positive |
| `<=>` | Cosine Distance | 1 - cos(θ) | **Text** | Medium | **Most common** |
| `<#>` | Inner Product | -(a·b) | Normalized | **Fastest** | Requires normalized vectors |

---

## Vector Functions

### `vector_dims()` - Get Dimensions

```sql
-- Check vector dimensions
SELECT vector_dims(embedding) AS dimensions
FROM documents
LIMIT 1;

-- Returns: 1536
```

**SQL Analogy**: Like `LENGTH()` for text or `ARRAY_LENGTH()` for arrays

---

### `vector_norm()` - Get Vector Magnitude

```sql
-- Calculate vector length/magnitude
SELECT 
    id,
    vector_norm(embedding) AS magnitude
FROM documents;
```

**Use case**: Check if vectors are normalized (magnitude = 1)

---

### Casting to Vector

```sql
-- Cast string to vector
SELECT '[1, 2, 3]'::vector;

-- Cast with dimension check
SELECT '[0.1, 0.2, 0.3]'::vector(3);

-- In queries
INSERT INTO documents (embedding) 
VALUES ('[0.1, 0.2, 0.3, ...]'::vector);
```

**SQL Analogy**: Like `'123'::INTEGER` or `'2024-01-01'::DATE`

---

## Index Types

Indexes dramatically improve query performance for large datasets.

### IVFFlat Index (Balanced)

**Good for**: Most use cases, balanced speed/memory

```sql
-- Create IVFFlat index for cosine similarity
CREATE INDEX documents_embedding_idx 
ON documents 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Parameters**:
- `lists` = Number of clusters
- **Rule of thumb**: Use `√(total_rows)` for lists
- Example: 10,000 rows → lists = 100

**Operator classes**:
- `vector_l2_ops` for `<->` (L2 distance)
- `vector_cosine_ops` for `<=>` (cosine distance) ← **Most common**
- `vector_ip_ops` for `<#>` (inner product)

---

### HNSW Index (Faster, More Memory)

**Good for**: Production, high-performance needs

```sql
-- Create HNSW index (recommended for production)
CREATE INDEX documents_embedding_idx
ON documents 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Parameters**:
- `m` = Connections per node (default: 16)
  - Higher = more accurate, more memory
  - Range: 4-64
- `ef_construction` = Build quality (default: 64)
  - Higher = better quality, slower build
  - Range: 4-1000

**Comparison**:

| Feature | IVFFlat | HNSW |
|---------|---------|------|
| Query speed | Good | **Excellent** |
| Build speed | Fast | Slower |
| Memory usage | Low | Higher |
| Accuracy | Good | **Better** |
| Recommended for | Development, testing | **Production** |

---

### Choosing Index Parameters

```sql
-- Small dataset (< 100K rows)
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Medium dataset (100K - 1M rows)
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 24, ef_construction = 100);

-- Large dataset (> 1M rows)
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 32, ef_construction = 128);
```

---

## Common Query Patterns

### Pattern 1: Basic Similarity Search

```sql
-- Find top 5 most similar documents
SELECT 
    id,
    title,
    content,
    1 - (embedding <=> $1::vector) AS similarity_score
FROM documents
WHERE embedding IS NOT NULL
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

**Parameters**:
- `$1` = Query vector as parameter `[0.1, 0.2, ...]`

---

### Pattern 2: Filtered Similarity Search

```sql
-- Find similar documents in specific category
SELECT 
    id,
    title,
    embedding <=> $1::vector AS distance
FROM documents
WHERE category = 'medical'
  AND embedding IS NOT NULL
  AND created_at > NOW() - INTERVAL '1 year'
ORDER BY embedding <=> $1::vector
LIMIT 10;
```

**Performance tip**: Place filters in WHERE clause before ORDER BY

---

### Pattern 3: Similarity Threshold

```sql
-- Only return documents above 80% similarity
SELECT 
    id,
    title,
    1 - (embedding <=> $1::vector) AS similarity
FROM documents
WHERE embedding IS NOT NULL
  AND (1 - (embedding <=> $1::vector)) > 0.8
ORDER BY embedding <=> $1::vector
LIMIT 20;
```

**Use case**: Filter out low-quality matches

---

### Pattern 4: Multiple Filters with Similarity

```sql
-- Complex filtering with similarity search
SELECT 
    d.id,
    d.title,
    d.category,
    d.author,
    1 - (d.embedding <=> $1::vector) AS similarity
FROM documents d
WHERE d.embedding IS NOT NULL
  AND d.category IN ('medical', 'health', 'wellness')
  AND d.status = 'published'
  AND d.language = 'en'
  AND (1 - (d.embedding <=> $1::vector)) > 0.7
ORDER BY d.embedding <=> $1::vector
LIMIT 10;
```

---

### Pattern 5: Join with Similarity

```sql
-- Find similar document pairs (duplicate detection)
SELECT 
    d1.id AS doc1_id,
    d1.title AS doc1_title,
    d2.id AS doc2_id,
    d2.title AS doc2_title,
    1 - (d1.embedding <=> d2.embedding) AS similarity
FROM documents d1
CROSS JOIN documents d2
WHERE d1.id < d2.id  -- Avoid duplicates and self-matches
  AND d1.embedding IS NOT NULL
  AND d2.embedding IS NOT NULL
  AND (1 - (d1.embedding <=> d2.embedding)) > 0.95
ORDER BY similarity DESC
LIMIT 50;
```

**Use case**: Find duplicate or near-duplicate documents

---

### Pattern 6: Similarity with Aggregation

```sql
-- Find average similarity by category
SELECT 
    category,
    COUNT(*) AS doc_count,
    AVG(1 - (embedding <=> $1::vector)) AS avg_similarity,
    MAX(1 - (embedding <=> $1::vector)) AS max_similarity
FROM documents
WHERE embedding IS NOT NULL
GROUP BY category
HAVING AVG(1 - (embedding <=> $1::vector)) > 0.5
ORDER BY avg_similarity DESC;
```

---

### Pattern 7: CTE with Similarity Search

```sql
-- Using CTE for complex queries
WITH query_vector AS (
    SELECT '[0.1, 0.2, ..., 1536 numbers]'::vector(1536) AS vec
),
similar_docs AS (
    SELECT 
        d.id,
        d.title,
        d.category,
        1 - (d.embedding <=> q.vec) AS similarity
    FROM documents d
    CROSS JOIN query_vector q
    WHERE d.embedding IS NOT NULL
      AND (1 - (d.embedding <=> q.vec)) > 0.7
    ORDER BY d.embedding <=> q.vec
    LIMIT 20
)
SELECT 
    sd.*,
    u.name AS author_name,
    u.email AS author_email
FROM similar_docs sd
JOIN users u ON sd.author_id = u.id
ORDER BY sd.similarity DESC;
```

---

## Performance Tips

### Tip 1: Create Appropriate Index

```sql
-- Always create index for similarity queries
CREATE INDEX documents_embedding_idx
ON documents 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Impact**: 10-100x faster queries on large datasets

---

### Tip 2: Increase Memory for Index Build

```sql
-- Temporarily increase memory for index creation
SET maintenance_work_mem = '2GB';

CREATE INDEX documents_embedding_idx
ON documents 
USING hnsw (embedding vector_cosine_ops);

RESET maintenance_work_mem;
```

**For large datasets**: Use 25-50% of available RAM

---

### Tip 3: Analyze After Bulk Operations

```sql
-- After inserting many vectors
COPY documents (title, content, embedding) FROM '/path/to/data.csv' CSV;

-- Update statistics
ANALYZE documents;
```

**Why**: Helps query planner make better decisions

---

### Tip 4: Use Appropriate Search Parameters

```sql
-- Adjust search accuracy vs speed
SET hnsw.ef_search = 100;  -- Higher = more accurate, slower

SELECT * FROM documents
ORDER BY embedding <=> $1::vector
LIMIT 10;

RESET hnsw.ef_search;
```

**Default**: 40
**Range**: 10-1000
**Trade-off**: Accuracy vs speed

---

### Tip 5: Filter Before Similarity

```sql
-- ✅ GOOD - Filter first, then similarity
SELECT * FROM documents
WHERE category = 'medical'
  AND embedding IS NOT NULL
ORDER BY embedding <=> $1::vector
LIMIT 5;

-- ❌ SLOWER - Similarity on all rows, then filter
SELECT * FROM (
    SELECT * FROM documents
    ORDER BY embedding <=> $1::vector
    LIMIT 100
) sub
WHERE category = 'medical'
LIMIT 5;
```

---

### Tip 6: Use Partial Indexes

```sql
-- Index only published documents
CREATE INDEX documents_published_embedding_idx
ON documents 
USING hnsw (embedding vector_cosine_ops)
WHERE status = 'published' AND embedding IS NOT NULL;
```

**Benefit**: Smaller index, faster queries for specific filters

---

## Common Gotchas

### Gotcha 1: Forgetting Vector Cast

```sql
-- ❌ ERROR: No operator matches
SELECT * FROM documents
ORDER BY embedding <=> '[0.1, 0.2, 0.3]'
LIMIT 5;

-- ✅ CORRECT: Must cast to vector type
SELECT * FROM documents
ORDER BY embedding <=> '[0.1, 0.2, 0.3]'::vector
LIMIT 5;
```

---

### Gotcha 2: Dimension Mismatch

```sql
-- Table expects 1536 dimensions
CREATE TABLE documents (embedding vector(1536));

-- ❌ ERROR: Wrong dimension
INSERT INTO documents (embedding)
VALUES ('[0.1, 0.2, 0.3]'::vector);

-- ✅ CORRECT: Must have 1536 numbers
INSERT INTO documents (embedding)
VALUES ('[0.1, 0.2, ..., 1536 numbers]'::vector);
```

---

### Gotcha 3: NULL Vectors

```sql
-- ❌ BAD: Returns NULL for rows with NULL embedding
SELECT embedding <=> $1::vector AS distance
FROM documents;

-- ✅ GOOD: Filter out NULLs
SELECT embedding <=> $1::vector AS distance
FROM documents
WHERE embedding IS NOT NULL;
```

---

### Gotcha 4: Missing Operator Class

```sql
-- ❌ WRONG: Index created but not used
CREATE INDEX ON documents USING ivfflat (embedding);

-- ✅ CORRECT: Specify operator class
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops);
```

---

### Gotcha 5: Wrong Distance Interpretation

```sql
-- Cosine DISTANCE (lower = more similar)
SELECT embedding <=> $1::vector AS distance FROM documents;
-- Returns: 0.1 (similar), 1.5 (different)

-- Cosine SIMILARITY (higher = more similar)
SELECT 1 - (embedding <=> $1::vector) AS similarity FROM documents;
-- Returns: 0.9 (similar), 0.1 (different)
```

**Remember**: Distance and similarity are inverses!

---

## Complete Examples

### Example 1: Medical Document Search System

```sql
-- 1. Create table
CREATE TABLE medical_documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    author_id INTEGER,
    status VARCHAR(50) DEFAULT 'draft',
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create index
CREATE INDEX medical_docs_embedding_idx
ON medical_documents 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 3. Create additional indexes for filters
CREATE INDEX medical_docs_category_idx ON medical_documents(category);
CREATE INDEX medical_docs_status_idx ON medical_documents(status);

-- 4. Insert sample data
INSERT INTO medical_documents (title, content, category, embedding)
VALUES 
    ('Common Cold Symptoms', 'The common cold is a viral infection...', 'respiratory', '[0.12, 0.45, ...]'::vector),
    ('Flu Treatment Guide', 'Influenza treatment includes rest...', 'respiratory', '[0.15, 0.42, ...]'::vector),
    ('Heart Disease Prevention', 'Cardiovascular health requires...', 'cardiology', '[0.89, 0.21, ...]'::vector);

-- 5. Analyze table
ANALYZE medical_documents;

-- 6. Search query
SELECT 
    id,
    title,
    category,
    1 - (embedding <=> $1::vector) AS similarity_score
FROM medical_documents
WHERE status = 'published'
  AND embedding IS NOT NULL
  AND category IN ('respiratory', 'infectious')
ORDER BY embedding <=> $1::vector
LIMIT 10;
```

---

### Example 2: Product Recommendation System

```sql
-- 1. Products table with embeddings
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    price DECIMAL(10, 2),
    embedding vector(1536),
    in_stock BOOLEAN DEFAULT true
);

-- 2. Create index
CREATE INDEX products_embedding_idx
ON products 
USING hnsw (embedding vector_cosine_ops);

-- 3. Find similar products (recommendation query)
WITH target_product AS (
    SELECT embedding FROM products WHERE id = $1
)
SELECT 
    p.id,
    p.name,
    p.category,
    p.price,
    1 - (p.embedding <=> tp.embedding) AS similarity
FROM products p
CROSS JOIN target_product tp
WHERE p.id != $1  -- Exclude the target product itself
  AND p.in_stock = true
  AND p.embedding IS NOT NULL
ORDER BY p.embedding <=> tp.embedding
LIMIT 5;
```

---

### Example 3: Duplicate Detection

```sql
-- Find potential duplicate documents
SELECT 
    d1.id AS doc1_id,
    d1.title AS doc1_title,
    d2.id AS doc2_id,
    d2.title AS doc2_title,
    1 - (d1.embedding <=> d2.embedding) AS similarity,
    CASE 
        WHEN (1 - (d1.embedding <=> d2.embedding)) > 0.98 THEN 'Exact duplicate'
        WHEN (1 - (d1.embedding <=> d2.embedding)) > 0.90 THEN 'Near duplicate'
        ELSE 'Similar'
    END AS match_type
FROM documents d1
JOIN documents d2 ON d1.id < d2.id
WHERE d1.embedding IS NOT NULL
  AND d2.embedding IS NOT NULL
  AND (1 - (d1.embedding <=> d2.embedding)) > 0.85
ORDER BY similarity DESC
LIMIT 100;
```

---

### Example 4: Monitoring Query Performance

```sql
-- Check if index is being used
EXPLAIN ANALYZE
SELECT * FROM documents
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 10;

-- Should see: "Index Scan using documents_embedding_idx"
-- If you see "Seq Scan", index is not being used
```

---

## Quick Reference

### Essential Operators

```sql
<->   -- L2 distance (Euclidean)
<=>   -- Cosine distance (most common for text)
<#>   -- Inner product (fastest, requires normalized vectors)
```

### Essential Functions

```sql
vector_dims(embedding)     -- Get dimensions
vector_norm(embedding)     -- Get magnitude
'[1,2,3]'::vector          -- Cast to vector
```

### Index Creation

```sql
-- IVFFlat (balanced)
CREATE INDEX ON table USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- HNSW (faster)
CREATE INDEX ON table USING hnsw (embedding vector_cosine_ops) WITH (m = 16);
```

### Basic Query Template

```sql
SELECT 
    id,
    title,
    1 - (embedding <=> $1::vector) AS similarity
FROM table
WHERE embedding IS NOT NULL
ORDER BY embedding <=> $1::vector
LIMIT 10;
```

---

## Resources

- **pgvector GitHub**: https://github.com/pgvector/pgvector
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **OpenAI Embeddings**: https://platform.openai.com/docs/guides/embeddings

---

## Summary for SQL Developers

| pgvector Concept | SQL Equivalent |
|------------------|----------------|
| `vector(1536)` | Custom data type (like `JSONB`, `UUID`) |
| `<=>` operator | Distance calculation function |
| `ORDER BY embedding <=>` | `ORDER BY distance ASC` |
| `::vector` | Type casting (like `::INTEGER`, `::DATE`) |
| `ivfflat/hnsw` | Index algorithm (like `btree`, `hash`, `gin`) |
| `vector_cosine_ops` | Operator class (like `text_pattern_ops`) |
| `1 - (embedding <=> query)` | Similarity score (0-1 range) |

**Key Takeaway**: pgvector extends PostgreSQL with vector operations, but follows familiar SQL patterns!


