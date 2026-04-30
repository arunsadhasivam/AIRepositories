# Complete LLM Flow - String to Vector to Token to String

---

## Full End to End Flow

---

### Step 1 - User Input

**Input:**
```
Plain string typed by user
"What are aspirin risks?"
```

**Code:**
```python
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores.pgvector import PGVector
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Initialize Ollama LLM - Mistral running locally
llm = Ollama(model="mistral")

# Initialize Ollama embeddings - ONLY for vector DB search, not LLM internal
embeddings = OllamaEmbeddings(model="mistral")

# Connect to existing pgvector store - documents already indexed
vectorstore = PGVector(
    collection_name="clinical_documents",
    connection_string="postgresql+psycopg2://user:password@localhost:5432/ragdb",
    embedding_function=embeddings
)

# User query as plain string - no vector yet
user_query = "What are aspirin risks?"
```

**Output:**
```
Plain string — "What are aspirin risks?"
```

**Inference:** None — just user input captured as string.

---

### Step 2 - Vector DB Search

**Input:**
```
Plain string — "What are aspirin risks?"
```

**Code:**
```python
# Create retriever - fetches top 3 matching chunks as plain text
# internally: string → embedding model → query vector → pgvector cosine search → plain text chunks
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# Helper to join all retrieved plain text chunks into single string
def format_docs(docs):
    # docs = list of Document objects - .page_content is plain text per chunk
    return "\n\n".join([doc.page_content for doc in docs])
```

**Output:**
```
Plain text chunks returned from pgvector:
Chunk 1: "Aspirin can cause stomach bleeding and ulcers..."
Chunk 2: "Aspirin overdose symptoms include nausea, tinnitus..."
Chunk 3: "Patients with kidney disease should avoid aspirin..."
```

**Inference:**
- Ollama embedding model runs locally
- Converts query string `"What are aspirin risks?"` → dense float vector `[0.23, 0.91, 0.45...]`
- pgvector computes cosine similarity between query vector and all stored chunk vectors
- Ranks chunks by similarity score
- Returns top 3 highest ranked chunks as plain text
- **No LLM involved here — only embedding model math**

---

### Step 3 - Prompt Building

**Input:**
```
{context} = plain text chunks from Step 2
{question} = original user query string "What are aspirin risks?"
```

**Code:**
```python
# Define prompt template
# {context} = plain text chunks injected here - NOT vectors
# {question} = original user query string via RunnablePassthrough() - NOT vector
rag_prompt = ChatPromptTemplate.from_template("""
You are a medical assistant. Answer using the context only.
If you don't know, say you don't know.

Context: {context}
Question: {question}
Answer:
""")
```

**Output:**
```
One complete plain string prompt:

"You are a medical assistant. Answer using the context only.
If you don't know, say you don't know.

Context:
Aspirin can cause stomach bleeding and ulcers...
Aspirin overdose symptoms include nausea, tinnitus...
Patients with kidney disease should avoid aspirin...

Question: What are aspirin risks?
Answer:"
```

**Inference:** None — just string interpolation. No model runs here.

---

### Step 4 - Chain Wired and Invoked

**Input:**
```
user_query plain string — "What are aspirin risks?"
```

**Code:**
```python
# Build RAG chain - wires Steps 2, 3, LLM, and parser together
rag_chain = (
    {
        # Step 2: retriever runs similarity_search internally
        # plain string → query vector → pgvector → plain text chunks → format_docs → plain string
        "context": retriever | format_docs,

        # Step 3: RunnablePassthrough passes user_query string unchanged into {question}
        "question": RunnablePassthrough()
    }
    # Step 3: fills {context} and {question} into prompt template as plain strings
    | rag_prompt

    # Steps 5-10: LLM receives complete plain string - all internal steps run here
    | llm

    # Step 11: extracts plain string from AIMessage response object
    | StrOutputParser()
)

# Invoke chain - triggers all steps in sequence
answer = rag_chain.invoke(user_query)
```

**Output:**
```
Triggers full chain execution in sequence:
Step 2 → Step 3 → Step 5 → Step 6 → Step 7 → Step 8 → Step 9 → Step 10 → Step 11
```

**Inference:** Chain orchestration only — no model runs at this line itself.

---

### Step 5 - Tokenizer Splits String into Tokens
*(Inside LLM — invisible to you)*

