import httpx   # pip install httpx — HTTP client for Ollama + MCP server calls
import json    # built-in — parse JSON responses

# ─────────────────────────────────────────────────────────────────────────────
# OLLAMA vs ANTHROPIC SDK — KEY DIFFERENCE
#
# Anthropic:  import anthropic → client.messages.create(...)
#             SDK wraps everything for you
#
# Ollama:     raw HTTP POST to http://localhost:11434/api/chat
#             You build the JSON body manually
#             No SDK needed — just httpx
#
# Ollama uses OpenAI-compatible format:
#   - "tool_calls" instead of "tool_use"
#   - "finish_reason" instead of "stop_reason"
#   - messages[].role = "tool" instead of "tool_result"
# ─────────────────────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/chat"   # Ollama local endpoint
MODEL      = "llama3.1"                          # Must support tools — llama3.1, mistral-nemo, qwen2.5


# ─────────────────────────────────────────────────────────────────────────────
# TOOL SCHEMA CACHE
#
# PROBLEM WITHOUT CACHING:
#   Every request passes tool schemas to the LLM.
#   1 schema ≈ 100-300 tokens.
#   10 tools × 1000 requests/day = millions of wasted tokens.
#
# SOLUTION: fetch tool schemas ONCE at app startup, store in module-level variable.
#   - discoverTools() called once → result stored in _TOOL_SCHEMA_CACHE
#   - Every LLM call reads from cache — zero extra HTTP calls, zero re-parsing
#
# In prod (FastAPI/Flask):
#   @app.on_event("startup") → call load_tool_cache()
#   Every request handler reads from _TOOL_SCHEMA_CACHE directly
#
# Cache invalidation:
#   - Simple: restart app (fine for tools that rarely change)
#   - Advanced: background thread calls discoverTools() every 5 minutes
#               and atomically swaps _TOOL_SCHEMA_CACHE
# ─────────────────────────────────────────────────────────────────────────────

_TOOL_SCHEMA_CACHE: list[dict] = []   # Module-level cache — populated once at startup


def load_tool_cache(mcp_server_url: str) -> None:
    """
    Call this ONCE at app startup.
    Fetches tool schemas from MCP server and stores in module-level cache.
    NOT an LLM call — just HTTP to MCP server.
    """
    global _TOOL_SCHEMA_CACHE   # Write to module-level variable

    # POST to MCP server tools/list endpoint — JSON-RPC 2.0 protocol
    response = httpx.post(
        mcp_server_url + "/mcp",                    # MCP server endpoint
        json={
            "jsonrpc": "2.0",                       # MCP protocol version
            "id": 1,                                # Request ID (arbitrary)
            "method": "tools/list",                 # MCP method to list all tools
            "params": {}                            # No params needed for listing
        },
        timeout=10.0                                # Fail fast if MCP server is down
    )

    data  = response.json()                         # Parse JSON response
    tools = data["result"]["tools"]                 # Extract tools array

    # Convert MCP schema format → Ollama/OpenAI tool format
    # MCP uses "inputSchema", Ollama uses "parameters" inside "function"
    _TOOL_SCHEMA_CACHE = [
        {
            "type": "function",                     # Ollama requires this wrapper
            "function": {
                "name":        tool["name"],         # Tool name e.g. "get_weather"
                "description": tool["description"],  # LLM reads this to decide when to call
                "parameters":  tool["inputSchema"]   # JSON Schema of inputs — renamed for Ollama
            }
        }
        for tool in tools                           # One entry per tool the MCP server exposes
    ]

    print(f"[Cache] Loaded {len(_TOOL_SCHEMA_CACHE)} tools from {mcp_server_url}")
    # Output: [Cache] Loaded 2 tools from https://weather-mcp.example.com


def get_cached_tools() -> list[dict]:
    """
    Read tool schemas from cache — called on every LLM request.
    Zero HTTP calls. Zero MCP server round-trips. Zero extra tokens from re-fetching.
    """
    if not _TOOL_SCHEMA_CACHE:                      # Guard: cache not loaded yet
        raise RuntimeError("Tool cache is empty. Call load_tool_cache() at startup first.")
    return _TOOL_SCHEMA_CACHE                       # Return cached list directly


# ─────────────────────────────────────────────────────────────────────────────
# ACTUAL TOOL FUNCTION
# This is YOUR code — executes locally or calls real MCP server.
# NOT an LLM call. Zero LLM cost.
# ─────────────────────────────────────────────────────────────────────────────

def get_weather(city: str) -> str:
    """
    Real prod version would POST to MCP server:

    r = httpx.post("https://weather-mcp.example.com/mcp", json={
        "jsonrpc": "2.0",
        "method":  "tools/call",
        "params":  {"name": "get_weather", "arguments": {"city": city}}
    })
    return r.json()["result"]["content"][0]["text"]
    """
    return f"72 degrees F, Sunny in {city}"         # Mocked for this example


# Map tool name → callable — used to route LLM's tool_call to correct function
# In prod: build this map dynamically from discovered tools + registered handlers
TOOL_REGISTRY = {
    "get_weather": get_weather                      # "get_weather" → function to call
}


