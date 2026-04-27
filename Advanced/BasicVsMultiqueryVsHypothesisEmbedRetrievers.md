# RAG Retrieval Strategies - Complete Guide

---

## 1. Normal RAG

### What is it?
Plain retrieval — user query directly searches the vector DB. No extra LLM calls. No preprocessing.

### Why use it?
- Simplest approach
- Lowest cost
- Fastest response time

### When to use it?
- User queries are already **specific and well-formed**
- Documents in vector DB are **well structured**
- Low latency is critical
- Budget is tight

### Advantage
- No extra LLM calls = low cost
- Fast — single vector search
- Easy to debug and maintain

### Drawback
- Short/sparse queries like `"404 error"` produce **weak embeddings**
- May miss relevant documents if query wording differs from document wording
- No vocabulary gap bridging

### Flow
```
User Query → Embed Query → similarity_search() → Retrieved Docs → LLM → Answer
```

### Code
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

# Connect to pgvector store
vectorstore = PGVector(
    collection_name="clinical_documents",
    connection_string="postgresql+psycopg2://user:password@localhost:5432/ragdb",
    embedding_function=embeddings
)

# Define RAG answer prompt - {context} = docs, {question} = user query
rag_prompt = ChatPromptTemplate.from_template("""
Use the following context to answer the question.
If you don't know, say you don't know.

Context: {context}
Question: {question}
Answer:
""")

# Create base retriever - fetches top 3 similar documents
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# Helper to join all retrieved docs into single string
def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])

# Build Normal RAG chain
# retriever fetches docs -> format -> inject into prompt -> LLM -> string
normal_rag_chain = (
    {
        "context": retriever | format_docs,  # retrieved docs formatted as string
        "question": RunnablePassthrough()     # user query passed through unchanged
    }
    | rag_prompt         # inject context and question into prompt template
    | llm                # send filled prompt to Mistral LLM
    | StrOutputParser()  # extract plain string from LLM response object
)

# Invoke chain - single vector search, no extra LLM calls
answer = normal_rag_chain.invoke("What are side effects of aspirin?")
print(answer)
```

---

## 2. HyDE (Hypothetical Document Embeddings)

### What is it?
LLM first generates a **hypothetical answer** as if the document already exists. That hypothesis is then embedded and used to search the vector DB instead of the raw query.

### Why use it?
- Short queries like `"404 error"` produce weak embeddings
- Help documents are written in **detailed descriptive language**
- Hypothesis bridges the **vocabulary gap** between short query and detailed documents

### When to use it?
- User queries are **short, sparse, or ambiguous** (error codes, single words)
- Documents are **descriptively written** (help docs, clinical docs, manuals)
- You need **better semantic matching** than raw query provides

### Advantage
- Bridges vocabulary gap between query and document language
- Single extra LLM call only
- No special retriever class needed — plain `similarity_search()`
- Works well for **troubleshooting and diagnostic queries**

### Drawback
- One extra LLM call = slightly higher cost
- If hypothesis is wrong, retrieval is worse than normal RAG
- Hypothesis quality depends on LLM quality

### Flow
```
User Query → LLM generates Hypothesis → Embed Hypothesis → similarity_search() → Retrieved Docs → LLM → Answer
```

### Code
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

# Connect to pgvector store
vectorstore = PGVector(
    collection_name="clinical_documents",
    connection_string="postgresql+psycopg2://user:password@localhost:5432/ragdb",
    embedding_function=embeddings
)

# Step 1: Define HyDE prompt - instructs LLM to generate hypothetical passage
hyde_prompt = ChatPromptTemplate.from_template("""
You are a technical/medical expert.
Given the query below, generate a hypothetical document passage
that describes possible causes, explanations or solutions.
Just return the hypothetical passage only, nothing else.

Query: {question}
Hypothetical passage:
""")

# Step 2: Build HyDE hypothesis generation chain
# user query -> HyDE prompt -> LLM -> plain hypothesis string
hyde_chain = (
    hyde_prompt          # fill query into HyDE prompt template
    | llm                # LLM generates hypothetical passage
    | StrOutputParser()  # extract plain string from LLM response
)

# Step 3: Generate hypothesis from sparse user query
user_query = "404 error"

# LLM generates -> "404 can occur due to client down, wrong endpoint, bad input..."
hypothesis = hyde_chain.invoke({"question": user_query})

# Step 4: Search vector DB using hypothesis - richer embedding than "404 error"
hyde_docs = vectorstore.similarity_search(hypothesis, k=3)

# Step 5: Define final RAG answer prompt
rag_prompt = ChatPromptTemplate.from_template("""
Use the following context to answer the question.
If you don't know, say you don't know.

Context: {context}
Question: {question}
Answer:
""")

# Step 6: Helper to join all retrieved docs into single string
def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])

# Step 7: Format hypothesis-retrieved docs into string
hyde_context = format_docs(hyde_docs)

# Step 8: Build and invoke final answer chain with retrieved context
hyde_rag_chain = (
    rag_prompt           # inject context and question into prompt
    | llm                # LLM answers using retrieved context
    | StrOutputParser()  # extract plain string answer
)

# Step 9: Invoke with hypothesis-retrieved context and original query
answer = hyde_rag_chain.invoke({
    "context": hyde_context,  # docs retrieved via hypothesis embedding
    "question": user_query    # original raw user query
})
print(answer)
```

