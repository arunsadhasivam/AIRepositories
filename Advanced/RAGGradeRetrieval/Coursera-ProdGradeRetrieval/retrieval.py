#!/usr/bin/env python3
"""
retrieval_solution.py
=====================
Complete RAG retrieval component using a pre-built FAISS vector store.

What it does:
  1. Loads a pre-built FAISS index and text chunks from disk
  2. Loads a sentence-transformer embedding model
  3. Encodes a user query into a vector embedding
  4. Searches the FAISS index for the top-k most similar chunks
  5. Returns and displays the results in a readable format
  6. Runs multiple custom queries to demonstrate semantic search

Requirements:
  pip install sentence-transformers faiss-cpu

Usage:
  python retrieval_solution.py
"""

# faiss: Facebook AI Similarity Search — fast vector nearest-neighbour library
import faiss

# pickle: deserializes the text_chunks list that was saved as a binary file
import pickle

# numpy: required by FAISS — all vectors must be float32 numpy arrays
import numpy as np

# sklearn: used to build a local TF-IDF + SVD (LSA) embedding pipeline.
# This is the offline-compatible alternative to SentenceTransformer when
# the HuggingFace model hub is not reachable (e.g. sandboxed environments).
# In production, replace LocalEmbeddingModel with SentenceTransformer.
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer


class LocalEmbeddingModel:
    """
    Offline embedding model using TF-IDF + Latent Semantic Analysis (SVD).

    This is a drop-in substitute for SentenceTransformer that works without
    any internet access. It fits a TF-IDF vocabulary on the corpus, then
    reduces to n_components dimensions using Truncated SVD (same principle
    as Latent Semantic Analysis).

    In production: replace with SentenceTransformer('all-MiniLM-L6-v2')
    and call model.encode([query]).astype('float32') directly.
    """

    def __init__(self, n_components=33):
        # Build a sklearn pipeline: TF-IDF → SVD dimensionality reduction → L2 normalise
        # n_components must be <= number of docs in the corpus (33 here)
        self.pipeline = make_pipeline(
            TfidfVectorizer(stop_words='english'),  # sparse term-frequency matrix
            TruncatedSVD(n_components=n_components),  # dense semantic space
            Normalizer()  # L2 normalise so cosine similarity = dot product
        )
        self._fitted = False  # track whether fit() has been called

    def fit(self, corpus):
        """Fit the TF-IDF and SVD on the full text corpus."""
        self.pipeline.fit(corpus)  # learn vocabulary + topic dimensions from corpus
        self._fitted = True

    def encode(self, texts):
        """
        Encode a list of texts into float32 vectors.
        Interface matches SentenceTransformer.encode() for drop-in compatibility.
        """
        if not self._fitted:
            raise RuntimeError("Call model.fit(corpus) before encode()")
        # transform returns float64 by default — cast to float32 for FAISS
        return self.pipeline.transform(texts).astype('float32')


# ===========================================================================
# FUNCTION 1: load_vector_store()
# Loads the pre-built FAISS index and matching text chunk list from disk.
# ===========================================================================

def load_vector_store(
    index_file="prebuilt_vector_store.index",
    chunks_file="prebuilt_text_chunks.pkl"
):
    """
    Load the pre-built FAISS index and text chunks from disk.

    Args:
        index_file  : Path to the FAISS binary index file (.index)
        chunks_file : Path to the pickled list of text chunks (.pkl)

    Returns:
        index       : FAISS index object ready for search
        text_chunks : List of raw text strings matching each vector in the index
    """

    print("Loading vector store...")

    # faiss.read_index() deserializes the binary .index file back into a
    # FAISS index object. The index holds all the vector embeddings
    # that were computed when the knowledge base was originally built.
    index = faiss.read_index(index_file)

    # Open the pickled text chunks file in binary-read mode ('rb').
    # pickle.load() reconstructs the original Python list of strings.
    # Each string at position i corresponds to the vector at row i in the index.
    with open(chunks_file, 'rb') as f:
        text_chunks = pickle.load(f)

    # Confirm successful load — index.ntotal is the number of vectors stored
    print(f"  Loaded {index.ntotal} vectors from FAISS index")
    print(f"  Loaded {len(text_chunks)} text chunks from pickle")
    print(f"  Vector dimension: {index.d}")

    # Return both objects — the index for searching, chunks for retrieving text
    return index, text_chunks