# ─────────────────────────────────────────────────────────────────────────────
# LLM CALL via OLLAMA
# Raw HTTP POST — no SDK.
# Returns the full parsed JSON response from Ollama.
# ─────────────────────────────────────────────────────────────────────────────

def call_ollama(messages: list[dict]) -> dict:
    """
    Single LLM call to Ollama.
    Reads tool schemas from cache — NOT re-fetched here.
    Cost (local Ollama): electricity + VRAM. No token billing.
    Cost (cloud Ollama): input tokens (messages + cached tool schemas) + output tokens.

    messages: full conversation history so far
    returns:  Ollama raw response dict
    """
    response = httpx.post(
        OLLAMA_URL,                                 # http://localhost:11434/api/chat
        json={
            "model":    MODEL,                      # e.g. "llama3.1"
            "messages": messages,                   # Full conversation history
            "tools":    get_cached_tools(),         # Read from cache — zero extra HTTP call
            "stream":   False                       # Get full response, not streaming chunks
        },
        timeout=120.0                               # Ollama can be slow locally — generous timeout
    )

    return response.json()                          # Return parsed Ollama response dict


# ─────────────────────────────────────────────────────────────────────────────
# AGENTIC LOOP
# Handles multiple tool calls before final answer.
# Each loop iteration = 1 LLM call to Ollama.
# ─────────────────────────────────────────────────────────────────────────────

def chat(user_query: str) -> str:
    """
    Full agentic loop:
      LLM Call #1 → tool decision (finish_reason: "tool_calls")
      [execute tool — zero LLM cost]
      LLM Call #2 → final answer (finish_reason: "stop")

    For N tools: N+1 LLM calls total.
    """

    # Build conversation — grows with each tool round-trip
    messages = [
        {"role": "user", "content": user_query}    # Initial user message
    ]

    # ── AGENTIC LOOP — each iteration = 1 LLM call ───────────────────────────
    while True:

        # ── LLM CALL #N ──────────────────────────────────────────────────────
        # Tools read from cache — not re-fetched, not re-parsed
        # Ollama format: finish_reason instead of stop_reason
        ollama_response = call_ollama(messages)

        # Extract the assistant message from Ollama response
        # Ollama: response["message"] contains role + content + tool_calls
        assistant_msg = ollama_response["message"]         # { role, content, tool_calls? }
        finish_reason = ollama_response["done_reason"]     # "tool_calls" or "stop"

        # Add LLM response to history — required for next call to have context
        # Ollama needs the full assistant message object including tool_calls
        messages.append(assistant_msg)

        # ── CASE 1: LLM done — return final answer ───────────────────────────
        # Ollama: finish_reason == "stop" (vs Anthropic: stop_reason == "end_turn")
        if finish_reason == "stop":
            return assistant_msg["content"]                # Final natural language answer

        # ── CASE 2: LLM wants to call tools ─────────────────────────────────
        # Ollama: finish_reason == "tool_calls" (vs Anthropic: stop_reason == "tool_use")
        if finish_reason == "tool_calls":

            # Ollama puts tool calls in message["tool_calls"] — a list
            tool_calls = assistant_msg.get("tool_calls", [])

            for tool_call in tool_calls:                   # Handle multiple tool calls

                # Extract tool call details
                # Ollama format: tool_call["function"]["name"] and ["arguments"]
                tool_name      = tool_call["function"]["name"]       # e.g. "get_weather"
                tool_arguments = tool_call["function"]["arguments"]  # dict e.g. {"city": "SF"}

                # Look up function in registry — NOT an LLM call
                fn = TOOL_REGISTRY.get(tool_name)
                if not fn:                                 # LLM hallucinated a tool name
                    tool_result = f"Error: tool '{tool_name}' not found"
                else:
                    tool_result = fn(**tool_arguments)     # Execute the function

                # Send tool result back to LLM
                # Ollama format: role = "tool" (vs Anthropic: "user" with type "tool_result")
                messages.append({
                    "role":    "tool",                     # Ollama uses "tool" role
                    "content": tool_result                 # The actual result string
                })

            # Loop → next call_ollama() reads full history including tool results


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP + RUN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # ── STARTUP: load tool schemas once into cache ────────────────────────────
    # In prod (FastAPI): put this in @app.on_event("startup")
    # In prod (Flask):   put this in app.before_first_request or app factory
    load_tool_cache("https://weather-mcp.example.com")
    # For local testing with mocked tools — comment above, uncomment below:
    # _TOOL_SCHEMA_CACHE = [{"type":"function","function":{"name":"get_weather","description":"Get weather","parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}}}]

    # ── REQUEST: read from cache, no re-fetch ─────────────────────────────────
    # Every chat() call reads _TOOL_SCHEMA_CACHE — zero MCP server calls per request
    answer = chat("What is the weather in San Francisco?")
    print("Answer:", answer)
    # Output: "The current weather in San Francisco is 72 degrees F and Sunny."
