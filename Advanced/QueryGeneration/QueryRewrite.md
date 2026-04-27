# Query Rewriting - Post Retrieval

## What is it?
After initial retrieval, the retrieved chunks are used to **rewrite the original query**
into a better, more focused query — then retrieve again with the improved query.

## Why use it?
- First retrieval may return **partially relevant** chunks
- Rewritten query using retrieved context produces **more precise** second retrieval
- Iteratively improves retrieval quality

## When to use it?
- First pass retrieval returns **noisy or incomplete** results
- User query is **ambiguous** and needs context to clarify
- High accuracy retrieval needed — medical, legal, clinical domains

## Flow
```
User Query
    → First Retrieval (Vector DB)
    → Retrieved Chunks
    → LLM rewrites query using chunks as context
    → Second Retrieval (Vector DB) with rewritten query
    → Final LLM Answer
```

## Advantage
- Second retrieval is much more **targeted and precise**
- Retrieved chunks guide the rewrite — less hallucination risk
- Works well for **complex multi-part questions**

## Disadvantage
- **2 vector DB searches** — higher latency
- **2 LLM calls** — rewriter + final answer
- Overkill for simple specific queries

---

## Code

```python
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores.pgvector import PGVector
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Initialize Ollama LLM - Mistral running locally
llm = Ollama(model="mistral")

# Initialize Ollama embeddings
embeddings = OllamaEmbeddings(model="mistral")

# Connect to existing pgvector store - documents already indexed
vectorstore = PGVector(
    collection_name="clinical_documents",           # collection to search in
    connection_string="postgresql+psycopg2://user:password@localhost:5432/ragdb",
    embedding_function=embeddings                   # embedding model to use
)

# Create base retriever - fetches top 3 similar documents
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# Helper to join all retrieved docs into single string
def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])  # join docs with separator

# ============================================================
# STEP 1 - First Retrieval with original user query
# ============================================================

# Original user query - may be vague or ambiguous
user_query = "What are the risks for diabetic patients?"

# First retrieval - searches vector DB with original query
# may return partially relevant chunks
first_docs = retriever.get_relevant_documents(user_query)

# Format first retrieved docs into single string
first_context = format_docs(first_docs)

print("=== First Retrieved Context ===")
print(first_context)

# ============================================================
# STEP 2 - Query Rewriting using first retrieved chunks
# ============================================================

# Define query rewriter prompt
# uses first retrieved chunks as context to rewrite original query
rewriter_prompt_template = """
You are a query rewriting expert.
Given the original user question and some retrieved context below,
rewrite the question into a more specific and focused search query
that will retrieve better results from the vector store.
Return only the rewritten query, nothing else.

Original question: {question}
Retrieved context: {context}
Rewritten query:
"""

# Create rewriter prompt object
rewriter_prompt = ChatPromptTemplate.from_template(rewriter_prompt_template)

# Build query rewriter chain
# original query + first context -> rewriter prompt -> LLM -> rewritten query string
rewriter_chain = (
    rewriter_prompt      # fill original query and first context into prompt
    | llm                # LLM rewrites query using retrieved context as guide
    | StrOutputParser()  # extract plain rewritten query string
)

# Generate rewritten query using first retrieved context
# LLM now has context to make query more specific
rewritten_query = rewriter_chain.invoke({
    "question": user_query,      # original vague user query
    "context": first_context     # first retrieved chunks as context guide
})

print("\n=== Rewritten Query ===")
print(rewritten_query)

# ============================================================
# STEP 3 - Second Retrieval with rewritten query
# ============================================================

# Second retrieval - now uses focused rewritten query
# produces more targeted and precise results
second_docs = retriever.get_relevant_documents(rewritten_query)

# Format second retrieved docs into single string
second_context = format_docs(second_docs)

print("\n=== Second Retrieved Context ===")
print(second_context)

# ============================================================
# STEP 4 - Final Answer using second retrieval results
# ============================================================

# Define final RAG answer prompt
final_prompt_template = """
Use the following context to answer the question.
If you don't know, say you don't know.

Context: {context}
Question: {question}
Answer:
"""

# Create final answer prompt object
final_prompt = ChatPromptTemplate.from_template(final_prompt_template)

# Build final answer chain
# second context + original query -> prompt -> LLM -> final answer string
final_chain = (
    final_prompt         # inject second retrieval context and original query
    | llm                # LLM generates final answer using precise context
    | StrOutputParser()  # extract plain string answer
)

# Invoke final chain with second retrieval context and original user query
final_answer = final_chain.invoke({
    "context": second_context,   # more precise second retrieval context
    "question": user_query       # original user query for final answer
})

print("\n=== Final Answer ===")
print(final_answer)
```

---

## Summary - Query Rewriting vs Other Strategies

| | Normal RAG | HyDE | MultiQueryRetriever | Query Rewriting |
|---|---|---|---|---|
| **LLM calls** | 1 | 2 | 2 | 3 |
| **Vector DB searches** | 1 | 1 | N | 2 |
| **Uses retrieved docs to improve query** | No | No | No | Yes |
| **Best for** | Specific queries | Sparse queries | Vague queries | Complex/ambiguous queries |
| **Cost** | Low | Medium | Medium-High | High |
| **Retrieval quality** | Base | Better embedding match | Broader coverage | Most precise |