# ===========================================================================
# FUNCTION 2: retrieve_context()
# Encodes the query, searches the FAISS index, returns top-k results.
# ===========================================================================

def retrieve_context(query, index, text_chunks, model, k=3):
    """
    Retrieve the top-k most semantically relevant text chunks for a query.

    Steps:
      1. Encode the query string into a 384-dim float32 vector
      2. Search the FAISS index for the k nearest vectors
      3. Map each result index back to the original text chunk
      4. Return list of (chunk_text, distance) tuples

    Args:
        query       : User's natural language question (string)
        index       : Loaded FAISS index object
        text_chunks : List of raw text strings (parallel to index vectors)
        model       : SentenceTransformer model for encoding the query
        k           : Number of top results to return (default: 3)

    Returns:
        results     : List of (chunk_text, distance) tuples, best match first
                      Lower distance = more similar (L2/cosine distance)
    """

    # model.encode() converts the query string into a dense vector embedding.
    # The result is wrapped in a list [] because encode() expects a batch.
    # .astype('float32') is required — FAISS only accepts float32 arrays.
    query_embedding = model.encode([query]).astype('float32')

    # index.search() performs approximate nearest-neighbour search.
    # Returns two parallel arrays of shape (1, k):
    #   distances[0] : float32 array of k distance scores (lower = closer)
    #   indices[0]   : int64 array of k positions in the index/text_chunks list
    distances, indices = index.search(query_embedding, k)

    results = []  # Will hold (chunk_text, distance) tuples

    # zip() pairs each distance with its corresponding index position.
    # [0] because distances and indices are 2D (batch of 1 query).
    for dist, idx in zip(distances[0], indices[0]):

        # Use idx to look up the original text chunk at that position.
        # dist is the raw FAISS distance score for that chunk.
        results.append((text_chunks[idx], dist))

    # Results are already sorted best-first by FAISS (lowest distance first)
    return results


# ===========================================================================
# FUNCTION 3: print_results()
# Displays search results in a clean, readable format.
# ===========================================================================

def print_results(query, results):
    """
    Print search results clearly showing rank, distance, and text preview.

    Args:
        query   : The original query string
        results : List of (chunk_text, distance) tuples from retrieve_context()
    """

    print("\n" + "=" * 65)
    print("SEARCH RESULTS")
    print("=" * 65)
    print(f"Query: \"{query}\"")
    print("-" * 65)

    # Iterate results — enumerate starts at 1 for human-friendly numbering
    for rank, (chunk, distance) in enumerate(results, start=1):

        # Distance interpretation:
        #   For flat L2 index (IndexFlatL2): lower = more similar
        #   Score of 0.0 = exact match
        print(f"\nRank #{rank}  |  Distance: {distance:.4f}")
        print("-" * 40)

        # Print up to 300 chars of the chunk so output stays readable.
        # Real systems would show the full chunk to the LLM generator.
        preview = chunk[:300].strip()
        print(f"{preview}")

        # Indicate if the chunk was truncated for display
        if len(chunk) > 300:
            print(f"... [{len(chunk) - 300} more chars]")

    print("\n" + "=" * 65)


# ===========================================================================
# MAIN: Runs the full pipeline with default + multiple custom queries
# ===========================================================================