**Input:**
```
Complete plain string prompt from Step 3
"You are a medical assistant... Question: What are aspirin risks? Answer:"
```

**Code:**
```
No code — happens invisibly inside Mistral LLM
```

**Output:**
```
List of token strings:
["You", "▁are", "▁a", "▁medical", "▁assistant", "...", "▁asp", "irin", "▁risks", "?"]
```

**Inference:**
- Mistral tokenizer vocabulary loaded into memory
- Entire prompt string split into subword tokens
- "aspirin" splits into `["▁asp", "irin"]` — subword tokenization
- Each token is a unit the LLM understands
- **No deep learning yet — just vocabulary lookup**

---

### Step 6 - Token Strings → Integer IDs
*(Inside LLM — invisible to you)*

**Input:**
```
List of token strings:
["You", "▁are", "▁a", "▁medical", "▁assistant", "▁asp", "irin", "▁risks", "?"]
```

**Code:**
```
No code — happens invisibly inside Mistral LLM
```

**Output:**
```
List of integer token IDs:
[887, 892, 263, 4802, 13892, 4521, 3012, 7823, 30]
```

**Inference:**
- Tokenizer vocabulary dictionary lookup — each token string → unique integer ID
- Mistral has vocabulary of ~32,000 tokens
- This converts text into numbers the neural network can process
- **No deep learning yet — just dictionary lookup**

---

### Step 7 - Token IDs → Embedding Vectors
*(Inside LLM embedding layer — invisible to you)*

**Input:**
```
List of integer token IDs:
[887, 892, 263, 4802, 13892, 4521, 3012, 7823, 30]
```

**Code:**
```
No code — happens invisibly inside Mistral LLM embedding layer
```

**Output:**
```
Matrix of token embedding vectors (4096 dimensions for Mistral 7B):
[
  [0.12, 0.87, 0.34, 0.56...],   <- vector for token "You"
  [0.34, 0.56, 0.91, 0.23...],   <- vector for token "are"
  [0.91, 0.23, 0.45, 0.78...],   <- vector for token "asp"
  [0.67, 0.12, 0.78, 0.34...],   <- vector for token "irin"
  [0.45, 0.89, 0.23, 0.67...],   <- vector for token "risks"
  ...
]
```

**Inference:**
- Mistral embedding matrix loaded — size is [32000 vocab × 4096 dimensions]
- Each token ID looks up its row in embedding matrix → 4096-dimensional float vector
- These vectors are NOT same as pgvector embeddings — completely different model and space
- **Deep learning begins here — first neural network layer activates**

---

### Step 8 - Attention Mechanism Processes Token Vectors
*(Inside LLM — 32 transformer layers — invisible to you)*

**Input:**
```
Matrix of token embedding vectors — one vector per token
Shape: [sequence_length × 4096]
```

**Code:**
```
No code — happens invisibly across 32 transformer layers inside Mistral 7B
```

**Output:**
```
Context-enriched output vectors — one per token position
Shape: [sequence_length × 4096]
"risks" vector now attends strongly to "aspirin", "bleeding", "kidney"
```

**Inference:**
- **This is the core deep learning inference step**
- Mistral 7B loads all 32 transformer layers into GPU/CPU memory
- Each layer runs Multi-Head Attention (32 attention heads in Mistral 7B):
  - Each token vector computes Query (Q), Key (K), Value (V) matrices
  - Attention scores computed: `softmax(Q × K^T / sqrt(d_k)) × V`
  - "aspirin" token attends to "risks", "bleeding", "stomach" — high attention scores
  - "kidney" token attends to "avoid", "aspirin" — high attention scores
  - Low attention tokens (stop words like "the", "are") get low scores
- After attention — Feed Forward Network runs on each token position
- This repeats across all 32 layers — each layer refines understanding
- Final layer output vectors are **context-aware representations** of every token
- **Most computationally expensive step — billions of floating point operations**

---

### Step 9 - Output Vectors → Token IDs
*(Inside LLM LM head — invisible to you)*

**Input:**
```
Final context-enriched output vectors from last transformer layer
Shape: [sequence_length × 4096]
```

**Code:**
```
No code — happens invisibly inside Mistral LM head layer
```

