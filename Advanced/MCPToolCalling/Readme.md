# Remote MCP + Ollama Tool Call — Complete Guide

## First: Clear the Confusion on Tool Naming

This is what confuses most people. Let me be 100% clear.

```
QUESTION: When LLM calls a tool, does it use:

  OPTION A:  "http://localhost:8080/mcp1/pdf-tool"   ← full URL?
  OPTION B:  "pdf_extract_text"                      ← just the tool name?

ANSWER:  OPTION B. Always just the tool name.
```

The LLM **never knows** the URL of the MCP server.
The LLM only sees tool names and descriptions.
YOUR APP is responsible for knowing which MCP server hosts which tool,
and routing the call to the right server URL.

```
┌────────────────────────────────────────────────────────────────────┐
│                        WHAT LLM SEES                               │
│                                                                     │
│   tools = [                                                        │
│     { name: "pdf_extract_text",  description: "Extract PDF..." }, │
│     { name: "html_scrape_url",   description: "Scrape URL..."  }, │
│   ]                                                                │
│                                                                     │
│   LLM picks:  "pdf_extract_text"   ← just the name               │
│   LLM has NO idea about:  http://localhost:8080/sse               │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│                        WHAT YOUR APP DOES                          │
│                                                                     │
│   LLM said: call "pdf_extract_text"                               │
│   Your app looks up: which MCP server has this tool?              │
│   Your app knows:    pdf_extract_text → http://localhost:8080/sse │
│   Your app calls:    POST http://localhost:8080/messages          │
└────────────────────────────────────────────────────────────────────┘
```

---

## Architecture: Multiple MCP Servers + Ollama

```
┌──────────────────────────────────────────────────────────────────────┐
│                        YOUR APP (app.py)                             │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  TOOL REGISTRY  (your app maintains this)                   │    │
│  │                                                             │    │
│  │  "pdf_extract_text"  → session_A (mcp-server-1:8080)       │    │
│  │  "pdf_extract_tables"→ session_A (mcp-server-1:8080)       │    │
│  │  "html_scrape_url"   → session_B (mcp-server-2:8081)       │    │
│  │  "html_to_text"      → session_B (mcp-server-2:8081)       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  Step 1: Connect to all MCP servers, fetch all tools               │
│  Step 2: Pass all tool names+schemas to Ollama                     │
│  Step 3: Ollama says "call pdf_extract_text"                       │
│  Step 4: App looks up registry → routes to mcp-server-1:8080      │
│  Step 5: Send result back to Ollama                                │
└──────┬──────────────────────┬───────────────────────┬──────────────┘
       │                      │                       │
       ▼                      ▼                       ▼
┌─────────────┐      ┌─────────────────┐     ┌──────────────┐
│   OLLAMA    │      │  MCP SERVER 1   │     │ MCP SERVER 2 │
│ :11434      │      │  :8080          │     │ :8081        │
│             │      │                 │     │              │
│ mistral     │      │ pdf_extract_text│     │html_scrape   │
│ llama3.1    │      │ pdf_extract_    │     │html_to_text  │
│             │      │   tables        │     │              │
└─────────────┘      └─────────────────┘     └──────────────┘
```

---

## Project Structure

```
project/
├── servers/
│   ├── pdf_server.py        ← MCP Server 1 (runs on :8080)  PDF tools
│   └── html_server.py       ← MCP Server 2 (runs on :8081)  HTML tools
├── client/
│   └── app.py               ← Your app: connects MCP + Ollama
└── requirements.txt
```

---

## Part 1: PDF MCP Server (runs on port 8080)