---

## 3. MultiQueryRetriever

### What is it?
LLM generates **multiple variations of the same query**. Each variation searches the vector DB independently. All results are **merged and deduplicated** before passing to LLM.

### Why use it?
- A single query phrasing may miss relevant documents
- Different phrasings retrieve different relevant documents
- Merged results give **broader and more complete context**

### When to use it?
- User queries are **vague or ambiguous** — `"What causes memory issues?"`
- Documents cover the **same topic from multiple angles**
- Retrieval coverage matters more than cost
- You want to compensate for **imperfect query formulation**

### Advantage
- Retrieves more relevant documents through multiple phrasings
- Automatic deduplication — no duplicate docs passed to LLM
- Built-in LangChain class handles everything internally

### Drawback
- Multiple vector DB searches = higher latency
- One extra LLM call to generate query variations
- Cost multiplies at scale with many users
- If prompt not restricted, LLM may generate too many queries

### Flow
```
User Query → LLM generates N queries → Each query searches vector DB independently → Merge + Deduplicate → Retrieved Docs → LLM → Answer
```

### Code
```python
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores.pgvector import PGVector
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.retrievers.multi_query import MultiQueryRetriever

# Initialize Ollama LLM - Mistral running locally
llm = Ollama(model="mistral")

# Initialize Ollama embeddings
embeddings = OllamaEmbeddings(model="mistral")

# Connect to pgvector store
vectorstore = PGVector(
    collection_name="clinical_documents",
    connection_string="postgresql+psycopg2://user:password@localhost:5432/ragdb",
    embedding_function=embeddings
)

# Step 1: Define restricted prompt - limits LLM to exactly 2 query variations
# "exactly 2" in prompt controls how many queries LLM generates
multi_query_prompt = ChatPromptTemplate.from_template("""
Generate exactly 2 alternative search queries for the vector store
from the user question below. No more, no less.
Output 2 queries, one per line, nothing else.

User question: {question}
Alternative queries:
""")

# Step 2: Build MultiQueryRetriever with restricted prompt
# internally: 1 LLM call generates queries, then searches vector DB for each
multi_retriever = MultiQueryRetriever.from_llm(
    retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),  # base retriever
    llm=llm,                                                      # LLM to generate query variations
    prompt=multi_query_prompt                                     # restricted to exactly 2 queries
)

# Step 3: Define final RAG answer prompt
rag_prompt = ChatPromptTemplate.from_template("""
Use the following context to answer the question.
If you don't know, say you don't know.

Context: {context}
Question: {question}
Answer:
""")

# Step 4: Helper to join all retrieved docs into single string
def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])

# Step 5: Build MultiQuery RAG chain
# MultiQueryRetriever fetches merged deduplicated docs -> format -> prompt -> LLM -> string
multi_rag_chain = (
    {
        "context": multi_retriever | format_docs,  # merged deduplicated docs formatted
        "question": RunnablePassthrough()           # original user query passed through unchanged
    }
    | rag_prompt         # inject merged context and question into prompt template
    | llm                # LLM answers using broader merged retrieved context
    | StrOutputParser()  # extract plain string from LLM response
)

# Step 6: Invoke chain - multiple searches happen internally, merged automatically
answer = multi_rag_chain.invoke("What causes memory issues in clinical systems?")
print(answer)
```

---

## Comparison Table

| | Normal RAG | HyDE | MultiQueryRetriever |
|---|---|---|---|
| **Extra LLM calls** | No | Yes — 1 call | Yes — 1 call |
| **Special retriever class** | No | No | Yes — `MultiQueryRetriever` |
| **What LLM generates** | Nothing | One hypothetical answer | Multiple query variations |
| **Vector DB search calls** | 1 | 1 | N (one per query variation) |
| **Result merging** | No | No | Yes — deduplicates |
| **Best for** | Specific queries | Short/sparse queries | Vague/ambiguous queries |
| **Vocabulary gap bridging** | No | Yes | Partial |
| **Cost** | Low | Medium | Medium-High |
| **Latency** | Low | Medium | High |
| **Risk** | Missing docs | Wrong hypothesis = worse results | High cost at scale |
| **Prompt controls count** | N/A | N/A | Yes — "exactly N" in prompt |
| **Recursive/infinite** | No | No | No — one level deep only |
