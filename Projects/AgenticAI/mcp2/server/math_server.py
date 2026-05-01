"""
mcp2/server/math_server.py
----------------------------
FastMCP server that exposes math tools only.
Runs on port 8002.

Key point: MCP2 has NO orchestration logic.
  - Math operations → handled here directly
  - Text/recommendation operations → delegated via A2A to MCP1
"""

import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastmcp import FastMCP
from mcp2.tools.math_tools import add, multiply, power, average

# Create MCP2 server instance
mcp = FastMCP("math-server")


@mcp.tool()
def tool_add(a: float, b: float) -> float:
    """Tool: Add two numbers. e.g. tool_add(3, 4) → 7.0"""
    return add(a, b)


@mcp.tool()
def tool_multiply(a: float, b: float) -> float:
    """Tool: Multiply two numbers. e.g. tool_multiply(3, 4) → 12.0"""
    return multiply(a, b)


@mcp.tool()
def tool_power(base: float, exp: float) -> float:
    """Tool: base^exp. e.g. tool_power(2, 10) → 1024.0"""
    return power(base, exp)


@mcp.tool()
def tool_average(numbers: list) -> float:
    """Tool: Average of a list. e.g. tool_average([1,2,3]) → 2.0"""
    return average(numbers)


if __name__ == "__main__":
    print("[MCP2] Math server starting on http://localhost:8002")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8002)
