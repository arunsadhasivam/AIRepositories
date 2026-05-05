# Claude Desktop Config + MCP Transport Types — FastMCP Edition

---

## Part 1: claude_desktop_config.json — Desktop Only

### Important: This Config File is ONLY for Claude Desktop

```
claude_desktop_config.json is read by Claude Desktop GUI only.

If you are writing your own Python app / RAG pipeline / microservice:
  → this file means nothing to your code
  → your code never reads this file
  → put the MCP server URL directly in your Python code via sse_client() or Client()

This file is useful ONLY when:
  → you want Claude Desktop (the GUI app) to connect to your MCP server
  → so you can chat with Claude in the UI and it uses your tools
```

### Exact File Name and Location

```
Claude Desktop accepts ONLY one exact filename:  claude_desktop_config.json

NOT:  mcp.json
NOT:  mcp1.json
NOT:  config.json
```

| OS | Exact File Path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

### Full claude_desktop_config.json Format

```json
{
  "mcpServers": {

    "pdf-tools-local": {
      "command": "python",
      "args": ["C:/WorkSpace/servers/pdf_server.py"],
      "env": {
        "PDF_TEMP_DIR": "C:/tmp/pdf"
      }
    },

    "remote-html-tools": {
      "url": "http://192.168.1.100:8081/mcp",
      "headers": {
        "Authorization": "Bearer your-token-here"
      }
    }

  }
}
```

The key inside `mcpServers` (`"pdf-tools-local"`, `"remote-html-tools"`) is a label you choose. Claude Desktop shows it in the UI.

---

## Part 2: FastMCP vs Raw MCP SDK

All code in this guide uses **FastMCP** — the recommended way.

| | Raw MCP SDK | FastMCP |
|---|---|---|
| Server create | `Server("name")` | `FastMCP("name")` |
| Declare tool | `@mcp.list_tools()` + `@mcp.call_tool()` — two decorators | `@mcp.tool()` — one decorator |
| Input schema | Write JSON schema manually | Auto-generated from Python type hints |
| Run server | Manual Starlette + uvicorn wiring | `mcp.run(transport="...", port=...)` |
| Client | `ClientSession` + transport import | `Client("url")` — auto detects transport |
| Status | Works, more boilerplate | **Current recommended way** |

---

## Part 3: Three Transport Types — When to Use Which

```
┌──────────────────┬──────────────────────┬──────────────────────────────────┐
│   stdio          │   SSE                │   Streamable HTTP                │
│   (local only)   │   (remote/local)     │   (remote — LATEST) ← use this   │
├──────────────────┼──────────────────────┼──────────────────────────────────┤
│ stdin/stdout     │ GET  /sse            │ POST /mcp                        │
│ no port          │ POST /messages       │ single endpoint                  │
│                  │ 2 endpoints          │                                  │
├──────────────────┼──────────────────────┼──────────────────────────────────┤
│ Use when server  │ Use when connecting  │ Use for all new projects.        │
│ and client are   │ to an existing legacy│ Simpler than SSE — one endpoint  │
│ on same machine. │ system already using │ instead of two. Latest MCP       │
│ Good for local   │ SSE. Not recommended │ standard. Your                   │
│ dev and scripts. │ for new projects.    │ recommendation_server.py uses    │
│                  │                      │ this already.                    │
└──────────────────┴──────────────────────┴──────────────────────────────────┘
```

**One line summary:**
- `stdio` — same machine, no network, spawned as child process
- `SSE` — remote over HTTP but needs two endpoints; use only for legacy systems
- `Streamable HTTP` — remote over HTTP, one endpoint, latest standard, use this always

---

## Transport 1: stdio (Local Only)

### Server — FastMCP stdio

```python
# pdf_server_stdio.py
# No HTTP. No uvicorn. No port.
# Claude Desktop spawns this as a child process via claude_desktop_config.json

from fastmcp import FastMCP
import pdfplumber

mcp = FastMCP("pdf-tools")


@mcp.tool()
def pdf_extract_text(file_path: str) -> dict:
    """Extract plain text from a PDF file. Use when user wants to read or summarize a PDF."""
    pages_text = {}
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            pages_text[f"page_{i+1}"] = page.extract_text() or ""
    return {"file": file_path, "pages": pages_text}


@mcp.tool()
def pdf_extract_tables(file_path: str) -> dict:
    """Extract all tables from a PDF as JSON. Use when user wants structured data from a PDF."""
    all_tables = {}
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            if tables:
                all_tables[f"page_{i+1}"] = tables
    return {"file": file_path, "tables": all_tables}


if __name__ == "__main__":
    mcp.run(transport="stdio")   # no host, no port — stdin/stdout only
```

