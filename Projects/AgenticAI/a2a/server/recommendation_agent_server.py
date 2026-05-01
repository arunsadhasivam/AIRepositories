"""
a2a/server/recommendation_agent_server.py
-------------------------------------------
A2A Server: Google ADK Agent that wraps MCP1's recommendation tools
and exposes them via the A2A (Agent-to-Agent) protocol.

Flow when called from MCP2 via A2A:
  MCP2 agent  →  A2A HTTP call  →  THIS server  →  MCP1 client  →  MCP1 tools

Why A2A here?
  - MCP2 needs to orchestrate 3 recommendation tools (process → count → html)
  - Instead of adding those tools to MCP2, MCP2 delegates to this A2A agent
  - This agent handles the full orchestration pipeline of MCP1's 3 tools
  - Keeps MCP2 focused only on math; recommendation logic stays in MCP1

Runs on port 8003.
"""

import sys
import os
import asyncio
import json
from aiohttp import web

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from mcp1.tools.recommendation_tools import process_text, get_count, print_count_html


# ── A2A Agent Card (required by A2A protocol) ──────────────────────────────────
# Agent Card describes this agent's capabilities to other agents (like MCP2)
AGENT_CARD = {
    "name": "RecommendationAgent",
    "description": "Orchestrates text processing: process_text → get_count → print_count_html",
    "version": "1.0.0",
    "url": "http://localhost:8003",
    "capabilities": {
        "streaming": False,          # Not streaming, simple request/response
        "pushNotifications": False
    },
    "skills": [
        {
            # Skill name that MCP2's A2A client will call
            "id": "full_recommendation_pipeline",
            "name": "Full Recommendation Pipeline",
            "description": "Takes raw text, runs all 3 tools, returns word counts + HTML",
            "inputModes": ["text"],
            "outputModes": ["text"]
        }
    ]
}


async def handle_agent_card(request):
    """
    GET /.well-known/agent.json
    A2A protocol requires every agent to expose its card at this URL.
    Other agents discover capabilities by fetching this endpoint.
    """
    return web.json_response(AGENT_CARD)


async def handle_task(request):
    """
    POST /tasks/send
    A2A protocol: caller sends a task payload, agent processes and returns result.

    Expected request body (A2A Task format):
    {
      "id": "task-uuid",
      "message": {
        "role": "user",
        "parts": [{"text": "apple banana apple orange"}]
      }
    }
    """
    # Parse incoming A2A task payload
    body = await request.json()

    # Extract the input text from A2A message parts
    task_id = body.get("id", "unknown")
    parts = body.get("message", {}).get("parts", [])
    input_text = parts[0].get("text", "") if parts else ""

    print(f"[A2A Server] Received task {task_id}: '{input_text[:60]}'")

    # ── Orchestration: run all 3 MCP1 tools in sequence ───────────────────────

    # Step 1: process_text → word frequency dict
    word_counts = process_text(input_text)
    print(f"[A2A Server] Step1 process_text done: {word_counts}")

    # Step 2: get_count → total and unique counts
    counts = get_count(word_counts)
    print(f"[A2A Server] Step2 get_count done: {counts}")

    # Step 3: print_count_html → HTML string
    html = print_count_html(word_counts)
    print(f"[A2A Server] Step3 print_count_html done (len={len(html)})")

    # Build A2A Task response format
    response_payload = {
        "id": task_id,
        "status": {"state": "completed"},
        "artifacts": [
            {
                "name": "recommendation_result",
                "parts": [
                    {
                        "text": json.dumps({
                            "word_counts": word_counts,   # e.g. {"apple": 3}
                            "counts": counts,              # e.g. {"total_words": 5}
                            "html": html                   # full HTML string
                        })
                    }
                ]
            }
        ]
    }

    return web.json_response(response_payload)


async def handle_list_tasks(request):
    """
    GET /tasks — A2A protocol endpoint (minimal implementation).
    Returns empty list since we don't persist tasks.
    """
    return web.json_response([])


def create_app():
    """Build and return the aiohttp web app with A2A routes."""
    app = web.Application()

    # A2A protocol required routes
    app.router.add_get("/.well-known/agent.json", handle_agent_card)  # agent discovery
    app.router.add_post("/tasks/send", handle_task)                    # task execution
    app.router.add_get("/tasks", handle_list_tasks)                    # task listing

    return app


if __name__ == "__main__":
    print("[A2A Server] RecommendationAgent starting on http://localhost:8003")
    app = create_app()
    # Run using aiohttp's built-in runner
    web.run_app(app, host="0.0.0.0", port=8003)
