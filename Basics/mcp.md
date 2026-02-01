RAG Architecture Examples

This document demonstrates two approaches for Retrieval-Augmented Generation (RAG) systems:

1. Deterministic / Local RAG – flag-based routing without LLM tool selection


2. Agentic / LLM-driven RAG – LLM decides which tool to call via MCP or LangChain




---

1️⃣ Deterministic / Local RAG

Architecture

Browser JS
   ↓
Backend API (Python FastAPI or Node.js)
   ├── Solr (term search)
   └── Vector DB (semantic search)

Flow

1. User query is sent to the API.


2. API checks a flag (e.g., term_search = true).


3. Deterministic routing:

term_search = true → call Solr

term_search = false → call Vector DB



4. API returns results to the frontend.


5. Optional fallback: If Solr returns no results, call Vector DB automatically.



Key Points

Deterministic, predictable, testable.

No LLM involved.

Fully production-grade for enterprise search portals.

MCP is optional; can be used as an internal orchestration layer but is not required.


Example (Python FastAPI)

from fastapi import FastAPI
from pydantic import BaseModel
import requests
from vector_search import vector_search

app = FastAPI()

class SearchRequest(BaseModel):
    query: str
    term_search: bool

@app.post("/search")
def search(req: SearchRequest):
    if req.term_search:
        solr_resp = requests.post("http://localhost:3000/solr-search", json={"query": req.query})
        if solr_resp.json().get("results"):
            return solr_resp.json()
    return vector_search(req.query)


---

2️⃣ Agentic / LLM-driven RAG

Architecture

Browser JS
   ↓
MCP / LangChain Service
   ├── Tool: Solr search
   ├── Tool: Vector DB search
   └── Optional tools: API calls, summarization
   ↓
LLM decides which tool(s) to call based on user query

Flow

1. User query is sent to MCP service.


2. LLM receives the query and determines:

Which tool to call

Arguments for the tool

Whether multiple tools need to be called



3. MCP routes the call to the correct tool.


4. Tool returns results to LLM.


5. LLM may merge, summarize, or further process the results.


6. Final response is returned to the frontend.



Key Points

Dynamic, flexible tool selection.

LLM makes decisions → tool calls are non-deterministic.

MCP standardizes tool contracts across languages/services.

Common in enterprise multi-tool RAG systems and AI assistants.


Example (Python + LangChain)

from langchain.tools import tool
from langchain.chat_models import ChatOpenAI

llm = ChatOpenAI(model="gpt-4.1-mini")

@tool
def solr_search(query: str):
    # Call Solr and return results
    return {"source": "solr", "results": ["doc1", "doc2"]}

@tool
def vector_search(query: str):
    # Call Vector DB and return results
    return {"source": "vector", "results": ["doc3", "doc4"]}

tools = [solr_search, vector_search]
llm_with_tools = llm.bind_tools(tools)

response = llm_with_tools.invoke("How do I reset my password?")


---

✅ Comparison Table

Feature	Deterministic RAG	Agentic RAG

LLM needed	❌ No	✅ Yes
Tool routing	✅ Explicit / deterministic	✅ LLM decides
Debuggable	✅ Easy	⚠️ Harder
Latency	Low	Higher
Suitable for production	✅ Yes	✅ Yes (multi-tool/agent)
MCP needed	❌ Optional	✅ Recommended



---

Summary

Deterministic RAG: Best for local, production-grade search portals; no LLM required.

Agentic RAG: Useful for multi-tool AI assistants where the LLM decides