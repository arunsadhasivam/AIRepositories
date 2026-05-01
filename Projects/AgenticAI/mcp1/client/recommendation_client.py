"""
mcp1/client/recommendation_client.py
"""
import asyncio, sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from fastmcp import Client
import json

class RecommendationMCPClient:
    def __init__(self, server_url: str = "http://localhost:8001/mcp"):
        self.server_url = server_url

    def _parse(self, result):
        # CallToolResult.content is a list of content blocks
        # each block has a .text attribute (string)
        raw = result.content[0].text
        try:
            return json.loads(raw)   # parse JSON string back to dict if possible
        except (json.JSONDecodeError, TypeError):
            return raw               # return as-is if plain string

    async def process_text(self, text: str):
        async with Client(self.server_url) as client:
            result = await client.call_tool("tool_process_text", {"text": text})
            return self._parse(result)

    async def get_count(self, word_counts: dict):
        async with Client(self.server_url) as client:
            result = await client.call_tool("tool_get_count", {"word_counts": word_counts})
            return self._parse(result)

    async def print_count_html(self, word_counts: dict):
        async with Client(self.server_url) as client:
            result = await client.call_tool("tool_print_count_html", {"word_counts": word_counts})
            return self._parse(result)

    async def math_tool_add_via_mcp2(self, a: float, b: float):
        async with Client(self.server_url) as client:
            result = await client.call_tool("tool_add_from_mcp2", {"a": a, "b": b})
            return self._parse(result)
        
    
async def _demo():
    client = RecommendationMCPClient()
    wc = await client.process_text("apple banana apple orange banana apple")
    print(f"word_counts: {wc}")
    cnt = await client.get_count(wc)
    print(f"counts: {cnt}")
    html = await client.print_count_html(wc)
    print(f"html (200): {str(html)[:200]}")


    

if __name__ == "__main__":
    asyncio.run(_demo())
    
    async def add_from_mcp2(self, a: float, b: float):
        """
        Call tool_add_from_mcp2 on MCP1 server.
        MCP1 server internally calls MCP2 add directly (no A2A).
        Flow: this client → MCP1 (8001) → MCP2 (8002) → result
        """
        async with Client(self.server_url) as client:
            result = await client.call_tool("tool_add_from_mcp2", {"a": a, "b": b})
            return self._parse(result)
