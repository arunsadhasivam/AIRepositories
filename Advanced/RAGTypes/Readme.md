# RAG Architectures — A Complete Overview

A structured reference to the 7 core Retrieval-Augmented Generation (RAG) patterns, from baseline to fully agentic systems.

---

## 1. Naïve RAG *(Baseline / Vanilla RAG)*

**What it is:**
The original "plug-and-play" architecture consisting of basic chunking, indexing in a vector database, and retrieving information for the LLM to read.

**Use Case:**
Basic Q&A and simple search over internal FAQs.

---

## 2. Conversational RAG *(RAG with Memory)*

**What it is:**
Extends baseline RAG by incorporating session memory. It stores prior interactions and injects context and conversational history into the retrieval and generation phases.

**Use Case:**
Multi-turn chatbots and personalized customer service.

---

## 3. Advanced RAG

**What it is:**
Uses pre-retrieval techniques (like query rewriting to fix poorly phrased questions) and post-retrieval optimizations (like re-ranking to ensure the most relevant context is fed directly to the LLM).

**Use Case:**
Highly specific, technical document analysis and summarization.

---

## 4. GraphRAG

**What it is:**
Integrates Knowledge Graphs with vector databases. It maps connections and relationships between entities instead of just relying on text semantics.

**Use Case:**
Complex knowledge mapping, fraud detection, and uncovering deep connections in heavily related data.

---

## 5. Adaptive RAG

**What it is:**
A dynamic system that analyzes the user's query and routes it to the most efficient retrieval strategy. It can determine whether to use standard search, a web search, or a complex multi-stage process depending on query complexity.

**Use Case:**
Enterprise systems that handle a mix of simple facts and highly complex, open-ended analytical questions.

---

## 6. Corrective RAG *(CRAG)*

**What it is:**
Focuses on reliability by adding validation loops. If retrieved documents are irrelevant to the user's prompt, the system autonomously searches for external information or corrects the query before generating a response.

**Use Case:**
Applications where mitigating hallucinations and ensuring strict factual accuracy are paramount.

---

## 7. Agentic RAG

**What it is:**
The most advanced architecture. It treats the retriever as an autonomous AI agent that can make decisions on its own — such as how many times to retrieve, when to switch data sources, and how to verify its own work before presenting an answer.

**Use Case:**
Action-oriented systems that not only answer questions but execute multi-step business logic, data extraction, and tool usage.

---

## Quick Comparison

| # | Architecture       | Key Capability                          | Best For                                      |
|---|--------------------|-----------------------------------------|-----------------------------------------------|
| 1 | Naïve RAG          | Chunk → Embed → Retrieve → Generate    | Simple FAQ / document Q&A                     |
| 2 | Conversational RAG | + Session memory & chat history         | Multi-turn chatbots                           |
| 3 | Advanced RAG       | + Query rewriting & re-ranking          | Technical document analysis                   |
| 4 | GraphRAG           | + Entity relationship mapping           | Fraud detection, knowledge graphs             |
| 5 | Adaptive RAG       | + Dynamic query routing                 | Mixed-complexity enterprise queries           |
| 6 | Corrective RAG     | + Validation loops & fallback search    | Hallucination-critical applications           |
| 7 | Agentic RAG        | + Autonomous multi-step decision-making | Complex workflows with tool use               |

---

*Each architecture builds on the previous, adding intelligence, reliability, and autonomy at each tier.*
