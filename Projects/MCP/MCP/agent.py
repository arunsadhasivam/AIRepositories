#!/usr/bin/env python3
"""
Ollama AI Agent for IT Helpdesk.

This agent:
1. Takes natural language input from the user
2. Sends it to the MCP server as a tool call
3. Gets results back from PostgreSQL via MCP
4. Displays results in a readable format
"""

import asyncio
import json
import subprocess
import sys
from mcp import ClientSession, StdioServerParameters    # MCP client libraries
from mcp.client.stdio import stdio_client               # stdio transport for local MCP server
import ollama                                           # Ollama Python client


# ============================================================
# Configuration
# ============================================================
OLLAMA_MODEL = "llama2"                                 # model pulled via: ollama pull llama3
MCP_SERVER_SCRIPT = "mcp_server.py"                    # path to our MCP server


# ============================================================
# Helper: Pretty print JSON results
# ============================================================
def _print_results(data: str):
    """Parse and print results in a readable format."""
    try:
        parsed = json.loads(data)                       # try to parse as JSON

        if isinstance(parsed, list):
            print(f"\n✅ Found {len(parsed)} result(s):\n")
            for i, item in enumerate(parsed, 1):
                print(f"--- #{i} ---")
                for key, value in item.items():
                    print(f"  {key}: {value}")         # print each field on its own line
                print()

        elif isinstance(parsed, dict):
            if "error" in parsed:
                print(f"\n❌ Error: {parsed['error']}")
            elif "message" in parsed:
                print(f"\nℹ️  {parsed['message']}")
            else:
                # summary or single ticket
                print("\n✅ Result:\n")
                print(json.dumps(parsed, indent=2))

    except json.JSONDecodeError:
        print(f"\n{data}")                              # if not JSON, print as plain text


# ============================================================
# Helper: Decide which MCP tool to call based on user query
# ============================================================
def _decide_tool(query: str) -> tuple[str, dict]:
    """
    Simple intent detection — maps user query to the right MCP tool and params.
    Returns (tool_name, tool_params) tuple.
    """
    q = query.lower()

    # If asking for a specific ticket number like TKT-1001
    if "tkt-" in q:
        import re
        match = re.search(r"tkt-\d+", q, re.IGNORECASE)    # extract ticket number with regex
        ticket_number = match.group(0).upper() if match else ""
        return "helpdesk_get_ticket", {
            "ticket_number": ticket_number,
            "queried_by": CURRENT_USER,
            "role": CURRENT_ROLE
        }

    # If asking for summary/stats/dashboard
    if any(word in q for word in ["summary", "statistics", "stats", "overview", "dashboard", "count"]):
        return "helpdesk_get_summary", {
            "queried_by": CURRENT_USER,
            "role": CURRENT_ROLE
        }

    # Default: natural language ticket query
    return "helpdesk_query_tickets", {
        "natural_query": query,
        "queried_by": CURRENT_USER,
        "role": CURRENT_ROLE
    }


# ============================================================
# Main agent — connects to MCP and processes queries
# ============================================================
async def run_agent(query: str):
    """
    Connect to MCP server, call the right tool, return results.

    Flow:
    1. Start MCP server as subprocess
    2. Connect MCP client via stdio
    3. Detect which tool to call
    4. Call the tool with parameters
    5. Print results
    """

    # Step 1: Define MCP server as a subprocess command
    server_params = StdioServerParameters(
        command=sys.executable,                         # use current Python interpreter
        args=[MCP_SERVER_SCRIPT],                       # run our mcp_server.py
        env=None
    )

    # Step 2: Connect MCP client to MCP server via stdio transport
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            # Step 3: Initialize the MCP session (handshake)
            await session.initialize()

            # Step 4: List available tools from MCP server (for verification)
            tools = await session.list_tools()
            print(f"\n🔧 Available MCP Tools: {[t.name for t in tools.tools]}")

            # Step 5: Decide which tool to call
            tool_name, tool_params = _decide_tool(query)
            print(f"📡 Calling tool: {tool_name}")
            print(f"🔍 Query: {query}\n")

            # Step 6: Call the MCP tool with parameters
            result = await session.call_tool(tool_name, arguments=tool_params)

            # Step 7: Extract text content from MCP result
            if result.content:
                raw = result.content[0].text            # MCP returns list of content blocks
                _print_results(raw)                     # pretty print results
            else:
                print("No results returned.")


# ============================================================
# Interactive CLI loop
# ============================================================
async def main():
    """Main interactive loop — keeps asking for queries until user types 'exit'."""

    print("=" * 60)
    print("  🎫 IT Helpdesk AI Agent — powered by MCP + Ollama")
    print("=" * 60)
    print(f"  User: {CURRENT_USER}  |  Role: {CURRENT_ROLE}")
    print("  Type 'exit' to quit\n")

    print("💡 Example queries:")
    print("  - Show all critical open tickets")
    print("  - How many unassigned tickets are there?")
    print("  - List all network tickets")
    print("  - Get ticket summary")
    print("  - What is the status of TKT-1002?")
    print()

    # Keep running until user exits
    while True:
        try:
            query = input("You: ").strip()              # get input from user

            if not query:
                continue                                # skip empty input

            if query.lower() in ["exit", "quit", "q"]:
                print("\n👋 Goodbye!")
                break

            await run_agent(query)                      # process the query

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


# ============================================================
# Entry point — set user and role here before running
# ============================================================
# Change these to test different roles
CURRENT_USER = "agent_priya"                           # username from agents table
CURRENT_ROLE = "agent"                                 # 'admin' or 'agent'

if __name__ == "__main__":
    asyncio.run(main())                                 # run async main loop
