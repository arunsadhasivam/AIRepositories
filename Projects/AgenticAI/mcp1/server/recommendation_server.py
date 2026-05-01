"""
mcp1/server/recommendation_server.py
--------------------------------------
FastMCP server that exposes 3 recommendation tools:
  - process_text
  - get_count
  - print_count_html

Runs on port 8001 via HTTP/SSE transport.

Also runs a lightweight aiohttp sidecar on port 8011 that serves:
  GET /.well-known/agent.json  → MCP1 agent card loaded from disk
  GET /config                  → MCP1 mcp_config.json loaded from disk

Why sidecar?
  FastMCP does not support custom HTTP routes in all versions.
  Rather than patching FastMCP internals, we run a tiny aiohttp server
  on a separate port (8011) for discovery endpoints only.
"""

import sys
import os
import json
import asyncio
import threading

# Add project root to path so we can import mcp1/tools
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastmcp import FastMCP
from aiohttp import web
from mcp1.tools.recommendation_tools import process_text, get_count, print_count_html

# ── Paths to config files ──────────────────────────────────────────────────────
_BASE = os.path.join(os.path.dirname(__file__), "..")

# mcp1/.well-known/agent.json  → A2A style discovery card
_AGENT_CARD_PATH = os.path.join(_BASE, ".well-known", "agent.json")

# mcp1/mcp_config.json         → MCP style server + tool schema config
_MCP_CONFIG_PATH = os.path.join(_BASE, "mcp_config.json")

# Load both files once at startup so every request just returns cached dict
with open(_AGENT_CARD_PATH) as f:
    _AGENT_CARD = json.load(f)    # e.g. {"name": "RecommendationMCPServer", "skills": [...]}

with open(_MCP_CONFIG_PATH) as f:
    _MCP_CONFIG = json.load(f)    # e.g. {"server": {...}, "tools": [...]}

print(f"[MCP1] Loaded agent card: {_AGENT_CARD['name']}")
print(f"[MCP1] Loaded mcp_config: {_MCP_CONFIG['server']['name']}")

_MCP_SERVER2_URL = _MCP_CONFIG['delegates_to']['mcp2']['endpoint']

# ── FastMCP server (port 8001) ─────────────────────────────────────────────────
mcp = FastMCP("recommendation-server")


@mcp.tool()
def tool_process_text(text: str) -> dict:
    """
    Tool 1: Process raw text → word frequency dict.
    Example input: "apple banana apple"
    Example output: {"apple": 2, "banana": 1}
    """
    # Delegate to the actual logic in tools/recommendation_tools.py
    return process_text(text)


@mcp.tool()
def tool_get_count(word_counts: dict) -> dict:
    """
    Tool 2: Given word frequency dict → return total and unique word counts.
    Example input: {"apple": 2, "banana": 1}
    Example output: {"total_words": 3, "unique_words": 2}
    """
    # Delegate to tools layer
    return get_count(word_counts)


@mcp.tool()
def tool_print_count_html(word_counts: dict) -> str:
    """
    Tool 3: Given word frequency dict → return HTML table string.
    """
    # Delegate to tools layer, returns full HTML string
    return print_count_html(word_counts)


@mcp.tool()
def tool_print_count_html(word_counts: dict) -> str:
    """
    Tool 3: Given word frequency dict → return HTML table string.
    """
    # Delegate to tools layer, returns full HTML string
    return print_count_html(word_counts)

 
@mcp.tool()
async def tool_add_from_mcp2(a: float, b: float) -> float:
    """
    Tool 5: MCP1 calls MCP2 multiply tool directly via MCP client.
    MCP1 → MCP2 (port 8002) → returns a * b
    No A2A involved — pure MCP client call.
    """
    from fastmcp import Client
 
    # Connect directly to MCP2 math server
    async with Client(_MCP_SERVER2_URL) as client:
        result = await client.call_tool("tool_add", {"a": a, "b": b})
 
    raw = result.content[0].text
    try:
        return json.loads(raw)
    except Exception:
        return raw




# ── Aiohttp sidecar (port 8011) ────────────────────────────────────────────────
# Serves agent.json and mcp_config.json for discovery

async def handle_agent_card(request):
    """
    GET /.well-known/agent.json
    Returns the A2A-style agent card loaded from mcp1/.well-known/agent.json
    """
    return web.json_response(_AGENT_CARD)   # serve cached dict as JSON


async def handle_mcp_config(request):
    """
    GET /config
    Returns the MCP-style server config loaded from mcp1/mcp_config.json
    """
    return web.json_response(_MCP_CONFIG)   # serve cached dict as JSON


def run_sidecar():
    """
    Run the aiohttp sidecar in its own thread with its own event loop.
    This avoids conflict with FastMCP's event loop on the main thread.
    """
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Build aiohttp app with discovery routes
    app = web.Application()
    app.router.add_get("/.well-known/agent.json", handle_agent_card)  # A2A discovery
    app.router.add_get("/config", handle_mcp_config)                   # MCP config

    # Run sidecar on port 8011
    print("[MCP1 Sidecar] Discovery server starting on http://localhost:8011")
    print("[MCP1 Sidecar]   GET http://localhost:8011/.well-known/agent.json")
    print("[MCP1 Sidecar]   GET http://localhost:8011/config")
    web.run_app(app, host="0.0.0.0", port=8011, loop=loop)


if __name__ == "__main__":
    # Start sidecar in background thread so it doesn't block FastMCP
    sidecar_thread = threading.Thread(target=run_sidecar, daemon=True)
    sidecar_thread.start()   # runs aiohttp on port 8011 in background

    # Start FastMCP on port 8001 (blocks main thread)
    print("[MCP1] Recommendation server starting on http://localhost:8001/mcp")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)