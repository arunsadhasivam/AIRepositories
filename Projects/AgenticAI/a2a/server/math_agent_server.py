"""
a2a/server/math_agent_server.py
---------------------------------
A2A Server: Wraps MCP2 math tools and exposes them via A2A protocol.
This is the REVERSE direction:

  MCP1 agent  →  A2A HTTP call  →  THIS server  →  MCP2 math tools

Why?
  - MCP1 (recommendation) needs math (e.g. compute average frequency)
  - Instead of adding math tools to MCP1, MCP1 delegates via A2A to THIS server
  - THIS server calls MCP2 math tools internally

Runs on port 8004.
"""

import sys
import os
import json
from aiohttp import web

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import math tools directly (same as MCP2 uses internally)
from mcp2.tools.math_tools import add, multiply, power, average


# ── A2A Agent Card ─────────────────────────────────────────────────────────────
AGENT_CARD = {
    "name": "MathAgent",
    "description": "Exposes math operations via A2A: add, multiply, power, average",
    "version": "1.0.0",
    "url": "http://localhost:8004",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False
    },
    "skills": [
        {
            "id": "math_operation",
            "name": "Math Operation",
            "description": "Perform a math operation: add | multiply | power | average",
            "inputModes": ["text"],
            "outputModes": ["text"]
        }
    ]
}


async def handle_agent_card(request):
    """
    GET /.well-known/agent.json
    A2A discovery endpoint — MCP1's A2A client fetches this first.
    """
    return web.json_response(AGENT_CARD)


async def handle_task(request):
    """
    POST /tasks/send
    A2A task handler. Expects payload:
    {
      "id": "task-uuid",
      "message": {
        "role": "user",
        "parts": [{
          "text": "{\"operation\": \"add\", \"args\": {\"a\": 3, \"b\": 4}}"
        }]
      }
    }

    Supported operations: add, multiply, power, average
    """
    body = await request.json()

    task_id = body.get("id", "unknown")
    parts = body.get("message", {}).get("parts", [])
    # Extract the JSON instruction from the text part
    input_text = parts[0].get("text", "{}") if parts else "{}"

    print(f"[A2A MathAgent] Received task {task_id}: {input_text}")

    # Parse the operation request from JSON string
    try:
        request_data = json.loads(input_text)
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid JSON in task parts"}, status=400)

    operation = request_data.get("operation", "")   # e.g. "add"
    args = request_data.get("args", {})             # e.g. {"a": 3, "b": 4}

    # Dispatch to the correct math tool based on operation name
    result = None
    if operation == "add":
        result = add(args.get("a", 0), args.get("b", 0))

    elif operation == "multiply":
        result = multiply(args.get("a", 0), args.get("b", 0))

    elif operation == "power":
        result = power(args.get("base", 0), args.get("exp", 0))

    elif operation == "average":
        result = average(args.get("numbers", []))

    else:
        result = f"Unknown operation: {operation}"

    print(f"[A2A MathAgent] Result for {operation}: {result}")

    # Build A2A response with result in artifact parts
    response_payload = {
        "id": task_id,
        "status": {"state": "completed"},
        "artifacts": [
            {
                "name": "math_result",
                "parts": [
                    {
                        "text": json.dumps({
                            "operation": operation,   # e.g. "add"
                            "args": args,             # e.g. {"a": 3, "b": 4}
                            "result": result          # e.g. 7.0
                        })
                    }
                ]
            }
        ]
    }

    return web.json_response(response_payload)


async def handle_list_tasks(request):
    """GET /tasks — minimal A2A protocol implementation."""
    return web.json_response([])


def create_app():
    """Build aiohttp app with A2A routes."""
    app = web.Application()
    app.router.add_get("/.well-known/agent.json", handle_agent_card)  # discovery
    app.router.add_post("/tasks/send", handle_task)                    # task execution
    app.router.add_get("/tasks", handle_list_tasks)
    return app


if __name__ == "__main__":
    print("[A2A MathAgent] Starting on http://localhost:8004")
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8004)