**Output:**
```
Probability distribution over 32000 vocabulary tokens for next token:
Token "Asp"    → 0.42 (highest)
Token "The"    → 0.18
Token "Risk"   → 0.12
Token "When"   → 0.08
...
Selected token ID → 4521 ("Asp")
```

**Inference:**
- LM head linear layer projects 4096-dimensional vector → 32000-dimensional logits
- Softmax converts logits to probability distribution over full vocabulary
- Greedy decoding selects highest probability token
- Or temperature/top-p sampling picks from top candidates
- **Sorts by attention-enriched probability — returns best next token**
- Process repeats auto-regressively — each new token generated one at a time
- Stops when `<end>` token generated or max tokens reached

---

### Step 10 - Token IDs → Plain String (Decoding)
*(Inside LLM decoder — invisible to you)*

**Input:**
```
List of output integer token IDs:
[4521, 3012, 508, 4556, 16165...]
```

**Code:**
```
No code — happens invisibly inside Mistral tokenizer decoder
```

**Output:**
```
Plain string answer:
"Aspirin can cause stomach bleeding, ulcers, and kidney issues.
Patients with kidney disease should avoid it..."
```

**Inference:**
- Each output token ID looked up in tokenizer vocabulary — ID → token string
- Subword tokens joined back — `["Asp", "irin"]` → `"Aspirin"`
- All tokens concatenated into final answer string
- **No deep learning here — just vocabulary reverse lookup**

---

### Step 11 - StrOutputParser

**Input:**
```
AIMessage object from LLM:
AIMessage(content="Aspirin can cause stomach bleeding...", response_metadata={...})
```

**Code:**
```python
# StrOutputParser extracts plain string from AIMessage wrapper object
# AIMessage(content="Aspirin can cause...") → "Aspirin can cause..."
StrOutputParser()
```

**Output:**
```
Plain string — final answer:
"Aspirin can cause stomach bleeding, ulcers, and kidney issues..."
```

**Inference:** None — just unwraps AIMessage object and returns `.content` string.

---

## Complete Summary Table

| Step | Where | Input | Output | Inference | You Control? |
|---|---|---|---|---|---|
| 1. User input | Your code | Keyboard | Plain string | None | Yes |
| 2. Vector DB search | Your code | Plain string | Plain text chunks | Embedding model math + cosine similarity | Yes |
| 3. Prompt building | Your code | Chunks + query string | Complete prompt string | None — string interpolation | Yes |
| 4. Chain invoke | Your code | Plain string | Triggers chain | None — orchestration only | Yes |
| 5. Tokenization | Inside LLM | Plain string | Token strings | Vocabulary lookup — no deep learning | No |
| 6. Token → ID | Inside LLM | Token strings | Integer IDs | Dictionary lookup — no deep learning | No |
| 7. ID → Vector | Inside LLM | Integer IDs | Token vectors | First neural layer — embedding matrix lookup | No |
| 8. Attention | Inside LLM | Token vectors | Output vectors | **32 transformer layers — full deep learning inference** | No |
| 9. Vector → ID | Inside LLM | Output vectors | Integer IDs | LM head softmax — ranks tokens by probability | No |
| 10. ID → String | Inside LLM | Integer IDs | Plain string | Vocabulary reverse lookup — no deep learning | No |
| 11. StrOutputParser | Your code | AIMessage object | Plain string | None — unwrap object | Yes |

---

## Key Insights

| Insight | Detail |
|---|---|
| **You only control** | Steps 1, 2, 3, 4, 11 |
| **Real deep learning happens** | Only Step 8 — 32 transformer layers with attention |
| **Vector DB vectors vs LLM vectors** | Completely separate — different models, different spaces |
| **String → vector (your code)** | Only at similarity_search() — Step 2 |
| **Vector → string (your code)** | pgvector returns chunks as plain text — Step 2 |
| **LLM input** | Always plain string — never vectors from your side |
| **LLM output** | Always plain string — never vectors from your side |
| **Attention ranks tokens** | Softmax scores determine which tokens matter most |
| **Steps 5, 6, 10** | Inside LLM but just lookup — no deep learning |
| **Step 7** | First neural layer — embedding matrix |
| **Step 8** | Core inference — 32 layers × 32 attention heads × billions of operations |
| **Step 9** | Sorts by probability — returns best next token greedily |
