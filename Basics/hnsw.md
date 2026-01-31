




# HNSW (Hierarchical Navigable Small World) - Complete Guide

## Table of Contents
1. [What is HNSW?](#what-is-hnsw)
2. [The Problem It Solves](#the-problem-it-solves)
3. [Core Concepts](#core-concepts)
4. [How HNSW Works](#how-hnsw-works)
5. [Layer Assignment](#layer-assignment)
6. [Search Algorithm](#search-algorithm)
7. [Insert Algorithm](#insert-algorithm)
8. [Configuration Parameters](#configuration-parameters)
9. [Performance Characteristics](#performance-characteristics)
10. [PostgreSQL Implementation](#postgresql-implementation)
11. [Real-World Examples](#real-world-examples)
12. [Comparisons](#comparisons)
13. [Best Practices](#best-practices)

---

## What is HNSW?

**HNSW** = Hierarchical Navigable Small World

A graph-based algorithm for **Approximate Nearest Neighbor (ANN)** search in high-dimensional vector spaces.

### Purpose
Find similar vectors **extremely fast** with near-perfect accuracy (95-99%).

### Use Cases
- Image similarity search
- Product recommendations
- Semantic text search
- Face recognition
- Document similarity
- Audio fingerprinting

---

## The Problem It Solves

### Scenario
You have 10 million product embeddings (768 dimensions each). A user searches, and you need to find the 10 most similar products in under 100ms.

### Naive Approach (Linear Scan)
```java
// Check EVERY vector
for (int i = 0; i < 10_000_000; i++) {
    double distance = calculateDistance(queryVector, vectors[i]);
    // Keep top 10
}
// Time: 5000ms ❌ Too slow!
```

### HNSW Approach
```java
// Navigate through hierarchical graph
// Check only ~1000-2000 vectors
result = hnsw.search(queryVector, k=10);
// Time: 50ms ✅ Fast!
```

**Result**: 100x faster with 98% accuracy

---

## Core Concepts

### 1. Multi-Layer Graph Structure

HNSW builds a graph with multiple layers:

```
Layer 3 (Top):      V1 ←----------→ V9           (Fewest vectors, longest jumps)
                    ↓              ↓
                    
Layer 2:            V1 ←→ V4 ←→ V7 ←→ V9         (Few vectors, long jumps)
                    ↓    ↓    ↓    ↓
                    
Layer 1:            V1 ←→ V2 ←→ V4 ←→ V5 ←→ V7 ←→ V8 ←→ V9  (More vectors, medium jumps)
                    ↓    ↓    ↓    ↓    ↓    ↓    ↓
                    
Layer 0 (Bottom):   V1-V2-V3-V4-V5-V6-V7-V8-V9-V10  (ALL vectors, short jumps)
```

**Key Properties**:
- **Layer 0**: Contains ALL vectors
- **Higher Layers**: Contain progressively fewer vectors
- **Same vector** can appear in multiple layers
- **Connections**: Based on distance/similarity

### 2. Hierarchical Navigation

Like Google Maps:
- **Layer 3**: Interstate highways (big jumps, few cities)
- **Layer 2**: State highways (medium jumps, more cities)
- **Layer 1**: Local roads (small jumps, many locations)
- **Layer 0**: All streets (precise navigation)

### 3. Small World Property

Any two vectors are reachable in O(log n) hops, even with millions of vectors.

---

## How HNSW Works

### Building the Index

#### Step 1: Layer Assignment (Random)

Each vector is randomly assigned to layers using exponential distribution:

```java
// Assign layer for new vector
double random = Math.random();  // 0.0 to 1.0
double mL = 1.0 / Math.log(2.0);  // Normalization constant ≈ 1.44
int layer = (int) Math.floor(-Math.log(random) * mL);

// Example:
// random = 0.23 → layer = 2 (vector appears in layers 0, 1, 2)
// random = 0.67 → layer = 0 (vector appears in layer 0 only)
// random = 0.10 → layer = 3 (vector appears in layers 0, 1, 2, 3)
```

#### Probability Distribution

| Layer | Probability | Out of 1M vectors |
|-------|-------------|-------------------|
| 0 | 100% | 1,000,000 |
| 1 | 50% | ~500,000 |
| 2 | 25% | ~250,000 |
| 3 | 12.5% | ~125,000 |
| 4 | 6.25% | ~62,500 |
| 10 | 0.098% | ~977 |
| 20 | 0.000095% | ~1 |

**Pattern**: Each layer has ~50% of the vectors from the layer below.

#### Step 2: Connect to Neighbors

For each layer the vector belongs to:

```java
// Find M nearest neighbors in this layer
List<Vector> neighbors = findNearestVectors(newVector, M, currentLayer);

// Create bidirectional connections
for (Vector neighbor : neighbors) {
    newVector.addNeighbor(neighbor, currentLayer);
    neighbor.addNeighbor(newVector, currentLayer);
    
    // If neighbor exceeds max connections, prune farthest
    if (neighbor.getNeighborCount(currentLayer) > maxNeighbors) {
        neighbor.pruneFarthestNeighbor(currentLayer);
    }
}
```

---

## Layer Assignment

### How Many Layers?

**Rule**: max_layers ≈ log₂(total_vectors)

| Dataset Size | Expected Max Layer |
|--------------|-------------------|
| 1,000 vectors | ~10 |
| 10,000 vectors | ~13 |
| 100,000 vectors | ~17 |
| 1,000,000 vectors | ~20 |
| 10,000,000 vectors | ~23 |

### Example: Inserting 10 Products

```
Product assignments (based on random probability):

P1 (Laptop):   random=0.23 → layer 2  (exists in 0,1,2)
P2 (Mouse):    random=0.67 → layer 0  (exists in 0 only)
P3 (Book):     random=0.45 → layer 1  (exists in 0,1)
P4 (Keyboard): random=0.89 → layer 0  (exists in 0 only)
P5 (Monitor):  random=0.40 → layer 1  (exists in 0,1)
P6 (Pen):      random=0.75 → layer 0  (exists in 0 only)
P7 (Desk):     random=0.18 → layer 2  (exists in 0,1,2)
P8 (Chair):    random=0.92 → layer 0  (exists in 0 only)
P9 (Phone):    random=0.50 → layer 1  (exists in 0,1)
P10 (Tablet):  random=0.81 → layer 0  (exists in 0 only)

Final Structure:

Layer 2:  P1 ←------------------→ P7
          ↓                       ↓
          
Layer 1:  P1 ←→ P3 ←→ P5 ←→ P7 ←→ P9
          ↓    ↓    ↓    ↓    ↓
          
Layer 0:  P1-P2-P3-P4-P5-P6-P7-P8-P9-P10
```

**Important**: Layer assignment is RANDOM, not based on vector similarity!

---

## Search Algorithm

### Goal
Find k nearest neighbors to query vector Q.

### Process

```
Given: Query vector Q, k=10 (find 10 nearest neighbors)

Step 1: Enter at Top Layer
├─ Start at entry point (random vector in highest layer)
├─ Current layer: 2
└─ Current position: V1

Step 2: Greedy Search in Current Layer
├─ Check V1's neighbors in layer 2: [V7]
├─ Calculate: distance(Q, V1) vs distance(Q, V7)
├─ Move to closer neighbor
└─ Repeat until no closer neighbor found

Step 3: Descend to Next Layer
├─ Go down to layer 1
├─ Starting from best position found in layer 2
└─ Repeat greedy search

Step 4: Continue Until Layer 0
├─ Descend through all layers
├─ At layer 0, collect k nearest neighbors
└─ Return results
```

### Detailed Example

```
Query: Find products similar to "Wireless Keyboard"

Layer 2: Start at P1 (Laptop)
├─ distance(keyboard, P1) = 0.12
├─ Check neighbor P7 (Desk): distance = 0.45
├─ P1 is closer, stay at P1
└─ Descend to layer 1

Layer 1: Start at P1
├─ Check neighbors: [P3, P5, P7, P9]
├─ distance(keyboard, P3) = 0.85 (Book - very different)
├─ distance(keyboard, P5) = 0.15 (Monitor - somewhat similar)
├─ distance(keyboard, P7) = 0.45 (Desk - different)
├─ distance(keyboard, P9) = 0.30 (Phone - different)
├─ P1 (0.12) still closest
└─ Descend to layer 0

Layer 0: Start at P1
├─ Check all neighbors: [P2, P4, others...]
├─ distance(keyboard, P2) = 0.08 (Mouse - very similar!)
├─ distance(keyboard, P4) = 0.03 (Keyboard - exact match!)
├─ Found top 10 nearest: [P4, P2, P1, P5, ...]
└─ Return results

Result: [P4 (Keyboard), P2 (Mouse), P1 (Laptop), ...]
Time: 15ms (checked ~50 vectors instead of all 10)
```

---

## Insert Algorithm

### Process for Adding New Vector

```java
// Insert new vector into HNSW index
public void insert(float[] newVector) {
    // Step 1: Assign layer (random)
    int targetLayer = assignRandomLayer();
    
    // Step 2: Search from top to find insertion point
    Vector currentNearest = entryPoint;
    
    for (int layer = topLayer; layer >= 0; layer--) {
        // Greedy search in this layer
        currentNearest = searchLayer(newVector, currentNearest, layer, 1);
        
        // If this is a layer where new vector belongs
        if (layer <= targetLayer) {
            // Find M nearest neighbors
            List<Vector> neighbors = searchLayer(newVector, currentNearest, layer, M);
            
            // Connect bidirectionally
            for (Vector neighbor : neighbors) {
                addConnection(newVector, neighbor, layer);
                addConnection(neighbor, newVector, layer);
                
                // Prune if needed
                if (neighbor.getDegree(layer) > maxM) {
                    pruneConnections(neighbor, layer);
                }
            }
        }
    }
    
    // Step 3: Update entry point if needed
    if (targetLayer > topLayer) {
        entryPoint = newVector;
        topLayer = targetLayer;
    }
}
```

### Insert Performance

| Dataset Size | Insert Time (with index) | Insert Time (without index) |
|--------------|-------------------------|----------------------------|
| 1K vectors | ~2ms | ~0.1ms |
| 100K vectors | ~5ms | ~0.1ms |
| 1M vectors | ~15ms | ~0.1ms |
| 10M vectors | ~50ms | ~0.1ms |

**Trade-off**: Slower inserts for much faster searches.

---

## Configuration Parameters

### 1. M (Connections per Layer)

**Definition**: Number of bidirectional connections each vector maintains per layer.

```sql
CREATE INDEX idx_embedding 
ON products 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16);  -- Default is 16
```

**Impact**:

| M Value | Memory | Build Time | Search Speed | Recall |
|---------|--------|------------|--------------|--------|
| 4 | Low | Fast | Slower | 90-95% |
| 8 | Medium-Low | Medium-Fast | Medium | 93-97% |
| 16 | Medium | Medium | Fast | 96-99% |
| 32 | High | Slow | Very Fast | 98-99.5% |
| 64 | Very High | Very Slow | Very Fast | 99%+ |

**Recommendation**:
- **Small datasets (<100K)**: m=8
- **Medium datasets (100K-1M)**: m=16 (default)
- **Large datasets (>1M)**: m=32
- **Critical accuracy needs**: m=64

### 2. ef_construction (Build Quality)

**Definition**: Size of the dynamic candidate list during index construction.

```sql
CREATE INDEX idx_embedding 
ON products 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);  -- Default is 64
```

**Impact**:

| ef_construction | Build Time | Index Quality | Search Recall |
|-----------------|------------|---------------|---------------|
| 40 | Fast | Lower | 93-96% |
| 64 | Medium | Medium | 96-98% |
| 100 | Medium-Slow | Good | 97-99% |
| 200 | Slow | High | 98-99.5% |
| 400 | Very Slow | Very High | 99%+ |

**Recommendation**:
- **Frequent rebuilds**: ef_construction=40-64
- **Static data**: ef_construction=200-400
- **Default**: ef_construction=64

### 3. ef_search (Query Time Exploration)

**Definition**: Size of the dynamic candidate list during search (not in CREATE INDEX).

**Note**: In PostgreSQL, set this at query time, not index creation.

```sql
-- Set for session
SET hnsw.ef_search = 100;

-- Or per query (not all implementations support this)
SELECT * FROM products 
ORDER BY embedding <-> query_vector 
LIMIT 10;
```

**Impact**:

| ef_search | Search Time | Recall |
|-----------|-------------|--------|
| 10 | Very Fast | 85-90% |
| 40 | Fast | 93-96% |
| 100 | Medium | 97-99% |
| 200 | Slow | 98-99.5% |
| 400 | Very Slow | 99%+ |

**Recommendation**:
- **Real-time search (<50ms)**: ef_search=40-100
- **High accuracy needs**: ef_search=200-400
- **Default**: ef_search=40

---

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Insert | O(log n) | Amortized |
| Search | O(log n) | Expected |
| Delete | O(log n) | If supported |
| Build | O(n log n) | Initial construction |

### Memory Usage

```
Memory per vector ≈ (dimensions × 4 bytes) + (M × 8 bytes × avg_layers)

Example for 1M vectors (768 dimensions, M=16):
- Vector data: 1M × 768 × 4 = 3.072 GB
- Graph structure: 1M × 16 × 8 × 1.1 = 0.141 GB
- Total: ~3.2 GB
```

### Search Performance Comparison

| Dataset Size | Linear Scan | HNSW (m=16) | Speedup |
|--------------|-------------|-------------|---------|
| 1K vectors | 5ms | 0.5ms | 10x |
| 10K vectors | 50ms | 1ms | 50x |
| 100K vectors | 500ms | 3ms | 167x |
| 1M vectors | 5000ms | 10ms | 500x |
| 10M vectors | 50000ms | 30ms | 1667x |

**Accuracy**: 96-99% recall (finds true nearest neighbors)

---

## PostgreSQL Implementation

### Installation

```sql
-- pgvector extension includes HNSW support
CREATE EXTENSION vector;
```

### Creating HNSW Index

```sql
-- Create table with vector column
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT,
    description TEXT,
    embedding vector(768)  -- 768-dimensional vector
);

-- Create HNSW index
CREATE INDEX idx_product_embedding 
ON products 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### Distance Operators

```sql
-- Cosine distance (most common for embeddings)
CREATE INDEX ON products USING hnsw (embedding vector_cosine_ops);

-- L2 (Euclidean) distance
CREATE INDEX ON products USING hnsw (embedding vector_l2_ops);

-- Inner product
CREATE INDEX ON products USING hnsw (embedding vector_ip_ops);
```

### Querying

```sql
-- Find 10 most similar products
SELECT 
    id, 
    name,
    embedding <-> '[0.1, 0.2, 0.3, ..., 0.768]' AS distance
FROM products
ORDER BY embedding <-> '[0.1, 0.2, 0.3, ..., 0.768]'
LIMIT 10;

-- With distance threshold
SELECT 
    id, 
    name,
    embedding <-> query_vector AS distance
FROM products
WHERE embedding <-> query_vector < 0.5  -- Only within distance 0.5
ORDER BY distance
LIMIT 10;
```

### Checking Index Usage

```sql
-- Verify index is being used
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM products 
ORDER BY embedding <-> '[0.1, 0.2, ...]' 
LIMIT 10;

-- Expected output:
-- Index Scan using idx_product_embedding on products
```

### Index Management

```sql
-- Check index size
SELECT pg_size_pretty(pg_relation_size('idx_product_embedding'));

-- Rebuild index
REINDEX INDEX idx_product_embedding;

-- Drop index
DROP INDEX idx_product_embedding;

-- Create index without blocking writes (PostgreSQL 12+)
CREATE INDEX CONCURRENTLY idx_product_embedding 
ON products 
USING hnsw (embedding vector_cosine_ops);
```

---

## Real-World Examples

### 1. E-commerce Product Search

```sql
-- Setup
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT,
    category TEXT,
    price DECIMAL,
    image_embedding vector(512)  -- ResNet-50 embeddings
);

-- Create HNSW index
CREATE INDEX idx_image_search 
ON products 
USING hnsw (image_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 100);

-- Search: Find similar products by image
-- User uploads image, convert to embedding, then query
SELECT 
    id,
    name,
    price,
    image_embedding <-> user_image_embedding AS similarity
FROM products
WHERE category = 'shoes'  -- Optional filter
ORDER BY image_embedding <-> user_image_embedding
LIMIT 20;

-- Performance: 15ms for 5M products
```

### 2. Semantic Document Search

```sql
-- Setup
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title TEXT,
    content TEXT,
    text_embedding vector(768)  -- BERT embeddings
);

-- Create HNSW index
CREATE INDEX idx_semantic_search 
ON documents 
USING hnsw (text_embedding vector_cosine_ops)
WITH (m = 32, ef_construction = 200);

-- Search: Find relevant documents
SELECT 
    id,
    title,
    text_embedding <-> query_embedding AS relevance
FROM documents
ORDER BY text_embedding <-> query_embedding
LIMIT 10;

-- Performance: 25ms for 10M documents
```

### 3. Recommendation System

```sql
-- Setup
CREATE TABLE user_profiles (
    user_id INTEGER PRIMARY KEY,
    preference_embedding vector(256)
);

CREATE TABLE items (
    item_id INTEGER PRIMARY KEY,
    name TEXT,
    item_embedding vector(256)
);

-- Create HNSW index
CREATE INDEX idx_recommendations 
ON items 
USING hnsw (item_embedding vector_cosine_ops);

-- Get recommendations for user
SELECT 
    i.item_id,
    i.name,
    i.item_embedding <-> u.preference_embedding AS match_score
FROM items i, user_profiles u
WHERE u.user_id = 12345
ORDER BY i.item_embedding <-> u.preference_embedding
LIMIT 50;
```

---

## Comparisons

### HNSW vs Other Index Types

#### HNSW vs IVFFlat (Another Vector Index)

| Aspect | HNSW | IVFFlat |
|--------|------|---------|
| **Search Speed** | Very Fast (5-20ms) | Fast (20-50ms) |
| **Insert Speed** | Slow (5-20ms) | Fast (1-5ms) |
| **Memory** | High | Medium |
| **Accuracy** | Very High (98-99%) | High (95-97%) |
| **Best For** | Read-heavy workloads | Balanced read/write |
| **Complexity** | O(log n) | O(√n) |

**When to use**:
- **HNSW**: E-commerce search, static datasets, high accuracy needs
- **IVFFlat**: Real-time recommendations, frequent updates, lower memory

#### HNSW vs B-tree

| Aspect | HNSW | B-tree |
|--------|------|--------|
| **Data Type** | Multi-dimensional vectors | Scalar values |
| **Comparison** | Distance/similarity | Exact value |
| **Result** | Approximate (top-k) | Exact match |
| **Use Case** | Similarity search | Exact lookup, range queries |
| **Example** | "Find similar images" | "Find user_id = 123" |

#### HNSW vs HashMap

| Aspect | HNSW | HashMap |
|--------|------|---------|
| **Structure** | Graph with layers | Buckets (array) |
| **Lookup** | O(log n) | O(1) |
| **Assignment** | Distance-based connections | Hash function |
| **Purpose** | Find nearest neighbors | Find exact key |
| **Similarity** | Preserves similarity | Ignores similarity |

---

### HNSW vs Global Catalog (Active Directory)

| Aspect | HNSW | Global Catalog |
|--------|------|----------------|
| **Hierarchy** | Multiple layers of same vectors | GC (partial) + DC (complete) |
| **Data at top** | Same vectors, fewer of them | Subset of attributes |
| **Data at bottom** | All vectors, complete data | Complete objects |
| **Selection** | Random probability | Frequently searched objects |
| **Purpose** | Fast similarity search | Fast cross-domain lookup |
| **Physical/Logical** | Logical layers | Physical servers |

**Similarity**: Both use hierarchy to avoid checking everything.
**Difference**: GC has partial data at top, HNSW has same data with fewer vectors.

---

## Best Practices

### 1. Index Creation Strategy

```sql
-- For bulk loading: Create index AFTER inserting data
CREATE TABLE products (id SERIAL, embedding vector(768));

-- Insert all data first (fast, no index overhead)
INSERT INTO products (embedding) 
SELECT embedding FROM staging_table;

-- Then create index (one-time cost)
CREATE INDEX idx_embedding 
ON products 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 100);
```

### 2. Workload-Specific Configuration

```sql
-- Read-heavy (e-commerce search)
CREATE INDEX USING hnsw (embedding vector_cosine_ops)
WITH (m = 32, ef_construction = 200);

-- Balanced (real-time recommendations)
CREATE INDEX USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Write-heavy (frequent updates)
-- Consider IVFFlat instead
CREATE INDEX USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 1000);
```

### 3. Monitoring Performance

```sql
-- Check if index is being used
EXPLAIN ANALYZE
SELECT * FROM products 
ORDER BY embedding <-> query_vector 
LIMIT 10;

-- Monitor index size
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
FROM pg_indexes
WHERE tablename = 'products';

-- Check index usage statistics
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,  -- Number of times index used
    idx_tup_read  -- Tuples read via index
FROM pg_stat_user_indexes
WHERE indexname = 'idx_embedding';
```

### 4. Dealing with Updates

```sql
-- Option 1: Batch updates during off-peak hours
-- 2 AM maintenance window
DROP INDEX idx_embedding;
UPDATE products SET embedding = new_embeddings;
CREATE INDEX idx_embedding USING hnsw (embedding);

-- Option 2: Use staging table for new data
CREATE TABLE products_staging (embedding vector(768));
INSERT INTO products_staging SELECT ...;  -- Fast

-- Periodic merge
INSERT INTO products SELECT * FROM products_staging;
TRUNCATE products_staging;
REINDEX INDEX idx_embedding;

-- Option 3: Accept slower inserts, keep index active
-- Direct inserts with index (slower but no downtime)
INSERT INTO products (embedding) VALUES (...);
```

### 5. Memory Management

```sql
-- Estimate memory needs before creating index
-- Formula: vectors × (dimensions × 4 + M × 8 × 1.1)

-- For 1M vectors, 768 dims, M=16:
-- Memory ≈ 1M × (768×4 + 16×8×1.1) ≈ 3.2 GB

-- Allocate sufficient work memory
SET maintenance_work_mem = '4GB';

-- Create index
CREATE INDEX idx_embedding 
ON products 
USING hnsw (embedding vector_cosine_ops);
```

### 6. Query Optimization

```sql
-- Good: Use index for similarity search
SELECT * FROM products
ORDER BY embedding <-> query_vector
LIMIT 10;

-- Bad: Filtering before similarity search (might not use index)
SELECT * FROM products
WHERE category = 'electronics'
ORDER BY embedding <-> query_vector
LIMIT 10;

-- Better: Filter after similarity search
SELECT * FROM (
    SELECT * FROM products
    ORDER BY embedding <-> query_vector
    LIMIT 100  -- Get more candidates
) candidates
WHERE category = 'electronics'
LIMIT 10;
```

### 7. Testing and Validation

```sql
-- Test recall: Compare HNSW results with exact search
-- Ground truth (exact, slow)
SELECT id FROM products
ORDER BY embedding <-> query_vector
LIMIT 10;

-- HNSW results (fast)
SELECT id FROM products
ORDER BY embedding <-> query_vector
LIMIT 10;

-- Calculate recall: % of ground truth IDs found in HNSW results
-- Target: 95-99% recall
```

---

## Common Issues and Solutions

### Issue 1: Slow Inserts

**Problem**: Inserting with HNSW index is very slow.

**Solutions**:
```sql
-- Solution A: Defer index creation
DROP INDEX idx_embedding;
INSERT INTO products ...; -- Fast
CREATE INDEX idx_embedding ...;  -- One-time cost

-- Solution B: Use IVFFlat for write-heavy workloads
CREATE INDEX USING ivfflat (embedding vector_cosine_ops);

-- Solution C: Batch inserts
BEGIN;
INSERT INTO products VALUES (...), (...), ...;  -- 1000 rows
COMMIT;
```

### Issue 2: Index Not Being Used

**Problem**: Query does sequential scan instead of using HNSW index.

**Check**:
```sql
EXPLAIN SELECT * FROM products
ORDER BY embedding <-> query_vector
LIMIT 10;

-- If shows "Seq Scan" instead of "Index Scan"
```

**Solutions**:
```sql
-- Ensure operator matches index type
-- Wrong: <=> (this might not use HNSW)
-- Correct: <-> for cosine distance

-- Update statistics
ANALYZE products;

-- Increase work_mem if needed
SET work_mem = '256MB';
```

### Issue 3: Poor Recall

**Problem**: HNSW not finding true nearest neighbors.

**Solutions**:
```sql
-- Increase m (more connections)
DROP INDEX idx_embedding;
CREATE INDEX USING hnsw (embedding)
WITH (m = 32);  -- Was 16

-- Increase ef_construction (better quality)
CREATE INDEX USING hnsw (embedding)
WITH (ef_construction = 200);  -- Was 64

-- Increase ef_search at query time
SET hnsw.ef_search = 200;  -- If supported
```

---

## Summary

### Key Takeaways

1. **HNSW is a graph-based index** for fast similarity search in vector spaces
2. **Uses hierarchical layers** to enable O(log n) search complexity
3. **Layer assignment is random** (not based on vector values)
4. **Connections are distance-based** (similar vectors connect)
5. **Trade-off**: Slower writes for 100-1000x faster reads
6. **Configurable**: Tune M and ef_construction for your workload
7. **High accuracy**: 95-99% recall with proper configuration

### When to Use HNSW

✅ **Use HNSW when**:
- Need very fast similarity search (<50ms)
- Read-heavy workload (90%+ reads)
- High accuracy requirements (>95% recall)
- Static or infrequently updated data
- Have sufficient memory

❌ **Don't use HNSW when**:
- Exact match queries (use B-tree)
- Write-heavy workload (consider IVFFlat)
- Very limited memory
- Small datasets (<1000 vectors, linear scan is fine)

### Quick Reference

```sql
-- Create HNSW index (standard config)
CREATE INDEX idx_embedding 
ON table_name 
USING hnsw (embedding_column vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Query with HNSW
SELECT * FROM table_name
ORDER BY embedding_column <-> query_vector
LIMIT k;

-- Check performance
EXPLAIN ANALYZE
SELECT * FROM table_name
ORDER BY embedding_column <-> query_vector
LIMIT k;
```

---

## References

- [Original HNSW Paper](https://arxiv.org/abs/1603.09320)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Last Updated**: January 2026






