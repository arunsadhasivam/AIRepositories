
# MCP — Model Context Protocol — Complete Tutorial

> **Every concept. Why. What problem. How it connects. Code. Advantages. Disadvantages. Local vs Remote. Production tips.**

---

## Table of Contents

1. [What is MCP?](#what-is-mcp)
2. [Project Structure](#project-structure)
3. [Concept 1 — Agent Card](#concept-1--agent-card)
4. [Concept 2 — Tool](#concept-2--tool)
5. [Concept 3 — Tool Annotations](#concept-3--tool-annotations)
6. [Concept 4 — Resource](#concept-4--resource)
7. [Concept 5 — Prompt Template](#concept-5--prompt-template)
8. [Concept 6 — Transport (Local vs Remote)](#concept-6--transport-local-vs-remote)
9. [Concept 7 — Sampling](#concept-7--sampling)
10. [Concept 8 — Roots](#concept-8--roots)
11. [Concept 9 — Capabilities Handshake](#concept-9--capabilities-handshake)
12. [Concept 10 — Progress Notifications](#concept-10--progress-notifications)
13. [Concept 11 — Cancellation](#concept-11--cancellation)
14. [Concept 12 — Logging](#concept-12--logging)
15. [Concept 13 — Pagination](#concept-13--pagination)
16. [Production Integration](#production-integration)
17. [How Everything Connects — Full Flow](#how-everything-connects--full-flow)

---

## What is MCP?

MCP (Model Context Protocol) is an open standard that lets LLMs connect to external tools, data, and services in a **standardized way**.

Think of it as **USB for AI** — any LLM host that speaks MCP can connect to any MCP server, regardless of language.

```
Without MCP:  LLM ──custom code──► Tool A
              LLM ──custom code──► Tool B    (every integration is bespoke)
              LLM ──custom code──► Tool C

With MCP:     LLM ──MCP──► Tool A
              LLM ──MCP──► Tool B            (one standard, any tool)
              LLM ──MCP──► Tool C
```

---

## Project Structure

```
mcp-server/
│
├── server.py                  # Main MCP server (all concepts live here)
├── .well-known/
│   └── agent.json             # Agent Card (auto-served on remote SSE)
│                              # On LOCAL stdio: exchanged in init handshake
├── tools/
│   ├── weather.py             # Tool functions
│   ├── search.py              # RAG search tool
│   └── documents.py           # Document tools
├── resources/
│   └── clinical_store.py      # Resource functions
├── prompts/
│   └── templates.py           # Prompt templates
└── requirements.txt           # pip install mcp
```

---

## Concept 1 — Agent Card

### 1. Why it is Used
Before a client connects, it needs to know what the server offers.  
Agent Card is that **discovery file** — a JSON the server publishes about itself.

### 2. What Problem it Solves
| Without Agent Card | With Agent Card |
|---|---|
| Manually configure every tool in every client | Client reads one JSON — knows everything automatically |
| Fragile — any tool change breaks clients | Server updates card — clients auto-adapt |
| No version info | Version declared — clients check compatibility |

### 3. How it Relates
> **Spring Boot Analogy:** Agent Card = `web.xml / application.properties` + `@SpringBootApplication`.  
> Just as Spring reads config on startup to know what beans/routes exist,  
> MCP client reads Agent Card to know what tools exist.

### 4. How Agent Card is Connected — Full Flow

#### LOCAL (stdio) — How Agent Card is exchanged:
```
1. Claude Desktop spawns your server.py as a child process
2. Host sends JSON-RPC initialize request over STDIN
3. Server responds with its capabilities over STDOUT
4. This response IS the Agent Card data — no HTTP needed

stdin  ──► { "method": "initialize", "params": { "protocolVersion": "2024-11-05" } }
stdout ◄── { "result": { "serverInfo": { "name": "...", "version": "..." }, "capabilities": {...} } }
```

#### REMOTE (SSE) — How Agent Card is served:
```
1. Client does HTTP GET http://your-server.com/.well-known/agent.json
2. Server returns agent.json BEFORE SSE connection is established
3. Client reads it, decides to connect
4. Client then connects to SSE endpoint: GET http://your-server.com/sse

HTTP GET /.well-known/agent.json  ──► returns agent.json
HTTP GET /sse                     ──► opens SSE stream (JSON-RPC flows here)
```

### 4. Code

```python
# server.py
from mcp.server.fastmcp import FastMCP

# ─── Everything here becomes the Agent Card ───────────────────
mcp = FastMCP(
    name        = "clinical-rag-server",          # → agent.json: "name"
    version     = "1.0.0",                        # → agent.json: "version"
    description = "RAG pipeline over clinical docs"  # → agent.json: "description"
)

# FastMCP auto-generates agent.json from your @mcp.tool(), @mcp.resource() etc.
# You do NOT write agent.json manually.
```

**What FastMCP auto-generates as `agent.json`:**
```json
{
  "name":        "clinical-rag-server",
  "version":     "1.0.0",
  "description": "RAG pipeline over clinical docs",
  "url":         "http://localhost:8000",
  "capabilities": {
    "tools":     {},
    "resources": {},
    "prompts":   {},
    "logging":   {}
  },
  "skills": [
    { "id": "search_docs",     "name": "Search Documents" },
    { "id": "get_weather",     "name": "Get Weather" }
  ]
}
```

**Where it is served (remote SSE only):**
```
GET http://localhost:8000/.well-known/agent.json
```

**Claude Desktop config (local stdio — no HTTP, no agent.json file needed):**
```json
{
  "mcpServers": {
    "rag-server": {
      "command": "python",
      "args":    ["server.py"]
    }
  }
}
```

### 5. Advantages
- Auto-discovery — client needs zero manual configuration
- Version info — client knows if server is compatible before connecting
- Capabilities declared — client skips unsupported features gracefully

### 6. Disadvantages
- If card is stale/outdated — client gets wrong info
- No versioning standard in protocol — you manage breaking changes
- FastMCP regenerates it on every restart — no static file to edit

### 7. Local vs Remote

| Mode | How Agent Card is Exchanged | Protocol |
|---|---|---|
| Local (stdio) | During JSON-RPC `initialize` handshake over stdin/stdout | No HTTP — pure JSON pipes |
| Remote (SSE) | `HTTP GET /.well-known/agent.json` before SSE connects | HTTP then SSE |

### 8. Production Tips
- Version your server: `"version": "2.1.0"` — clients detect breaking changes
- Never hardcode capabilities — let FastMCP generate from your decorators
- Cache agent.json on client side with TTL — do not fetch on every request

---

## Concept 2 — Tool

### 1. Why it is Used
A Tool is a **function the LLM can call** to perform actions — search DB, call API, run query.  
Without tools, LLM can only generate text from training data (frozen at cutoff date).

### 2. What Problem it Solves
LLMs are frozen at their training cutoff. Tools give the LLM **live executable functions**  
that reach external systems in real time.

### 3. How it Relates
> **Spring MVC Analogy:** Tool = `@GetMapping` / `@PostMapping` Controller method.  
> Just as a Controller handles HTTP requests and returns responses,  
> a Tool handles LLM requests and returns results.

### 4. How Tool is Connected — Full Flow

```
User: "What's the weather in San Jose?"

LLM thinks: I need weather data → I see get_weather tool → I will call it

JSON-RPC request (LOCAL: over stdin / REMOTE: over HTTP):
{
  "method": "tools/call",
  "params": {
    "name":      "get_weather",
    "arguments": { "city": "San Jose" }
  }
}

Server runs get_weather("San Jose") → returns "San Jose: 72°F, Sunny"

JSON-RPC response back to LLM:
{
  "result": {
    "content": [{ "type": "text", "text": "San Jose: 72°F, Sunny" }]
  }
}

LLM uses result in its final response to user.
```

### 4. Code

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("demo")

# ─── BASIC TOOL ───────────────────────────────────────────────
@mcp.tool()
def get_weather(city: str) -> str:
    """
    Returns current weather for a city.
    IMPORTANT: Clear docstring = LLM picks this tool correctly.
    Vague docstring = LLM picks wrong tool.
    """
    # Simulated — replace with real OpenWeatherMap API call
    weather_data = {
        "San Jose":      "72°F, Sunny",
        "San Francisco": "62°F, Foggy",
        "Menlo Park":    "70°F, Clear",
    }
    return weather_data.get(city, f"{city}: 68°F, Partly Cloudy")


# ─── RAG SEARCH TOOL ─────────────────────────────────────────
@mcp.tool()
def search_clinical_docs(query: str, top_k: int = 5) -> list:
    """
    Search clinical documents using hybrid BM25 + pgvector retrieval.
    Use this when user asks about medical conditions, treatments, or guidelines.
    """
    # Your existing RAG pipeline call
    results = rag_pipeline.search(query, top_k=top_k)
    return results


# ─── MULTI-PARAM TOOL ────────────────────────────────────────
@mcp.tool()
def filter_docs(query: str, doc_type: str, date_from: str) -> dict:
    """Filter clinical docs by type and date range."""
    return {
        "query":     query,
        "type":      doc_type,
        "from":      date_from,
        "results":   db.query(query, doc_type, date_from)
    }
```

**How LLM discovers tools (tools/list request):**
```json
{
  "method": "tools/list"
}
```
```json
{
  "result": {
    "tools": [
      {
        "name":        "get_weather",
        "description": "Returns current weather for a city.",
        "inputSchema": {
          "type":       "object",
          "properties": { "city": { "type": "string" } },
          "required":   ["city"]
        }
      }
    ]
  }
}
```

### 5. Advantages
- LLM auto-selects the right tool — no if/else routing code needed
- Strongly typed inputs via Python type hints — validated automatically
- Docstring becomes the tool description — LLM uses it to decide when to call

### 6. Disadvantages
- LLM picks wrong tool if descriptions are ambiguous — write crystal clear docstrings
- No built-in retry on tool failure — handle exceptions inside the tool
- Tool result size limited by context window — large results need pagination

### 7. Local vs Remote

| Mode | Protocol | How Tool Call Works |
|---|---|---|
| Local (stdio) | JSON-RPC 2.0 over stdin/stdout | Host writes JSON to stdin, reads response from stdout |
| Remote (SSE) | JSON-RPC 2.0 over HTTP + SSE | HTTP POST with JSON body, response via SSE stream |

### 8. Production Tips
- Always wrap tool body in try/except — never let exception crash the server
- Add timeouts to external calls: `requests.get(url, timeout=30)`
- Log every tool invocation with inputs for observability (Langfuse)
- One tool = one responsibility — do not put search + write in same tool

---

## Concept 3 — Tool Annotations

### 1. Why it is Used
Annotations are **metadata on a tool** telling the client about its behavior —  
is it safe? Does it modify data? Is it slow? Client and LLM use this before calling.

### 2. What Problem it Solves
Without annotations: LLM deletes data when user just wanted to read.  
With annotations: client shows confirmation dialog before destructive calls.

### 3. How it Relates
> **Java Analogy:** Tool Annotations = `@Transactional(readOnly=true)` or `@PreAuthorize` in Spring Security.  
> Just as those annotations declare behavior to the Spring framework,  
> MCP annotations declare tool behavior to the LLM/client.

### 4. How Annotations are Connected — Full Flow

```
tools/list response includes annotations per tool:

{
  "name": "search_docs",
  "annotations": {
    "readOnlyHint":   true,   ← LLM sees this: safe to call without warning
    "idempotentHint": true,   ← same input = same output
    "title":          "Safe Document Search"
  }
}

{
  "name": "delete_patient",
  "annotations": {
    "readOnlyHint":    false, ← LLM sees this: modifies data
    "destructiveHint": true   ← Client: show warning dialog to user first
  }
}
```

### 4. Code

```python
# ─── READ-ONLY TOOL — safe, no side effects ──────────────────
@mcp.tool(annotations={
    "readOnlyHint":   True,   # does NOT modify any data
    "idempotentHint": True,   # same input = same output always
    "title":          "Safe Document Search"
})
def search_docs(query: str) -> list:
    """Read-only search — safe to call anytime."""
    return pgvector_search(query)


# ─── DESTRUCTIVE TOOL — client should warn user ───────────────
@mcp.tool(annotations={
    "readOnlyHint":    False,  # DOES modify data
    "destructiveHint": True,   # deletes or overwrites
    "title":           "Delete Patient Record"
})
def delete_patient_record(patient_id: str) -> str:
    """Permanently deletes patient record — irreversible."""
    db.delete(patient_id)
    return f"Deleted: {patient_id}"


# ─── LONG RUNNING TOOL ───────────────────────────────────────
@mcp.tool(annotations={
    "readOnlyHint":  True,
    "openWorldHint": True   # makes external network/API calls
})
async def reindex_all_documents() -> str:
    """Re-indexes 50K+ clinical documents — takes several minutes."""
    await run_full_reindex()
    return "Reindex complete"
```

### 5. Advantages
- LLM makes smarter tool selection — prefers safe tools by default
- Client UI can show confirmation dialog before destructive calls
- Audit logs can automatically flag destructive tool usage

### 6. Disadvantages
- Annotations are **hints only** — protocol does NOT enforce them
- LLM may ignore annotations — real safety must be inside tool logic
- No standard for custom annotations beyond the defined set

### 7. Local vs Remote

| Mode | Where Annotations Appear |
|---|---|
| Local (stdio) | Inside `tools/list` JSON response over stdout during discovery |
| Remote (SSE) | Inside `tools/list` HTTP JSON response during discovery |

### 8. Production Tips
- Always set `readOnlyHint` — never leave it undefined in production
- Enforce safety in code too — annotations alone are not a security boundary
- Log all `destructiveHint=True` calls with user identity for audit trail

---

## Concept 4 — Resource

### 1. Why it is Used
Resources are **read-only data** the LLM can access as context — files, DB rows, configs.  
Unlike tools which DO things, resources just provide DATA.

### 2. What Problem it Solves
Stuffing all documents into the LLM prompt upfront is wasteful.  
Resources let the LLM pull only what it needs, by URI — like lazy loading.

### 3. How it Relates
> **AEM/Sling Analogy:** Resource = JCR Node.  
> Just as Sling resolves a URL to a JCR node and reads its properties,  
> MCP resolves a URI to a Resource and reads its content.

### 4. How Resource is Connected — Full Flow

```
CLIENT (LLM host) sends resources/read request:

{
  "method": "resources/read",
  "params": {
    "uri": "clinical://doc/12345"
  }
}

SERVER resolves URI → calls get_clinical_doc(doc_id="12345") → returns content

{
  "result": {
    "contents": [{
      "uri":      "clinical://doc/12345",
      "mimeType": "text/plain",
      "text":     "Patient record content here..."
    }]
  }
}
```

### 4. Code

```python
# ─── STATIC RESOURCE — fixed URI ─────────────────────────────
@mcp.resource("config://app-settings")
def get_config() -> str:
    """Returns app configuration as readable resource."""
    return "max_results=10\nmode=production\nrag_enabled=true"


# ─── TEMPLATE RESOURCE — URI with parameter ───────────────────
# Client calls: resources/read  uri=clinical://doc/12345
@mcp.resource("clinical://doc/{doc_id}")
def get_clinical_doc(doc_id: str) -> str:
    """
    Fetch clinical document by ID.
    URI template: {doc_id} is extracted from the URI automatically.
    """
    doc = pgvector_store.get_document(doc_id)
    return doc.content


# ─── FILE RESOURCE ────────────────────────────────────────────
@mcp.resource("file://guidelines/{filename}")
def get_guideline_file(filename: str) -> str:
    """Read clinical guideline file."""
    with open(f"/data/guidelines/{filename}") as f:
        return f.read()
```

**How LLM discovers resources (resources/list):**
```json
{
  "result": {
    "resources": [
      {
        "uri":         "config://app-settings",
        "name":        "App Settings",
        "description": "Returns app configuration as readable resource.",
        "mimeType":    "text/plain"
      }
    ],
    "resourceTemplates": [
      {
        "uriTemplate": "clinical://doc/{doc_id}",
        "name":        "Clinical Document",
        "mimeType":    "text/plain"
      }
    ]
  }
}
```

### 5. Advantages
- Lazy loading — LLM fetches only needed data, not everything upfront
- Separation of concerns — data access separate from tool logic
- URI templates allow parameterized access to any record

### 6. Disadvantages
- Read-only — cannot write back via resource (use Tool for writes)
- No streaming for large resources — whole content returned at once
- Changing URI scheme breaks all clients

### 7. Local vs Remote

| Mode | Protocol | How Resource is Read |
|---|---|---|
| Local (stdio) | JSON-RPC `resources/read` over stdin/stdout | URI sent in, content returned as JSON |
| Remote (SSE) | JSON-RPC `resources/read` over HTTP | HTTP POST with URI, content in response |

### 8. Production Tips
- Add access control inside resource functions — check caller identity
- Cache frequently-read resources with Redis TTL — avoid DB hit per LLM call
- Version resource URIs: `clinical://v2/doc/{id}` — allows schema migration
- Return structured JSON not raw text for machine-readable resources

---

## Concept 5 — Prompt Template

### 1. Why it is Used
Prompt Templates are **reusable, parameterized prompts** the server exposes.  
Instead of every client writing its own prompts, server defines best-practice prompts centrally.

### 2. What Problem it Solves
Each developer writing their own prompts = inconsistency + duplicated effort.  
Prompt Templates centralize prompt engineering — change once, all clients improve.

### 3. How it Relates
> **Spring Data Analogy:** Prompt Template = `@Query` in Spring Data JPA.  
> Just as `@Query` centralizes JPQL in the repository (not in every service),  
> Prompt Templates centralize prompt logic in the MCP server.

### 4. How Prompt Template is Connected — Full Flow

```
Step 1: Client lists available prompts
  Request:  { "method": "prompts/list" }
  Response: { "result": { "prompts": [ { "name": "rag_search", "arguments": [...] } ] } }

Step 2: Client fetches specific prompt with arguments
  Request:  { "method": "prompts/get",
              "params": { "name": "rag_search", "arguments": { "query": "diabetes" } } }

Step 3: Server fills template and returns assembled prompt
  Response: { "result": { "messages": [
               { "role": "user", "content": { "type": "text",
                 "text": "Search clinical documents for: diabetes. Return top 5..." } }
             ]}}

Step 4: Client sends this assembled prompt to the LLM
```

### 4. Code

```python
# ─── BASIC PROMPT TEMPLATE ───────────────────────────────────
@mcp.prompt()
def weather_prompt(city: str) -> str:
    """Prompt template for weather queries."""
    return (
        f"What is the weather in {city}? "
        f"Use the get_weather tool to find accurate real-time data."
    )


# ─── RAG PROMPT TEMPLATE with multiple params ────────────────
@mcp.prompt()
def rag_clinical_prompt(query: str, top_k: int = 5, doc_type: str = "all") -> str:
    """Best-practice prompt for clinical document search."""
    return (
        f'Search clinical documents for: "{query}". '
        f"Filter by document type: {doc_type}. "
        f"Return top {top_k} results. "
        f"Use search_clinical_docs tool. Cite document IDs in response."
    )


# ─── LLM-AS-JUDGE EVALUATION PROMPT ─────────────────────────
@mcp.prompt()
def judge_prompt(question: str, answer: str, context: str) -> str:
    """Prompt for LLM-as-Judge faithfulness/relevance evaluation."""
    return (
        f"Evaluate this RAG answer.\n"
        f"Question: {question}\n"
        f"Answer:   {answer}\n"
        f"Context:  {context}\n"
        f"Score faithfulness, relevance, completeness 1-5. "
        f"Return JSON: {{faithfulness: N, relevance: N, completeness: N}}"
    )
```

### 5. Advantages
- Centralized prompt engineering — one change improves all clients
- Parameterized — reusable across different inputs
- Discoverable — clients list all available prompts via `prompts/list`

### 6. Disadvantages
- No versioning in protocol — breaking prompt changes affect all clients immediately
- Clients may ignore available prompts and write their own anyway
- No prompt chaining built in — compose manually

### 7. Local vs Remote

| Mode | How Prompts are Fetched |
|---|---|
| Local (stdio) | `prompts/list` and `prompts/get` JSON-RPC over stdin/stdout |
| Remote (SSE) | `prompts/list` and `prompts/get` HTTP JSON-RPC calls |

### 8. Production Tips
- Version prompt IDs: `rag_clinical_prompt_v2` — never change existing prompt signature
- Test prompts with LLM-as-Judge before deploying — measure faithfulness score
- Store prompt performance metrics — track which prompts produce best scores

---

## Concept 6 — Transport (Local vs Remote)

### 1. Why it is Used
Transport defines **HOW** the MCP client and server communicate.  
Two modes: **local (stdio)** for same-machine tools, **remote (SSE)** for networked servers.

### 2. What Problem it Solves
Different deployments need different communication:
- Developer's local file tool → zero network setup needed
- Production RAG server → must serve thousands of clients remotely

### 3. How it Relates
> **Java Analogy:**  
> `stdio` = in-process method call (same JVM, direct call)  
> `SSE`   = REST API call over HTTP (different JVM, remote)  
> Same logic, different transport — like `@Service` vs `@FeignClient` in Spring.

### 4. How Transport is Connected — Full Flow

#### LOCAL stdio:
```
Claude Desktop config:
{
  "mcpServers": {
    "rag": { "command": "python", "args": ["server.py"] }
  }
}

1. Claude Desktop spawns: python server.py
2. JSON-RPC flows over OS pipes:
   Claude Desktop STDOUT ──► server.py STDIN
   server.py STDOUT       ──► Claude Desktop STDIN
3. Every tool call = one JSON write to stdin, one JSON read from stdout
4. Server dies when Claude Desktop closes — same process lifecycle
```

#### REMOTE SSE:
```
1. Server runs independently: python server.py --transport sse
2. Client connects: HTTP GET http://your-server.com/sse
3. SSE stream opens — kept alive
4. Tool calls: client writes JSON-RPC to stream, server responds on stream
5. Server runs independently — can restart without affecting client config
```

### 4. Code

```python
import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("rag-server")

@mcp.tool()
def search_docs(query: str) -> list:
    return rag_pipeline.search(query)

if __name__ == "__main__":

    # ─── LOCAL (stdio) ────────────────────────────────────────
    # Run: python server.py
    # Protocol: JSON-RPC 2.0 over stdin/stdout pipes
    # No HTTP server. No ports. No auth needed.
    # Host spawns this as child process.
    if "--transport" not in sys.argv:
        mcp.run(transport="stdio")

    # ─── REMOTE (SSE) ─────────────────────────────────────────
    # Run: python server.py --transport sse
    # Protocol: JSON-RPC 2.0 over HTTP + Server-Sent Events
    # Starts HTTP server on port 8000
    # Client connects to: http://localhost:8000/sse
    elif sys.argv[sys.argv.index("--transport") + 1] == "sse":
        mcp.run(transport="sse")
```

**Claude Desktop config for LOCAL:**
```json
{
  "mcpServers": {
    "rag-server": {
      "command": "python",
      "args":    ["server.py"]
    }
  }
}
```

**Client connection for REMOTE:**
```
GET http://localhost:8000/sse          ← SSE stream opens here
GET http://localhost:8000/.well-known/agent.json  ← agent card here
```

### 5. Advantages & Disadvantages

| Factor | Local (stdio) | Remote (SSE) |
|---|---|---|
| Protocol | JSON-RPC over stdin/stdout | JSON-RPC over HTTP + SSE |
| Latency | Near zero — in-process | Network latency |
| Security | High — no network exposure | Needs HTTPS, auth tokens |
| Scalability | Single machine only | Cloud-scale, multi-client |
| Setup | Simple — just run Python | Server hosting, ports, SSL |
| Lifecycle | Dies with host process | Independent — restart separately |
| Best for | Dev tools, Claude Desktop | Production, multi-user, cloud |

### 7. Local vs Remote Summary
```
USE LOCAL when:
  ✅ Developing on your machine
  ✅ Claude Desktop personal tools
  ✅ Security-sensitive (no network exposure)
  ✅ Single user, single machine

USE REMOTE when:
  ✅ Production deployment
  ✅ Multiple users sharing tools
  ✅ RAG pipeline serving many LLM hosts
  ✅ Tools need powerful remote hardware (GPU)
```

### 8. Production Tips
- Always use HTTPS for remote SSE — never plain HTTP in production
- Add Bearer token auth middleware on SSE endpoint
- Implement reconnection logic on client — SSE connections can drop
- Use nginx reverse proxy in front of SSE server for TLS termination
- Health check endpoint: `GET /health` — separate from MCP SSE endpoint

---

## Concept 7 — Sampling

### 1. Why it is Used
Sampling lets the MCP **SERVER ask the HOST's LLM** to generate text mid-execution.  
Normal flow: LLM → calls Tool. Sampling reverses: Tool → calls LLM back.

### 2. What Problem it Solves
Sometimes a tool needs LLM intelligence to complete its work —  
generating a summary, classifying a document, deciding which sub-tool to call.  
Sampling enables **server-driven agentic loops**.

### 3. How it Relates
> **Java Analogy:** Sampling = Callback pattern.  
> Tool registers a callback (LLM call), host executes it and returns result.  
> Like `CompletableFuture` where your service calls back to framework for help.

### 4. How Sampling is Connected — Full Flow

```
Normal flow:    User → LLM → calls Tool → returns result → LLM responds

Sampling flow:  User → LLM → calls Tool
                             Tool needs LLM help
                             Tool → sampling/createMessage → Host LLM
                             Host LLM generates text → returns to Tool
                             Tool uses LLM output → returns final result → LLM responds

JSON-RPC from SERVER to HOST (reverse direction):
{
  "method": "sampling/createMessage",
  "params": {
    "messages": [{ "role": "user", "content": { "type": "text",
                   "text": "Summarize this clinical document in 3 sentences: ..." } }],
    "maxTokens": 200
  }
}
```

### 4. Code

```python
from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP("rag-server")

@mcp.tool()
async def generate_clinical_summary(doc_id: str, ctx: Context) -> str:
    """
    Fetches document then asks LLM to summarize it.
    Uses sampling — server calls LLM mid-tool-execution.
    """
    # Step 1: fetch document (normal resource read — no LLM involved)
    doc_content = fetch_document(doc_id)

    # Step 2: ask LLM to summarize it (SAMPLING — reverse direction)
    # This sends a JSON-RPC request BACK to the host LLM
    summary = await ctx.sample(
        f"Summarize this clinical document in 3 sentences:\n{doc_content}"
    )

    # Step 3: return LLM-generated summary to the original LLM call
    return summary.text


# Flow diagram:
# User:  "Summarize document 123"
# LLM:   calls generate_clinical_summary(doc_id="123")
# Tool:  fetches doc → sends sampling request to host LLM
# Host:  LLM generates 3-sentence summary
# Tool:  receives summary → returns to original LLM
# LLM:   uses summary in final response to user
```

### 5. Advantages
- Server can use LLM intelligence mid-tool — enables true agentic workflows
- Server drives the reasoning loop — not just a passive responder
- Composable — tool can call LLM multiple times with different prompts

### 6. Disadvantages
- Most hosts **do NOT support sampling yet** — verify before building on it
- Circular dependency risk — LLM → Tool → LLM → risk of infinite loops
- Extra latency — two LLM calls happening for one user request
- Hard to debug — nested LLM calls in Langfuse traces

### 7. Local vs Remote

| Mode | How Sampling Works |
|---|---|
| Local (stdio) | Tool writes sampling request to stdout; host LLM processes; result returned via stdin |
| Remote (SSE) | Tool sends sampling SSE event to host; host calls LLM; result returned via SSE |

### 8. Production Tips
- Check host capabilities for sampling before using — graceful fallback if missing
- Set `maxTokens` on sampling requests — prevent runaway generation
- Add circuit breaker — if sampling fails N times, fall back to non-LLM logic
- Log sampling calls separately in Langfuse — distinguish inner vs outer LLM calls

---

## Concept 8 — Roots

### 1. Why it is Used
Roots are a **security mechanism** where the CLIENT tells the SERVER  
which file paths or URI namespaces it is allowed to access.

### 2. What Problem it Solves
Without roots: a buggy tool could read files anywhere on the server.  
With roots: client declares allowed scope, server must stay within it.

### 3. How it Relates
> **Security Analogy:** Roots = CORS allowed origins in Spring Security, or `chroot` jail in Linux.  
> Client declares its allowed scope, server respects the boundary.

### 4. How Roots is Connected — Full Flow

```
During initialization (both LOCAL and REMOTE):

CLIENT sends initialize with roots:
{
  "method": "initialize",
  "params": {
    "roots": [
      { "uri": "file:///data/clinical/", "name": "Clinical Docs" },
      { "uri": "file:///data/config/",   "name": "App Config"    }
    ]
  }
}

SERVER receives roots → stores them → validates every path against them

When tool tries to read /etc/passwd:
  Tool checks: does "file:///etc/passwd" start with any declared root?
  No → ACCESS DENIED — return error, do not read file
```

### 4. Code

```python
from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP("file-server")

@mcp.tool()
def read_file(path: str, ctx: Context) -> str:
    """
    Read file — validates against client-declared roots.
    Roots tell us which paths client allows us to access.
    """
    # Get roots declared by client during initialization
    # Client sent: roots = ["file:///data/clinical/", "file:///data/config/"]
    allowed_roots = ctx.client_roots

    # Build the file URI for comparison
    file_uri = f"file://{path}"

    # Validate: is requested path within any allowed root?
    is_allowed = any(
        file_uri.startswith(root) for root in allowed_roots
    )

    if not is_allowed:
        # Reject — path is outside client-declared roots
        return f"ACCESS DENIED: '{path}' outside allowed roots: {allowed_roots}"

    # Safe to read — within allowed root
    with open(path) as f:
        return f.read()


# Claude Desktop declares roots in config:
# {
#   "mcpServers": {
#     "file-server": {
#       "command": "python",
#       "args": ["server.py"],
#       "roots": [
#         { "uri": "file:///data/clinical/", "name": "Clinical Docs" }
#       ]
#     }
#   }
# }
```

### 5. Advantages
- Client controls server's file access scope — clear security boundary
- Named roots — human-readable labels for audit logs
- Scope fixed at session start — predictable access pattern

### 6. Disadvantages
- Protocol does NOT enforce roots — server must validate manually in every tool
- Complex apps need many roots — configuration overhead
- Too-broad roots (`/data/` instead of `/data/clinical/`) weaken security

### 7. Local vs Remote

| Mode | How Roots are Declared |
|---|---|
| Local (stdio) | Sent during JSON-RPC `initialize` handshake over stdin/stdout |
| Remote (SSE) | Sent during SSE connection initialization HTTP request |

### 8. Production Tips
- Treat roots as hints — enforce path validation independently in every tool
- Log all root violations — attempt to access outside roots = security incident
- Use most restrictive roots possible — principle of least privilege
- Use different roots per user role — admin vs read-only users

---

## Concept 9 — Capabilities Handshake

### 1. Why it is Used
When client connects, **both sides declare what they support**.  
This prevents crashes when client tries a feature the server does not implement.

### 2. What Problem it Solves
Without capabilities: client calls sampling → server does not support it → hard crash.  
With capabilities: client checks first → gracefully skips unsupported features.

### 3. How it Relates
> **Java Analogy:** Capabilities = Interface negotiation.  
> Like checking if a class `implements Serializable` before serializing,  
> or TLS cipher negotiation — both sides agree on what they support.

### 4. How Capabilities Handshake is Connected — Full Flow

```
Step 1: Client connects (LOCAL: spawns process / REMOTE: HTTP GET /sse)

Step 2: Client sends initialize request:
{
  "jsonrpc": "2.0",
  "method":  "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "sampling": {},                   ← client supports sampling
      "roots": { "listChanged": true }  ← client supports roots
    },
    "clientInfo": { "name": "Claude Desktop", "version": "1.0" }
  }
}

Step 3: Server responds with its capabilities:
{
  "jsonrpc": "2.0",
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools":     {},   ← server has tools
      "resources": {},   ← server has resources
      "prompts":   {},   ← server has prompts
      "logging":   {}    ← server supports logging
                         ← NO sampling: client knows not to request it
    },
    "serverInfo": { "name": "rag-server", "version": "1.0.0" }
  }
}

Step 4: Client stores server capabilities → only uses what server declared
```

### 4. Code

```python
# FastMCP AUTO-DECLARES capabilities from your decorators.
# No manual capability code needed.

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("rag-server")

# Adding this → declares "tools" capability automatically
@mcp.tool()
def search_docs(query: str) -> list:
    return rag_pipeline.search(query)

# Adding this → declares "resources" capability automatically
@mcp.resource("clinical://doc/{doc_id}")
def get_doc(doc_id: str) -> str:
    return db.get(doc_id)

# Adding this → declares "prompts" capability automatically
@mcp.prompt()
def search_prompt(query: str) -> str:
    return f"Search for: {query}"

# Logging is declared automatically by FastMCP

# The initialize handshake response will include:
# {
#   "capabilities": {
#     "tools":     {},   ← because @mcp.tool() exists
#     "resources": {},   ← because @mcp.resource() exists
#     "prompts":   {},   ← because @mcp.prompt() exists
#     "logging":   {}    ← always included by FastMCP
#   }
# }
```

### 5. Advantages
- Graceful degradation — client skips features server does not support
- Forward compatible — new features added without breaking old clients
- Zero manual config — FastMCP auto-declares from your decorators

### 6. Disadvantages
- Capabilities mismatch = features silently unavailable — hard to debug
- Declared at init, fixed for session — no dynamic updates
- Client must re-connect to pick up new capabilities after server update

### 7. Local vs Remote

| Mode | When Handshake Happens |
|---|---|
| Local (stdio) | First JSON-RPC message over stdin/stdout when host spawns server |
| Remote (SSE) | First HTTP request when client connects to SSE endpoint |

### 8. Production Tips
- Log full capabilities exchange at DEBUG level — diagnose mismatch issues
- Check server capabilities before calling advanced features (sampling, roots)
- Pin `protocolVersion` in production — avoid surprise breaking changes on upgrade

---

## Concept 10 — Progress Notifications

### 1. Why it is Used
For long-running tools (re-indexing 50K docs, full eval pipeline),  
server sends **progress updates** so client and user know the operation is alive.

### 2. What Problem it Solves
Without progress: user stares at spinner for 5 minutes not knowing if tool is hung.  
With progress: user sees `Indexing document 12,450 of 50,000 — 25%`.

### 3. How it Relates
> **Java Analogy:** Progress Notifications = `ProgressMonitor` in Swing,  
> or `@Async` with progress callback in Spring.  
> Same concept — long task, periodic status updates back to caller.

### 4. How Progress is Connected — Full Flow

```
Tool starts executing...

Server sends notification (LOCAL: stdout / REMOTE: SSE push):
{ "method": "notifications/progress", "params": { "progress": 1, "total": 7 } }
{ "method": "notifications/progress", "params": { "progress": 2, "total": 7 } }
{ "method": "notifications/progress", "params": { "progress": 3, "total": 7 } }
...
{ "method": "notifications/progress", "params": { "progress": 7, "total": 7 } }

Tool returns final result:
{ "result": { "content": [{ "type": "text", "text": "Reindex complete" }] } }

Client receives both notifications AND final result on same stream.
```

### 4. Code

```python
import asyncio
from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP("rag-server")

@mcp.tool()
async def reindex_clinical_docs(folder: str, ctx: Context) -> str:
    """
    Re-indexes all clinical documents.
    Sends progress notifications so client shows progress bar.
    """
    stages = [
        "Scanning folder for documents",     # step 1
        "Parsing PDFs with Apache Tika",     # step 2
        "Chunking text into segments",        # step 3
        "Generating embeddings via Ollama",  # step 4
        "Writing vectors to pgvector",       # step 5
        "Updating Solr BM25 index",          # step 6
        "Flushing Redis cache",              # step 7
    ]
    total = len(stages)

    for i, stage in enumerate(stages):
        await asyncio.sleep(1)               # simulate real work

        # Send progress notification to client
        # LOCAL:  written as JSON notification to stdout
        # REMOTE: pushed as SSE event to client
        await ctx.report_progress(
            progress = i + 1,   # current step number
            total    = total    # total steps
        )
        await ctx.info(f"Step {i + 1}/{total}: {stage}")

    return f"Reindex complete: {total} stages finished for {folder}"
```

### 5. Advantages
- User knows tool is alive — no false timeout cancellations
- Client can show progress bar — better UX for long operations
- Combined with logging — full observability during execution

### 6. Disadvantages
- Not all clients display progress — some silently ignore notifications
- Adds async complexity — must use async/await throughout
- Granularity is manual — you decide what counts as a step

### 7. Local vs Remote

| Mode | How Progress is Delivered |
|---|---|
| Local (stdio) | JSON-RPC notification written to stdout between request/response |
| Remote (SSE) | SSE event pushed to client HTTP connection in real time |

### 8. Production Tips
- Report progress at meaningful milestones — not every loop iteration
- Include counts in progress: `Indexed 12,450 / 50,000 docs`
- Cap to max 1 notification per second — avoid flooding client
- Always send `progress(total, total)` before returning — confirms completion

---

## Concept 11 — Cancellation

### 1. Why it is Used
When user clicks Stop or a timeout fires, client sends a **cancellation signal**  
to stop a running tool mid-execution. Saves compute, gives user control.

### 2. What Problem it Solves
Without cancellation: accidental `reindex all documents` runs 10 minutes even after user realizes mistake.  
With cancellation: user clicks stop → tool exits immediately and cleans up.

### 3. How it Relates
> **Java Analogy:** Cancellation = `Thread.interrupt()` + `InterruptedException`,  
> or `Future.cancel()` in `ExecutorService`.  
> Same pattern — external signal to stop ongoing work gracefully.

### 4. How Cancellation is Connected — Full Flow

```
Client sends cancellation notification (while tool is running):
{
  "method": "notifications/cancelled",
  "params": {
    "requestId": "abc123",   ← ID of the tool call to cancel
    "reason":    "User clicked stop"
  }
}

Server:
1. Receives notification on stdin (LOCAL) or SSE (REMOTE)
2. Raises asyncio.CancelledError inside the running tool coroutine
3. Tool's except CancelledError block runs — cleanup happens
4. Tool exits gracefully
```

### 4. Code

```python
import asyncio
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("rag-server")

@mcp.tool()
async def long_embedding_job(folder: str) -> str:
    """
    Long embedding job — can be cancelled by client at any point.
    Use async + await asyncio.sleep(0) to enable cancellation checks.
    """
    processed = 0
    files     = list_files(folder)
    total     = len(files)

    try:
        for file in files:
            # yield to event loop — this is where CancelledError is raised
            # Without this, cancellation cannot interrupt the loop
            await asyncio.sleep(0)

            embed_document(file)     # do the real work
            processed += 1
            print(f"Processed {processed}/{total}")

        return f"Completed: {processed} files embedded"

    except asyncio.CancelledError:
        # Client sent notifications/cancelled
        # Clean up any partial work before exiting
        cleanup_partial_index(folder)
        print(f"Cancelled after {processed} files — cleanup done")
        return f"Cancelled: {processed}/{total} files processed before stop"
```

### 5. Advantages
- Saves compute — stops expensive GPU/DB operations immediately on cancel
- Good UX — user not stuck waiting for accidental long-running call
- Graceful cleanup — `CancelledError` lets you rollback partial state

### 6. Disadvantages
- Must write all cancellable tools as `async` — cannot cancel synchronous blocking code
- Partial state cleanup is your responsibility — protocol does not help
- `await asyncio.sleep(0)` needed in every loop iteration — extra boilerplate

### 7. Local vs Remote

| Mode | How Cancellation Signal is Sent |
|---|---|
| Local (stdio) | Client writes `notifications/cancelled` JSON to server's stdin |
| Remote (SSE) | Client sends HTTP POST or SSE cancellation event to server |

### 8. Production Tips
- Add `await asyncio.sleep(0)` at top of every loop — enables cancellation point
- Always clean up DB/file state in `CancelledError` handler — avoid partial writes
- Log cancellation events — useful for billing and performance analysis
- Set client-side timeout AND handle `CancelledError` — defense in depth

---

## Concept 12 — Logging

### 1. Why it is Used
MCP server can send **structured log messages** back to the client during tool execution.  
Full observability without needing separate logging infrastructure.

### 2. What Problem it Solves
When a tool fails silently you have no visibility into what happened inside MCP server.  
Logging lets client see exactly what server did — like println inside a black box.

### 3. How it Relates
> **Java Analogy:** MCP Logging = SLF4J + Logback in Spring Boot,  
> but log messages are forwarded to the MCP client instead of written to a file.  
> Like MDC (Mapped Diagnostic Context) propagated over the wire.

### 4. How Logging is Connected — Full Flow

```
Tool executes and logs at various points...

Server sends log notifications (LOCAL: stdout / REMOTE: SSE push):
{
  "method": "notifications/message",
  "params": {
    "level":  "info",
    "logger": "rag-server",
    "data":   "Running hybrid BM25 + pgvector search"
  }
}
{
  "method": "notifications/message",
  "params": {
    "level":  "warning",
    "data":   "Redis cache miss — hitting pgvector directly"
  }
}

Client receives log notifications on same stream as tool results.
Client can display them in console, forward to Langfuse, or ignore.
```

### 4. Code

```python
import logging
from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP("rag-server")

# ─── Option 1: Standard Python logging ───────────────────────
# FastMCP captures and forwards as notifications/message
@mcp.tool()
def search_docs_logged(query: str) -> list:
    """Search with Python standard logging."""
    logging.debug(  f"search_docs called: query={query}")
    logging.info(    "Running hybrid BM25 + pgvector search")
    logging.warning( "Redis cache miss — hitting pgvector directly")

    results = hybrid_search(query)

    logging.info(f"Found {len(results)} results for: {query}")
    return results


# ─── Option 2: Context logging (async tools) ─────────────────
# Direct MCP notifications via ctx — more control
@mcp.tool()
async def search_docs_ctx(query: str, ctx: Context) -> list:
    """Search with context-based MCP logging."""
    await ctx.debug(  f"Tool invoked: query={query}")
    await ctx.info(    "Checking Redis cache first")

    cached = redis.get(query)
    if cached:
        await ctx.info("Cache HIT — returning cached results")
        return cached

    await ctx.warning("Cache MISS — running full vector search")
    results = hybrid_search(query)

    await ctx.info(f"Search complete: {len(results)} results")
    return results
```

### 5. Advantages
- Full observability without separate logging infra — logs come to client
- Structured log levels: debug, info, warning, error — client can filter
- Combined with Langfuse — trace every LLM call with tool logs

### 6. Disadvantages
- Noisy if overused — too many logs flood client connection
- Not all clients display MCP logs — some silently discard them
- Must NEVER log PHI/PII in clinical environments — serious compliance risk

### 7. Local vs Remote

| Mode | How Logs are Delivered |
|---|---|
| Local (stdio) | JSON-RPC `notifications/message` written to stdout between tool messages |
| Remote (SSE) | SSE log events pushed to client in real time during tool execution |

### 8. Production Tips
- **Never log PHI/PII** — clinical environments require data masking (HIPAA)
- Use correlation IDs in logs — tie tool log to specific user request trace
- Set log level per environment: DEBUG in dev, INFO/WARNING in prod
- Forward MCP logs to Langfuse for full RAG pipeline observability

---

## Concept 13 — Pagination

### 1. Why it is Used
When a tool returns large datasets (1000 documents, 500 results),  
returning everything at once overloads the LLM context window.  
Pagination returns data in **manageable chunks**.

### 2. What Problem it Solves
LLM context windows are limited (~128K tokens for most models).  
Dumping 50,000 clinical documents in one response would exceed the window.  
Pagination returns 10 at a time — LLM asks for next page as needed.

### 3. How it Relates
> **Spring Analogy:** Pagination = Spring Data's `Pageable` + `Page<T>`.  
> Same concept — `PageRequest(page, size)`, `Page.hasNext()`, `Page.getTotalElements()`.  
> MCP has no built-in `Pageable` — you implement same pattern manually.

### 4. How Pagination is Connected — Full Flow

```
LLM calls tool: search_clinical_docs_paged(query="diabetes", page=1, page_size=10)
Server returns:  { page:1, total:847, has_next:true, results:[doc1...doc10] }

LLM sees has_next=true → calls again: search_clinical_docs_paged(..., page=2)
Server returns:  { page:2, total:847, has_next:true, results:[doc11...doc20] }

LLM found answer on page 2 → stops. No need to fetch remaining 82 pages.

Each page = one JSON-RPC request/response cycle (LOCAL: stdin/stdout, REMOTE: HTTP)
```

### 4. Code

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("rag-server")

@mcp.tool()
def search_clinical_docs_paged(
    query:     str,
    page:      int = 1,    # page number — starts at 1
    page_size: int = 10    # results per page — default 10
) -> dict:
    """
    Paginated clinical document search.
    LLM calls page=1, checks has_next, then page=2, etc.
    Stops when has_next=False or answer is found.
    """
    # Run search on full dataset
    all_results = hybrid_search(query)    # returns all matching docs
    total       = len(all_results)

    # Calculate page boundaries
    start        = (page - 1) * page_size     # first index for this page
    end          = start + page_size           # last index for this page
    current_page = all_results[start:end]      # slice for this page only

    return {
        "page":        page,
        "page_size":   page_size,
        "total":       total,
        "total_pages": (total + page_size - 1) // page_size,
        "has_next":    end < total,            # True = more pages exist
        "has_prev":    page > 1,               # True = not first page
        "results":     current_page            # only this page's docs
    }
```

### 5. Advantages
- Fits within LLM context window — page by page, not all at once
- Reduces memory — server does not load all results into RAM
- LLM can stop early — answer on page 1 means no page 2 needed

### 6. Disadvantages
- Multiple round trips — 3 pages = 3 tool calls = 3x latency
- No built-in cursor standard in MCP — implement offset or cursor yourself
- LLM may not paginate correctly — needs clear prompt instruction

### 7. Local vs Remote

| Mode | How Pagination Works |
|---|---|
| Local (stdio) | Each page = one JSON-RPC request/response cycle over stdin/stdout |
| Remote (SSE) | Each page = one HTTP JSON-RPC request, response returned via SSE |

### 8. Production Tips
- Use cursor-based pagination for large datasets — offset breaks on data changes
- Include `next_cursor` in response — LLM passes it back for next page
- Cache paginated results with Redis TTL — avoid re-running search on page 2
- Default `page_size=10` — LLM context safe; caller can increase if needed

---

## Production Integration

### Your RAG Pipeline → MCP Server Mapping

| Your Component | MCP Concept | How |
|---|---|---|
| Flask API endpoints | Tools | `@mcp.tool()` |
| pgvector document store | Resources | `clinical://doc/{id}` |
| LLM-as-Judge prompts | Prompt Templates | `@mcp.prompt()` |
| Langfuse logging | Logging | `ctx.info()` / `logging.info()` |
| Redis cache | Tool with `readOnlyHint=True` | Annotated read-only tool |
| Input/output guardrails | Two tools | Called before/after main tool |
| PII masking | Inside tool | Applied before any logging |
| Hybrid BM25 + pgvector | Core tool logic | Inside `search_docs` tool |
| LLM-as-Judge eval | Sampling | `ctx.sample()` inside judge tool |

### Production Checklist

```
Security:
  ✅ HTTPS only — never plain HTTP for remote SSE
  ✅ Bearer token auth on all SSE connections
  ✅ PII/PHI masking before any logging (HIPAA)
  ✅ Roots declared — validated inside every file-reading tool
  ✅ Annotate every tool — readOnlyHint + destructiveHint always set

Reliability:
  ✅ Exception handling inside every tool — server never crashes
  ✅ Timeouts on all external calls (DB, API, Solr)
  ✅ CancelledError handled in all async tools
  ✅ Health endpoint: GET /health separate from SSE endpoint

Observability:
  ✅ Langfuse connected for full RAG + MCP trace visibility
  ✅ Correlation IDs in all log messages
  ✅ Progress notifications on all tools > 5 second duration
  ✅ Log all destructiveHint=True tool calls with user identity

Performance:
  ✅ Redis cache on read-only tools — reduce pgvector hits
  ✅ Pagination on all search tools — default page_size=10
  ✅ Cap progress notifications to 1/sec — avoid flooding
  ✅ Rate limiting on SSE endpoint — prevent tool flooding

Compatibility:
  ✅ Pin MCP protocolVersion — avoid surprise breaking changes
  ✅ Version all prompt IDs: rag_prompt_v2
  ✅ Version resource URIs: clinical://v2/doc/{id}
  ✅ Reconnection logic on client for SSE drops
```

---

## How Everything Connects — Full Flow

```
┌─────────────────────────────────────────────────────┐
│                   MCP HOST                          │
│              (Claude Desktop / App)                 │
│                                                     │
│  1. READ Agent Card  ─────────────────────────────► │ /.well-known/agent.json (REMOTE)
│     (or init handshake on LOCAL stdio)              │ stdin/stdout init (LOCAL)
│                                                     │
│  2. CAPABILITIES HANDSHAKE ──────────────────────►  │ What do you support?
│     ◄──────────────────────────────────────────     │ tools, resources, prompts, logging
│                                                     │
│  3. DECLARE ROOTS ────────────────────────────────► │ You may access: /data/clinical/
│                                                     │
│  User asks: "Search for diabetes treatment"         │
│                                                     │
│  4. LLM decides: call search_docs tool              │
│     TOOL CALL ─────────────────────────────────►    │ tools/call → search_docs("diabetes")
│                                                     │
│     ◄── LOGGING notifications ──────────────────    │ "Cache miss, running pgvector"
│     ◄── PROGRESS notifications ─────────────────    │ "Step 2/5: Embedding query"
│     ◄── TOOL RESULT ────────────────────────────    │ [doc1, doc2, doc3 ...]
│                                                     │
│  5. LLM needs more context: read resource           │
│     RESOURCE READ ─────────────────────────────►    │ resources/read → clinical://doc/123
│     ◄── RESOURCE CONTENT ───────────────────────    │ Full document text
│                                                     │
│  6. LLM uses PROMPT TEMPLATE                        │
│     PROMPT GET ────────────────────────────────►    │ prompts/get → rag_clinical_prompt
│     ◄── ASSEMBLED PROMPT ───────────────────────    │ Filled template string
│                                                     │
│  7. Tool needs LLM help: SAMPLING                   │
│     ◄── SAMPLING REQUEST ───────────────────────    │ sampling/createMessage
│     SAMPLING RESULT ───────────────────────────►    │ LLM-generated summary
│                                                     │
│  8. User clicks stop: CANCELLATION                  │
│     CANCEL NOTIFICATION ───────────────────────►    │ notifications/cancelled
│     ◄── CLEANUP COMPLETE ───────────────────────    │ Tool exits gracefully
│                                                     │
└─────────────────────────────────────────────────────┘

TRANSPORT:
  LOCAL  → all arrows above = JSON-RPC over stdin/stdout pipes
  REMOTE → all arrows above = JSON-RPC over HTTPS + SSE stream
```

---

*Install: `pip install mcp` | Debug: `npx @modelcontextprotocol/inspector python server.py`*
