# Claude Desktop Config + MCP Transport Types — Complete Guide

---

## Part 1: Claude Desktop Config File

### Exact File Name and Location

```
The file is NOT called mcp.json.
The file is NOT called mcp1.json.
Claude Desktop accepts ONLY one exact filename:

  claude_desktop_config.json
```

| OS | Exact File Path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

```
%APPDATA% on Windows typically resolves to:
C:\Users\YourName\AppData\Roaming\Claude\claude_desktop_config.json
```

Any other filename (`mcp.json`, `mcp1.json`, `config.json`) is completely ignored by Claude Desktop.

---

### Full claude_desktop_config.json Format

```json
{
  "mcpServers": {

    "pdf-tools": {
      "command": "python",
      "args": ["C:/WorkSpace/servers/pdf_server.py"],
      "env": {
        "PDF_TEMP_DIR": "C:/tmp/pdf"
      }
    },

    "remote-html-tools": {
      "url": "http://192.168.1.100:8081/sse",
      "headers": {
        "Authorization": "Bearer your-token-here"
      }
    }

  }
}
```

The key inside `mcpServers` (like `"pdf-tools"`, `"remote-html-tools"`) is just a label you choose. It can be anything. Claude Desktop shows it in the UI.

---

## Part 2: MCP Transport Types

There are **3 transport types** in MCP. SSE is not the only one.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    3 MCP TRANSPORT TYPES                            │
├──────────────────┬──────────────────┬───────────────────────────────┤
│   stdio          │   SSE            │   Streamable HTTP             │
│   (local only)   │   (remote/local) │   (remote, newest standard)   │
├──────────────────┼──────────────────┼───────────────────────────────┤
│ Launched as      │ Runs as HTTP     │ Runs as HTTP server           │
│ child process    │ server with      │ Single endpoint for           │
│ stdin/stdout     │ two endpoints:   │ everything:                   │
│                  │ GET /sse         │ POST /mcp                     │
│                  │ POST /messages   │                               │
├──────────────────┼──────────────────┼───────────────────────────────┤
│ Use when:        │ Use when:        │ Use when:                     │
│ Same machine     │ Remote server,   │ Remote server,                │
│ No firewall      │ older MCP SDK    │ MCP SDK >= 1.0                │
│                  │                  │ Preferred for new projects    │
└──────────────────┴──────────────────┴───────────────────────────────┘
```

---

## Transport 1: stdio (Local Only)

### How it works

```
Claude Desktop / Your App
        │
        │  spawns as child process
        ▼
  python pdf_server.py
        │
   communicates via
   stdin / stdout
   (no HTTP, no port)
```

No HTTP server needed. No port. No SSE. MCP messages go through standard input/output of the process.

### Server code — stdio

```python
# pdf_server_stdio.py
# No HTTP server needed. No uvicorn. No port.
# Claude Desktop spawns this as a child process.

import asyncio
import json
import pdfplumber
from mcp.server import Server
from mcp.server.stdio import stdio_server          # ← stdio transport
from mcp.types import Tool, TextContent

mcp = Server("pdf-tools-stdio")

@mcp.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="pdf_extract_text",
            description="Extract plain text from a PDF file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"}
                },
                "required": ["file_path"]
            }
        )
    ]

@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "pdf_extract_text":
        with pdfplumber.open(arguments["file_path"]) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        return [TextContent(type="text", text=json.dumps({"text": text}))]
    return [TextContent(type="text", text=json.dumps({"error": "unknown tool"}))]