```python
# servers/pdf_server.py
# Runs at: http://localhost:8080
# Exposes:  pdf_extract_text, pdf_extract_tables
# Your app connects here via:  http://localhost:8080/sse

import json
import uvicorn
import pdfplumber
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request

# ── Create MCP server ─────────────────────────────────────────────────────────
mcp = Server("pdf-server")

# ── Declare tools ─────────────────────────────────────────────────────────────
@mcp.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="pdf_extract_text",
            description="Extract plain text from a PDF file. Use when user wants to read or summarize a PDF.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the PDF file"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="pdf_extract_tables",
            description="Extract all tables from a PDF file as JSON. Use when user wants structured data from a PDF.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the PDF file"
                    }
                },
                "required": ["file_path"]
            }
        )
    ]

# ── Execute tools ─────────────────────────────────────────────────────────────
@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:

    if name == "pdf_extract_text":
        file_path = arguments["file_path"]
        pages_text = {}
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                pages_text[f"page_{i+1}"] = page.extract_text() or ""
        result = {"file": file_path, "pages": pages_text}
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "pdf_extract_tables":
        file_path = arguments["file_path"]
        all_tables = {}
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if tables:
                    all_tables[f"page_{i+1}"] = tables
        result = {"file": file_path, "tables": all_tables}
        return [TextContent(type="text", text=json.dumps(result))]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

# ── SSE transport wiring ──────────────────────────────────────────────────────
sse = SseServerTransport("/messages")

async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp.run(streams[0], streams[1], mcp.create_initialization_options())

async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

http_app = Starlette(routes=[
    Route("/sse",      endpoint=handle_sse),
    Route("/messages", endpoint=handle_messages, methods=["POST"]),
])

if __name__ == "__main__":
    uvicorn.run(http_app, host="0.0.0.0", port=8080)   # ← runs on port 8080
```

---

## Part 2: HTML MCP Server (runs on port 8081)

```python
# servers/html_server.py
# Runs at: http://localhost:8081
# Exposes:  html_scrape_url, html_to_text
# Your app connects here via:  http://localhost:8081/sse

import json
import uvicorn
import requests
from bs4 import BeautifulSoup
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request

mcp = Server("html-server")

@mcp.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="html_scrape_url",
            description="Fetch a live URL and return its plain text content. Use when user provides a URL to scrape.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL starting with http:// or https://"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="html_to_text",
            description="Convert a raw HTML string to clean plain text. Use when you already have HTML content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "html": {
                        "type": "string",
                        "description": "Raw HTML string to convert"
                    }
                },
                "required": ["html"]
            }
        )
    ]

@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:

    if name == "html_scrape_url":
        url = arguments["url"]
        resp = requests.get(url, timeout=30, headers={"User-Agent": "MCP-Bot/1.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)[:5000]
        result = {"url": url, "title": soup.title.string if soup.title else None, "text": text}
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "html_to_text":
        html = arguments["html"]
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        result = {"text": text, "char_count": len(text)}
        return [TextContent(type="text", text=json.dumps(result))]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

sse = SseServerTransport("/messages")

async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp.run(streams[0], streams[1], mcp.create_initialization_options())

async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

http_app = Starlette(routes=[
    Route("/sse",      endpoint=handle_sse),
    Route("/messages", endpoint=handle_messages, methods=["POST"]),
])

if __name__ == "__main__":
    uvicorn.run(http_app, host="0.0.0.0", port=8081)   # ← runs on port 8081
```

---

## Part 3: Your App — Ollama + Multi-MCP Routing

