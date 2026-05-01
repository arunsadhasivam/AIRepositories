"""
mcp2/client/math_client.py
"""
import asyncio, sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from fastmcp import Client
import json

class MathMCPClient:
    def __init__(self, server_url: str = "http://localhost:8002/mcp"):
        self.server_url = server_url

    def _parse(self, result):
        # CallToolResult.content[0].text holds the return value as string
        raw = result.content[0].text
        try:
            return json.loads(raw)   # convert "7.0" -> 7.0, "true" -> True etc
        except (json.JSONDecodeError, TypeError):
            return raw

    async def add(self, a: float, b: float):
        async with Client(self.server_url) as client:
            result = await client.call_tool("tool_add", {"a": a, "b": b})
            return self._parse(result)

    async def multiply(self, a: float, b: float):
        async with Client(self.server_url) as client:
            result = await client.call_tool("tool_multiply", {"a": a, "b": b})
            return self._parse(result)

    async def power(self, base: float, exp: float):
        async with Client(self.server_url) as client:
            result = await client.call_tool("tool_power", {"base": base, "exp": exp})
            return self._parse(result)

    async def average(self, numbers: list):
        async with Client(self.server_url) as client:
            result = await client.call_tool("tool_average", {"numbers": numbers})
            return self._parse(result)

async def _demo():
    client = MathMCPClient()
    print(await client.add(5, 3))
    print(await client.multiply(4, 6))
    print(await client.power(2, 8))
    print(await client.average([1, 2, 3, 4, 5]))

if __name__ == "__main__":
    asyncio.run(_demo())