async def main():
    # stdio_server() reads from stdin, writes to stdout
    # No HTTP. No port. Claude Desktop pipes directly.
    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(read_stream, write_stream, mcp.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

### claude_desktop_config.json — stdio

```json
{
  "mcpServers": {
    "pdf-tools": {
      "command": "python",
      "args": ["C:/WorkSpace/servers/pdf_server_stdio.py"],
      "env": {
        "PYTHONPATH": "C:/WorkSpace"
      }
    }
  }
}
```

Claude Desktop reads this, spawns `python pdf_server_stdio.py` as a child process, and pipes MCP messages through stdin/stdout. No URL needed. No HTTP.

### Python app — stdio client

```python
# If your own Python app (not Claude Desktop) uses a stdio MCP server
import asyncio
from mcp import ClientSession
from mcp.client.stdio import stdio_client          # ← stdio client
from mcp import StdioServerParameters

async def run():
    # Tell the client how to launch the server process
    server_params = StdioServerParameters(
        command="python",
        args=["C:/WorkSpace/servers/pdf_server_stdio.py"],
        env=None
    )

    # stdio_client spawns the process and pipes to it
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool(
                "pdf_extract_text",
                {"file_path": "C:/tmp/report.pdf"}
            )
            print(result.content[0].text)

asyncio.run(run())
```

---

## Transport 2: SSE (HTTP — Remote or Local)

### How it works

```
Your App / Claude Desktop
        │
        │  HTTP connection
        │
        ├── GET  /sse       ← open persistent SSE stream
        └── POST /messages  ← send tool calls here
                │
                ▼
        MCP Server (any machine)
        running uvicorn on a port
```

Two separate HTTP endpoints required on the server. The SSE stream stays open for the lifetime of the session.

### Server code — SSE

```python
# pdf_server_sse.py
# Runs as HTTP server. Reachable from any machine.
# TWO endpoints required:
#   GET  /sse       → opens SSE stream
#   POST /messages  → receives tool calls

import asyncio
import json
import uvicorn
import pdfplumber
from mcp.server import Server
from mcp.server.sse import SseServerTransport      # ← SSE transport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request

mcp = Server("pdf-tools-sse")

@mcp.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="pdf_extract_text",
            description="Extract plain text from a PDF file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"}
                },
                "required": ["file_path"]
            }
        )
    ]

@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "pdf_extract_text":
        with pdfplumber.open(arguments["file_path"]) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        return [TextContent(type="text", text=json.dumps({"text": text}))]
    return [TextContent(type="text", text=json.dumps({"error": "unknown tool"}))]

# ── SSE transport setup ───────────────────────────────────────────────────────
# SseServerTransport("/messages") tells it:
#   tool call results go back via SSE stream
#   tool call requests come in via POST /messages
sse = SseServerTransport("/messages")               # ← param is the POST endpoint path

async def handle_sse(request: Request):
    # Client hits GET /sse → this opens the persistent SSE stream
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp.run(streams[0], streams[1], mcp.create_initialization_options())

async def handle_messages(request: Request):
    # Client hits POST /messages → this receives the tool call and executes it
    await sse.handle_post_message(request.scope, request.receive, request._send)

http_app = Starlette(routes=[
    Route("/sse",      endpoint=handle_sse),
    Route("/messages", endpoint=handle_messages, methods=["POST"]),
])

if __name__ == "__main__":
    uvicorn.run(http_app, host="0.0.0.0", port=8080)
```

### claude_desktop_config.json — SSE remote server

```json
{
  "mcpServers": {
    "remote-pdf-tools": {
      "url": "http://192.168.1.100:8080/sse",
      "headers": {
        "Authorization": "Bearer your-token"
      }
    }
  }
}
```

No `command` field. Just `url` pointing to the remote SSE endpoint.

### Python app — SSE client

```python
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client              # ← SSE client

async def run():
    async with sse_client(
        url="http://192.168.1.100:8080/sse",       # ← full remote URL required
        headers={"Authorization": "Bearer token"}
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "pdf_extract_text",
                {"file_path": "/remote/path/report.pdf"}
            )
            print(result.content[0].text)

asyncio.run(run())
```

---

## Transport 3: Streamable HTTP (Newest — Recommended for New Projects)

### How it works

```
Your App / Claude Desktop
        │
        │  HTTP connection
        │
        └── POST /mcp      ← single endpoint for everything
                            (list tools, call tools, all via this one endpoint)
                │
                ▼
        MCP Server (any machine)
```

One endpoint only. Simpler than SSE. Supported from MCP SDK 1.0+. This is the direction MCP is moving toward.

### Server code — Streamable HTTP

```python
# pdf_server_streamable.py
# ONE endpoint only: POST /mcp
# Simpler than SSE (no separate /sse + /messages split)
# Requires: mcp >= 1.0.0

import json
import uvicorn
import pdfplumber
from mcp.server import Server
from mcp.server.streamable_http import StreamableHTTPServerTransport  # ← new transport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request

mcp = Server("pdf-tools-streamable")

@mcp.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="pdf_extract_text",
            description="Extract plain text from a PDF file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"}
                },
                "required": ["file_path"]
            }
        )
    ]

@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "pdf_extract_text":
        with pdfplumber.open(arguments["file_path"]) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        return [TextContent(type="text", text=json.dumps({"text": text}))]
    return [TextContent(type="text", text=json.dumps({"error": "unknown tool"}))]

# ── Streamable HTTP transport setup ──────────────────────────────────────────
# Only ONE endpoint needed: POST /mcp
# No separate /sse GET endpoint. No /messages POST endpoint.
transport = StreamableHTTPServerTransport(mcp_endpoint="/mcp")  # ← single endpoint path

async def handle_mcp(request: Request):
    async with transport.connect(request.scope, request.receive, request._send) as streams:
        await mcp.run(streams[0], streams[1], mcp.create_initialization_options())

http_app = Starlette(routes=[
    Route("/mcp", endpoint=handle_mcp, methods=["POST"]),  # ← single route only
])

if __name__ == "__main__":
    uvicorn.run(http_app, host="0.0.0.0", port=8080)
```

### claude_desktop_config.json — Streamable HTTP

```json
{
  "mcpServers": {
    "remote-pdf-tools": {
      "url": "http://192.168.1.100:8080/mcp",
      "headers": {
        "Authorization": "Bearer your-token"
      }
    }
  }
}
```

Same format as SSE in config. Claude Desktop detects the transport type automatically.

### Python app — Streamable HTTP client

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client    # ← new client

async def run():
    async with streamable_http_client(
        url="http://192.168.1.100:8080/mcp",       # ← single endpoint URL
        headers={"Authorization": "Bearer token"}
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "pdf_extract_text",
                {"file_path": "/remote/path/report.pdf"}
            )
            print(result.content[0].text)

asyncio.run(run())
```

---

## Side-by-Side Comparison

```
                stdio              SSE                 Streamable HTTP
                ─────              ───                 ───────────────
Server runs     same machine       any machine         any machine
as              child process      HTTP server         HTTP server

Server import   stdio_server()     SseServerTransport  StreamableHTTPServerTransport

HTTP endpoints  none               GET  /sse           POST /mcp
                                   POST /messages      (one endpoint only)

Client import   stdio_client()     sse_client()        streamable_http_client()

Config in       command + args     url: ".../sse"      url: ".../mcp"
claude config

Auth            none               headers: {}         headers: {}

MCP SDK req     any                any                 >= 1.0.0

Best for        local dev,         remote, legacy      remote, new projects
                scripts            compatibility
```

---

## Quick Answer to Your Questions

**Q: Does mcp.json work or must it be a specific name?**
Only `claude_desktop_config.json` works. Any other name is ignored.

**Q: Is SSE the only way to invoke remote MCP?**
No. Three options:
- `stdio` — local only, no HTTP
- `SSE` — remote, two endpoints (`GET /sse` + `POST /messages`)
- `Streamable HTTP` — remote, one endpoint (`POST /mcp`), preferred for new projects

**Q: Do I set any special param on the server to enable SSE?**
Yes. On the server you import `SseServerTransport` and create two routes.
On the client you import `sse_client` and pass the full remote URL.
Without both sides using the matching transport, connection fails.