```python
# client/app.py
# ─────────────────────────────────────────────────────────────────────────────
# YOUR APPLICATION
#
# Connects to:
#   MCP Server 1: http://localhost:8080/sse  (PDF tools)
#   MCP Server 2: http://localhost:8081/sse  (HTML tools)
#   Ollama:       http://localhost:11434     (local LLM)
#
# KEY POINT:
#   Ollama only sees tool NAMES like "pdf_extract_text"
#   Your app maintains a registry: tool name → which MCP session to use
#   When Ollama says "call pdf_extract_text", app looks up registry
#   and calls the right MCP server
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import json
import ollama                               # pip install ollama
from mcp import ClientSession
from mcp.client.sse import sse_client

# ── MCP server URLs ───────────────────────────────────────────────────────────
PDF_MCP_URL  = "http://localhost:8080/sse"  # PDF server SSE endpoint
HTML_MCP_URL = "http://localhost:8081/sse"  # HTML server SSE endpoint

# ── Ollama config ─────────────────────────────────────────────────────────────
OLLAMA_MODEL = "mistral"                    # must support tool calling
                                            # alternatives: llama3.1, qwen2.5


# ═════════════════════════════════════════════════════════════════════════════
# SECTION A: MCP CALLS
# Talk to remote MCP servers — nothing to do with Ollama here
# ═════════════════════════════════════════════════════════════════════════════

async def mcp_fetch_tools(session: ClientSession, server_label: str) -> list[dict]:
    """
    MCP CALL: Ask one MCP server what tools it has.
    Returns tools in Ollama format.

    Ollama tool format:
    {
      "type": "function",
      "function": {
        "name": "pdf_extract_text",
        "description": "...",
        "parameters": { ...json schema... }
      }
    }
    """
    print(f"[MCP] Fetching tools from {server_label}...")
    response = await session.list_tools()

    ollama_tools = []
    for tool in response.tools:
        # Convert MCP format → Ollama format
        # MCP:    { name, description, inputSchema }
        # Ollama: { type: "function", function: { name, description, parameters } }
        ollama_tools.append({
            "type": "function",
            "function": {
                "name":        tool.name,
                "description": tool.description,
                "parameters":  tool.inputSchema   # inputSchema IS the JSON schema
            }
        })

    print(f"[MCP] Got {len(ollama_tools)} tools from {server_label}: "
          f"{[t['function']['name'] for t in ollama_tools]}")
    return ollama_tools


async def mcp_execute_tool(
    tool_name: str,
    tool_args: dict,
    tool_registry: dict          # maps tool_name → ClientSession
) -> str:
    """
    MCP CALL: Execute a specific tool on the correct MCP server.

    tool_registry tells us:
      "pdf_extract_text"  → session connected to :8080
      "html_scrape_url"   → session connected to :8081

    Ollama told us to call "pdf_extract_text"
    We look up registry → find session for :8080
    We POST the tool call to :8080/messages
    Result comes back via SSE stream
    """
    # ── Look up which MCP server has this tool ────────────────────────────────
    session = tool_registry.get(tool_name)
    if not session:
        return json.dumps({"error": f"No MCP server found for tool: {tool_name}"})

    print(f"\n[MCP] Executing tool '{tool_name}'")
    print(f"[MCP] Arguments: {json.dumps(tool_args, indent=2)}")

    # ── Call the tool on the correct MCP server ───────────────────────────────
    # Internally this does: POST http://localhost:808x/messages
    # with body: { method: "tools/call", params: { name, arguments } }
    result = await session.call_tool(tool_name, tool_args)

    # Extract text from result content blocks
    output = "\n".join(
        block.text for block in result.content if hasattr(block, "text")
    )

    print(f"[MCP] Tool result: {output[:200]}{'...' if len(output) > 200 else ''}")
    return output


# ═════════════════════════════════════════════════════════════════════════════
# SECTION B: OLLAMA CALLS
# Talk to local Ollama — nothing to do with MCP connection here
# ═════════════════════════════════════════════════════════════════════════════

def ollama_chat(messages: list[dict], tools: list[dict]) -> dict:
    """
    LLM CALL: Send conversation + available tools to Ollama.

    Ollama endpoint called internally: POST http://localhost:11434/api/chat

    Returns Ollama response dict. Two possible outcomes:
      1. response has tool_calls  → Ollama wants to call a tool
      2. response has no tool_calls → Ollama gave final text answer
    """
    print(f"\n[OLLAMA] Calling model '{OLLAMA_MODEL}'...")

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        tools=tools            # ← all tools from all MCP servers go here
                               # Ollama sees: pdf_extract_text, html_scrape_url etc.
                               # Ollama does NOT see: localhost:8080 or localhost:8081
    )

    # response["message"] contains:
    #   { "role": "assistant",
    #     "content": "some text",           ← final answer (if no tool call)
    #     "tool_calls": [                   ← tool call request (if LLM wants a tool)
    #       { "function": {
    #           "name": "pdf_extract_text",
    #           "arguments": { "file_path": "/tmp/doc.pdf" }
    #       }}
    #     ]
    #   }

    has_tool_calls = bool(response["message"].get("tool_calls"))
    print(f"[OLLAMA] Response has tool_calls: {has_tool_calls}")
    return response


def ollama_extract_tool_calls(response: dict) -> list[dict]:
    """
    Parse Ollama response to get list of tool calls.
    Each item: { name: str, arguments: dict }
    """
    tool_calls = []
    for tc in response["message"].get("tool_calls", []):
        tool_calls.append({
            "name":      tc["function"]["name"],       # e.g. "pdf_extract_text"
            "arguments": tc["function"]["arguments"]   # e.g. {"file_path": "/tmp/x.pdf"}
        })
    return tool_calls


def ollama_extract_text(response: dict) -> str:
    """Extract final text answer from Ollama response."""
    return response["message"].get("content", "")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION C: AGENTIC LOOP
# Connects MCP and Ollama. Loops until Ollama gives final answer.
# ═════════════════════════════════════════════════════════════════════════════

async def run(user_message: str):
    """
    Full flow:
    1. Connect to both MCP servers
    2. Fetch tools from each → build combined tool list + registry
    3. Pass all tools to Ollama
    4. Loop: Ollama picks tool → app routes to right MCP server → result back to Ollama
    5. Ollama gives final answer
    """

    print(f"\n{'='*60}")
    print(f"User: {user_message}")
    print(f"{'='*60}")

    # tool_registry maps:  tool_name (str) → ClientSession
    # This is how your app knows WHICH MCP server to call for each tool
    tool_registry = {}

    # all_tools is the combined list passed to Ollama
    all_tools = []

    # ── Step 1: Connect to MCP Server 1 (PDF tools on :8080) ─────────────────
    async with sse_client(url=PDF_MCP_URL) as (r1, w1):
        async with ClientSession(r1, w1) as pdf_session:
            await pdf_session.initialize()

            # Fetch PDF tools
            pdf_tools = await mcp_fetch_tools(pdf_session, "PDF-Server(:8080)")

            # Register: each PDF tool name → pdf_session
            for tool in pdf_tools:
                tool_name = tool["function"]["name"]
                tool_registry[tool_name] = pdf_session
                # tool_registry now has:
                #   "pdf_extract_text"   → pdf_session (points to :8080)
                #   "pdf_extract_tables" → pdf_session (points to :8080)

            all_tools.extend(pdf_tools)

            # ── Step 2: Connect to MCP Server 2 (HTML tools on :8081) ─────────
            async with sse_client(url=HTML_MCP_URL) as (r2, w2):
                async with ClientSession(r2, w2) as html_session:
                    await html_session.initialize()

                    # Fetch HTML tools
                    html_tools = await mcp_fetch_tools(html_session, "HTML-Server(:8081)")

                    # Register: each HTML tool name → html_session
                    for tool in html_tools:
                        tool_name = tool["function"]["name"]
                        tool_registry[tool_name] = html_session
                        # tool_registry now has:
                        #   "html_scrape_url" → html_session (points to :8081)
                        #   "html_to_text"    → html_session (points to :8081)

                    all_tools.extend(html_tools)

                    # ── At this point tool_registry looks like: ────────────────
                    # {
                    #   "pdf_extract_text":   <Session → :8080>,
                    #   "pdf_extract_tables": <Session → :8080>,
                    #   "html_scrape_url":    <Session → :8081>,
                    #   "html_to_text":       <Session → :8081>,
                    # }
                    #
                    # Ollama sees only the names in all_tools.
                    # It picks a name. App uses registry to find right session.

                    print(f"\n[APP] Total tools available to Ollama: {len(all_tools)}")
                    print(f"[APP] Tool registry: {list(tool_registry.keys())}")

                    # ── Step 3: Build conversation history ─────────────────────
                    messages = [
                        {"role": "user", "content": user_message}
                    ]

                    # ── Step 4: Agentic loop ────────────────────────────────────
                    turn = 0
                    while True:
                        turn += 1
                        print(f"\n[APP] ── Turn {turn} ──────────────────────────")

                        # ── OLLAMA CALL: send messages + all tools ────────────
                        response = ollama_chat(messages, all_tools)
                        assistant_message = response["message"]

                        # Add Ollama's response to history
                        messages.append(assistant_message)

                        # ── CASE A: No tool calls → Ollama gave final answer ──
                        if not assistant_message.get("tool_calls"):
                            final_answer = ollama_extract_text(response)
                            print(f"\n[APP] Done after {turn} turns.")
                            print(f"\n{'='*60}")
                            print(f"Final Answer:\n{final_answer}")
                            print(f"{'='*60}")
                            return final_answer

                        # ── CASE B: Ollama wants to call tools ────────────────
                        tool_calls = ollama_extract_tool_calls(response)
                        print(f"[APP] Ollama requested tools: "
                              f"{[tc['name'] for tc in tool_calls]}")

                        for tc in tool_calls:
                            tool_name = tc["name"]      # e.g. "html_scrape_url"
                            tool_args = tc["arguments"] # e.g. {"url": "https://..."}

                            # ── MCP CALL: route to correct MCP server ─────────
                            # App looks up: "html_scrape_url" → html_session → :8081
                            # App does NOT call :8080 (that would be wrong server)
                            result = await mcp_execute_tool(
                                tool_name,
                                tool_args,
                                tool_registry   # ← routing map lives here
                            )

                            # Add tool result to conversation history
                            # Ollama reads this in next turn to continue reasoning
                            messages.append({
                                "role":    "tool",
                                "content": result
                            })

                        # Loop → Ollama will now read tool results and continue


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(run(
        "Scrape https://docs.python.org and summarize what you find"
    ))
```