### claude_desktop_config.json — stdio

```json
{
  "mcpServers": {
    "pdf-tools": {
      "command": "python",
      "args": ["C:/WorkSpace/servers/pdf_server_stdio.py"]
    }
  }
}
```

### Python app client — stdio

```python
import asyncio
from fastmcp import Client
from mcp import StdioServerParameters

async def run():
    params = StdioServerParameters(
        command="python",
        args=["C:/WorkSpace/servers/pdf_server_stdio.py"]
    )
    async with Client(params) as client:
        result = await client.call_tool("pdf_extract_text", {"file_path": "C:/tmp/report.pdf"})
        print(result.content[0].text)

asyncio.run(run())
```

---

## Transport 2: SSE (Legacy Remote — Avoid for New Projects)

### Server — FastMCP SSE

```python
# pdf_server_sse.py
# Use only if you must connect to a legacy system that already runs SSE.
# For new projects use Streamable HTTP instead.

from fastmcp import FastMCP
import pdfplumber

mcp = FastMCP("pdf-tools-sse")


@mcp.tool()
def pdf_extract_text(file_path: str) -> dict:
    """Extract plain text from a PDF file. Use when user wants to read or summarize a PDF."""
    pages_text = {}
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            pages_text[f"page_{i+1}"] = page.extract_text() or ""
    return {"file": file_path, "pages": pages_text}


if __name__ == "__main__":
    # FastMCP auto creates GET /sse + POST /messages — no manual Starlette needed
    mcp.run(transport="sse", host="0.0.0.0", port=8080)
```

### claude_desktop_config.json — SSE remote

```json
{
  "mcpServers": {
    "remote-pdf-tools": {
      "url": "http://192.168.1.100:8080/sse",
      "headers": { "Authorization": "Bearer your-token" }
    }
  }
}
```

### Python app client — SSE

```python
import asyncio
from fastmcp import Client

async def run():
    # /sse in URL → FastMCP Client auto detects SSE transport
    async with Client("http://192.168.1.100:8080/sse") as client:
        result = await client.call_tool("pdf_extract_text", {"file_path": "/tmp/report.pdf"})
        print(result.content[0].text)

asyncio.run(run())
```

---

## Transport 3: Streamable HTTP (Latest — Use This Always)

### Server — FastMCP Streamable HTTP

```python
# pdf_server_streamable.py
# ONE endpoint: POST /mcp
# Latest MCP standard. Same as your recommendation_server.py.

from fastmcp import FastMCP
import pdfplumber
import requests
from bs4 import BeautifulSoup

mcp = FastMCP("pdf-html-tools")


@mcp.tool()
def pdf_extract_text(file_path: str) -> dict:
    """Extract plain text from a PDF file. Use when user wants to read or summarize a PDF."""
    pages_text = {}
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            pages_text[f"page_{i+1}"] = page.extract_text() or ""
    return {"file": file_path, "pages": pages_text}


@mcp.tool()
def pdf_extract_tables(file_path: str) -> dict:
    """Extract all tables from a PDF as JSON. Use when user wants structured data from a PDF."""
    all_tables = {}
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            if tables:
                all_tables[f"page_{i+1}"] = tables
    return {"file": file_path, "tables": all_tables}


@mcp.tool()
def html_scrape_url(url: str, max_chars: int = 5000) -> dict:
    """Fetch a live URL and return plain text. Use when user provides a URL to scrape."""
    resp = requests.get(url, timeout=30, headers={"User-Agent": "MCP-Bot/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return {"url": url, "title": soup.title.string if soup.title else None,
            "text": text[:max_chars], "truncated": len(text) > max_chars}


if __name__ == "__main__":
    # FastMCP creates POST /mcp only — no Starlette wiring needed
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
```

### claude_desktop_config.json — Streamable HTTP remote

```json
{
  "mcpServers": {
    "remote-pdf-tools": {
      "url": "http://192.168.1.100:8080/mcp",
      "headers": { "Authorization": "Bearer your-token" }
    }
  }
}
```

### Python app client — Streamable HTTP