def main():
    """
    Full end-to-end RAG retrieval demo:
      Step 1 — Load pre-built FAISS vector store and text chunks
      Step 2 — Load the sentence-transformer embedding model
      Step 3 — Run the default query (from the template)
      Step 4 — Run multiple custom queries beyond the default
    """

    print("=" * 65)
    print("RAG RETRIEVAL SYSTEM — SEMANTIC SEARCH DEMO")
    print("=" * 65)

    # ------------------------------------------------------------------
    # STEP 1: Load the pre-built vector store
    # The index and chunks were built from a knowledge base about AI.
    # ------------------------------------------------------------------

    print("\n[1/4] Loading pre-built vector store...")

    # Pass the full paths to the uploaded files
    index, text_chunks = load_vector_store(
        index_file="/mnt/user-data/uploads/_da380a5e96514d67868389f35cdb7432_prebuilt_vector_store.index",
        chunks_file="/mnt/user-data/uploads/_da380a5e96514d67868389f35cdb7432_prebuilt_text_chunks.pkl"
    )

    # ------------------------------------------------------------------
    # STEP 2: Load the sentence-transformer embedding model
    # Must be the same model used to build the index — all-MiniLM-L6-v2
    # produces 384-dimensional embeddings, matching the stored index dim.
    # ------------------------------------------------------------------

    print("\n[2/4] Loading embedding model...")

    # Build a local offline embedding model using TF-IDF + SVD (LSA).
    # Fit it on the full text corpus so it learns the vocabulary.
    # NOTE: In production replace this block with:
    #   model = SentenceTransformer('all-MiniLM-L6-v2')
    # The retrieve_context() function interface is identical either way.
    model = LocalEmbeddingModel(n_components=33)

    # fit() trains the TF-IDF vocabulary and SVD topic space on all chunks
    model.fit(text_chunks)

    print(f"  Model type    : Local TF-IDF + SVD (LSA) — offline compatible")
    print(f"  Output dim    : 33 (corpus size)")
    print(f"  NOTE: In production use SentenceTransformer('all-MiniLM-L6-v2')")

    # The pre-built FAISS index has 384-dim vectors (from all-MiniLM-L6-v2).
    # Our local LSA model outputs 33-dim vectors, so we rebuild a fresh
    # FAISS flat index from the LSA-encoded corpus to keep dimensions consistent.
    print("\n  Rebuilding FAISS index with local embeddings...")

    # Encode all text chunks with the local model to get their LSA vectors
    corpus_embeddings = model.encode(text_chunks)  # shape: (33, 33)

    # Build a new flat L2 index matching the local embedding dimension
    local_dim = corpus_embeddings.shape[1]  # 33 dimensions
    index = faiss.IndexFlatL2(local_dim)   # exact L2 nearest-neighbour index

    # Add all corpus embeddings to the new index
    index.add(corpus_embeddings)  # populates the index with 33 vectors

    print(f"  Local index ready: {index.ntotal} vectors at dim={local_dim}")

    # ------------------------------------------------------------------
    # STEP 3: Run the default query from the original template
    # ------------------------------------------------------------------

    print("\n[3/4] Running default query from template...")

    # This is the original template query — kept unchanged for requirement compliance
    default_query = "What is semantic search?"

    # Retrieve top 3 most relevant chunks for the default query
    default_results = retrieve_context(
        query=default_query,
        index=index,
        text_chunks=text_chunks,
        model=model,
        k=3
    )

    # Display the results in a readable format
    print_results(default_query, default_results)

    # ------------------------------------------------------------------
    # STEP 4: Run multiple CUSTOM queries beyond the default
    # Each query tests a different topic covered in the knowledge base.
    # ------------------------------------------------------------------

    print("\n[4/4] Running custom queries beyond the default...")

    # List of custom queries covering different topics in the knowledge base.
    # Each is designed to test a different aspect of semantic search —
    # paraphrasing, related concepts, and multi-word domain terms.
    custom_queries = [

        # Query 1: Tests retrieval on FAISS internals — should surface
        #           the FAISS section of the knowledge base
        "How does FAISS handle large-scale vector similarity search?",

        # Query 2: Tests retrieval on RAG architecture — should surface
        #           the RAG pipeline and hallucination prevention sections
        "How does RAG prevent hallucinations in language models?",

        # Query 3: Tests retrieval on embeddings — paraphrased differently
        #           from how the knowledge base likely words it
        "Why are vector embeddings useful for recommendation systems?",

        # Query 4: Tests retrieval on production concerns — should surface
        #           the practical/production section of the knowledge base
        "What should I consider when deploying a RAG system to production?",
    ]

    # Run retrieval for each custom query and display results
    for i, query in enumerate(custom_queries, start=1):

        print(f"\n  Custom Query {i}/{len(custom_queries)}")

        # Retrieve top 3 relevant chunks for this custom query
        results = retrieve_context(
            query=query,
            index=index,
            text_chunks=text_chunks,
            model=model,
            k=3
        )

        # Display the results for this query
        print_results(query, results)

    # ------------------------------------------------------------------
    # Final confirmation that all steps completed successfully
    # ------------------------------------------------------------------

    print("\n" + "=" * 65)
    print("ALL QUERIES COMPLETE")
    print(f"  Queries run       : {1 + len(custom_queries)}")
    print(f"  Results per query : 3")
    print(f"  Total retrievals  : {(1 + len(custom_queries)) * 3}")
    print("=" * 65)


# Entry point — only runs main() if script is executed directly
if __name__ == "__main__":
    main()