---

## Exact Network Calls Happening Behind the Scenes

```
YOUR APP                    PDF MCP (:8080)     HTML MCP (:8081)     OLLAMA (:11434)
    │                            │                    │                    │
    │── GET /sse ───────────────►│                    │                    │
    │   (connect pdf session)    │                    │                    │
    │                            │                    │                    │
    │── GET /sse ────────────────────────────────────►│                    │
    │   (connect html session)   │                    │                    │
    │                            │                    │                    │
    │── list_tools() ───────────►│                    │                    │
    │◄── [pdf_extract_text,      │                    │                    │
    │     pdf_extract_tables] ───│                    │                    │
    │                            │                    │                    │
    │── list_tools() ────────────────────────────────►│                    │
    │◄── [html_scrape_url,       │                    │                    │
    │     html_to_text] ─────────────────────────────│                    │
    │                            │                    │                    │
    │── POST /api/chat ──────────────────────────────────────────────────►│
    │   tools: [pdf_extract_text,│                    │  (Ollama sees      │
    │           html_scrape_url, │                    │   only names,      │
    │           ...]             │                    │   no URLs)         │
    │◄── tool_use: "html_scrape_url" { url: "..." } ─────────────────────│
    │                            │                    │                    │
    │   (app looks up registry)  │                    │                    │
    │   "html_scrape_url" → :8081│                    │                    │
    │                            │                    │                    │
    │── POST /messages ──────────────────────────────►│                    │
    │   call html_scrape_url     │                    │                    │
    │◄── { text: "scraped..." } ─────────────────────│                    │
    │                            │                    │                    │
    │── POST /api/chat (with tool result) ───────────────────────────────►│
    │◄── "Here is the summary..." ───────────────────────────────────────│
```