```python
import asyncio
from fastmcp import Client

async def run():
    # /mcp in URL → FastMCP Client auto detects Streamable HTTP transport
    async with Client("http://192.168.1.100:8080/mcp") as client:
        result = await client.call_tool("pdf_extract_text", {"file_path": "/tmp/report.pdf"})
        print(result.content[0].text)

asyncio.run(run())
```

---

## Part 4: Orchestration Layer

### What is the Orchestration Layer?

The orchestration layer is the part of your app that sits **between the LLM and all MCP servers**.
It has one job: when the LLM says "call tool X", figure out which MCP server has tool X and call it.

```
Without orchestration layer:
  LLM says "call pdf_extract_text"
  → who handles this? your code has no idea.

With orchestration layer:
  LLM says "call pdf_extract_text"
  → orchestration layer looks up registry
  → finds pdf_client → calls http://192.168.1.100:8080/mcp
  → returns result to LLM
```

The orchestration layer is also called:
- **MCP Host** — in official MCP spec terminology
- **Agent loop** — in LangChain / LangGraph terminology
- **Tool router** — in general agentic AI terminology
- **Orchestrator** — in multi-agent system terminology

### Orchestration Layer Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER (your app)                       │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  TOOL REGISTRY  (built at startup by connecting to all MCP servers)│  │
│  │                                                                    │  │
│  │  "pdf_extract_text"   → FastMCP Client → http://host1:8080/mcp   │  │
│  │  "pdf_extract_tables" → FastMCP Client → http://host1:8080/mcp   │  │
│  │  "html_scrape_url"    → FastMCP Client → http://host2:8081/mcp   │  │
│  │  "html_to_text"       → FastMCP Client → http://host2:8081/mcp   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  AGENTIC LOOP                                                      │  │
│  │                                                                    │  │
│  │  1. Pass all tool names + schemas to LLM (Ollama)                 │  │
│  │  2. LLM picks a tool name                                         │  │
│  │  3. Registry lookup: tool name → correct MCP Client               │  │
│  │  4. Call tool on that MCP server                                  │  │
│  │  5. Return result to LLM                                          │  │
│  │  6. Repeat until LLM gives final answer                           │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────┬───────────────────────────────────────┬───────────────────────────┘
       │                                       │
       ▼                                       ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   OLLAMA    │     │ MCP SERVER 1 │     │ MCP SERVER 2 │
│ :11434      │     │ :8080/mcp    │     │ :8081/mcp    │
│             │     │              │     │              │
│ Sees only   │     │pdf_extract_  │     │html_scrape_  │
│ tool NAMES  │     │  text        │     │  url         │
│ not URLs    │     │pdf_extract_  │     │html_to_text  │
│             │     │  tables      │     │              │
└─────────────┘     └──────────────┘     └──────────────┘
```

### Orchestration Layer — Full Code

```python
# orchestrator.py
# ─────────────────────────────────────────────────────────────────────────────
# This is the orchestration layer.
# It connects to all remote MCP servers, builds a tool registry,
# passes all tools to Ollama, and routes tool calls to the correct server.
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import ollama
from fastmcp import Client

# ── Remote MCP server URLs ────────────────────────────────────────────────────
MCP_SERVERS = {
    "pdf-server":  "http://192.168.1.100:8080/mcp",   # hosts pdf_extract_text, pdf_extract_tables
    "html-server": "http://192.168.1.101:8081/mcp",   # hosts html_scrape_url, html_to_text
}

OLLAMA_MODEL = "mistral"   # must support tool calling: mistral, llama3.1, qwen2.5


# ── Step 1: Build tool registry from all MCP servers ─────────────────────────
async def build_registry(server_urls: dict) -> tuple[dict, list]:
    """
    Connects to every MCP server, fetches their tools.
    Returns:
      tool_registry: { tool_name → FastMCP Client }
      ollama_tools:  [ { type, function: { name, description, parameters } } ]
    """
    tool_registry = {}   # maps tool name → Client that has it
    ollama_tools  = []   # all tools in Ollama format for LLM

    for server_label, url in server_urls.items():
        client = Client(url)                           # FastMCP Client — auto detects transport from /mcp
        await client.__aenter__()                      # open connection

        tools = await client.list_tools()              # MCP CALL: fetch tool list from this server
        print(f"[Orchestrator] {server_label} tools: {[t.name for t in tools]}")

        for tool in tools:
            tool_registry[tool.name] = client          # register: name → client

            ollama_tools.append({                      # add to combined list for Ollama
                "type": "function",
                "function": {
                    "name":        tool.name,
                    "description": tool.description,
                    "parameters":  tool.parameters     # FastMCP exposes JSON schema directly
                }
            })

    return tool_registry, ollama_tools