---

## Tool Name vs URL — Final Summary

```
┌──────────────────────────────────────────────────────────────────┐
│  WHAT OLLAMA SEES          │  WHAT YOUR APP KNOWS               │
│  (just tool names)         │  (full routing map)                │
├──────────────────────────────────────────────────────────────────┤
│  "pdf_extract_text"        │  → POST http://localhost:8080/msg  │
│  "pdf_extract_tables"      │  → POST http://localhost:8080/msg  │
│  "html_scrape_url"         │  → POST http://localhost:8081/msg  │
│  "html_to_text"            │  → POST http://localhost:8081/msg  │
└──────────────────────────────────────────────────────────────────┘

Ollama calls:   "html_scrape_url"          ← just the name
App routes to:  http://localhost:8081/messages  ← full URL
```

The LLM (Ollama) never touches an MCP URL.
Your app's `tool_registry` dict is the bridge between the two worlds.

---

## How to Run

```bash
# Terminal 1: Start PDF MCP server
python servers/pdf_server.py
# Listening on http://localhost:8080

# Terminal 2: Start HTML MCP server
python servers/html_server.py
# Listening on http://localhost:8081

# Terminal 3: Make sure Ollama is running with a tool-capable model
ollama pull mistral
ollama serve
# Listening on http://localhost:11434

# Terminal 4: Run your app
python client/app.py
```

## requirements.txt

```
mcp>=1.0.0
ollama>=0.2.0
pdfplumber>=0.10.0
beautifulsoup4>=4.12.0
requests>=2.31.0
uvicorn>=0.24.0
starlette>=0.27.0
```