# ── Step 2: Route a tool call to the correct MCP server ──────────────────────
async def route_tool_call(tool_name: str, tool_args: dict, tool_registry: dict) -> str:
    """
    Orchestration routing:
    Ollama said call 'html_scrape_url' → look up registry → find html-server client
    → call tool on that server → return result string.

    Ollama never knows the URL. Only the orchestrator knows.
    """
    client = tool_registry.get(tool_name)
    if not client:
        return f"ERROR: No MCP server registered for tool '{tool_name}'"

    print(f"[Orchestrator] Routing '{tool_name}' → {client}")

    result = await client.call_tool(tool_name, tool_args)  # MCP CALL: execute on remote server
    return result.content[0].text


# ── Step 3: Agentic loop — LLM + orchestrated MCP tool calls ─────────────────
async def run(user_message: str):
    """
    Full orchestration loop:
    1. Connect to all MCP servers → build registry
    2. Pass all tool schemas to Ollama
    3. Ollama picks tool → orchestrator routes to correct MCP server
    4. Result fed back to Ollama → repeat until final answer
    """

    print(f"\n{'='*60}")
    print(f"User: {user_message}")
    print(f"{'='*60}")

    # Build registry: connects to all MCP servers at startup
    tool_registry, ollama_tools = await build_registry(MCP_SERVERS)
    print(f"\n[Orchestrator] Total tools available: {list(tool_registry.keys())}")

    # Conversation history
    messages = [{"role": "user", "content": user_message}]

    turn = 0
    while True:
        turn += 1
        print(f"\n[Orchestrator] ── Turn {turn} ──")

        # LLM CALL: Ollama sees all tool names (not URLs)
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            tools=ollama_tools
        )
        assistant_msg = response["message"]
        messages.append(assistant_msg)

        # No tool calls → Ollama gave final text answer
        if not assistant_msg.get("tool_calls"):
            print(f"\n{'='*60}")
            print(f"Final Answer:\n{assistant_msg['content']}")
            print(f"{'='*60}")
            return

        # Ollama requested tool calls → orchestrator routes each one
        for tc in assistant_msg["tool_calls"]:
            tool_name = tc["function"]["name"]
            tool_args = tc["function"]["arguments"]

            print(f"[Orchestrator] Ollama requested: '{tool_name}' args={tool_args}")

            # Route to correct MCP server — this is the orchestration
            result = await route_tool_call(tool_name, tool_args, tool_registry)
            print(f"[Orchestrator] Result: {result[:150]}")

            # Feed result back to Ollama
            messages.append({"role": "tool", "content": result})


asyncio.run(run("Scrape https://docs.python.org and summarize the main topics"))
```

---

## Side-by-Side Comparison — FastMCP

```
                    stdio                SSE                  Streamable HTTP
                    ─────                ───                  ───────────────
1-line use          Same machine only.   Remote over HTTP     Remote over HTTP.
                    No network.          but 2 endpoints.     1 endpoint only.
                    Scripts/local dev.   Legacy systems only. Use for everything new.

Server code         mcp.run(             mcp.run(             mcp.run(
                      "stdio")             "sse",               "streamable-http",
                                           port=8080)           port=8080)

Endpoints           none                 GET  /sse            POST /mcp
                                         POST /messages

Client URL          StdioServerParams    "http://host/sse"    "http://host/mcp"

claude config       command + args       url: ".../sse"       url: ".../mcp"

mcp.json useful?    Yes (Claude Desktop) Yes (Claude Desktop) Yes (Claude Desktop)
                    No (Python app)      No (Python app)      No (Python app)
```

---

## Quick Reference

```python
# ── Server ────────────────────────────────────────────────────────────────────
from fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool()
def my_tool(input: str) -> str:
    """Tool description — LLM reads this to decide when to call."""
    return f"result: {input}"

mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)


# ── Client ────────────────────────────────────────────────────────────────────
from fastmcp import Client
import asyncio

async def run():
    async with Client("http://localhost:8080/mcp") as client:
        result = await client.call_tool("my_tool", {"input": "hello"})
        print(result.content[0].text)

asyncio.run(run())
```

---

## requirements.txt

```
fastmcp>=2.0.0
ollama>=0.2.0
pdfplumber>=0.10.0
beautifulsoup4>=4.12.0
requests>=2.31.0
```
