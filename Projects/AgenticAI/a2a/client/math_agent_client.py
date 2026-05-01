"""
a2a/client/math_agent_client.py
---------------------------------
A2A Client: Used by MCP1 (recommendation side) to delegate math operations
to the MathAgent A2A server (port 8004), which internally uses MCP2 tools.

REVERSE direction vs recommendation_agent_client:
  MCP1 caller  →  [THIS CLIENT]  →  A2A HTTP  →  MathAgent A2A Server  →  MCP2 tools

MCP1 does NOT call MCP2 directly — it delegates via A2A.
"""

import asyncio
import aiohttp
import json
import uuid


class MathAgentClient:
    """
    A2A client for the MathAgent server (port 8004).
    MCP1 uses this to delegate math work to MCP2 via A2A.
    """

    def __init__(self, agent_url: str = "http://localhost:8004"):
        # Base URL of the MathAgent A2A server
        self.agent_url = agent_url

    async def discover(self) -> dict:
        """
        GET /.well-known/agent.json — discover MathAgent capabilities.
        A2A protocol: always discover before sending tasks.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.agent_url}/.well-known/agent.json") as resp:
                card = await resp.json()
                print(f"[A2A MathClient] Discovered: {card['name']} - {card['description']}")
                return card

    async def _send_task(self, operation: str, args: dict) -> dict:
        """
        Internal helper: send a math operation task to the A2A server.

        Args:
            operation: one of "add" | "multiply" | "power" | "average"
            args:      operation-specific args dict

        Returns:
            dict with keys: operation, args, result
        """
        # Build A2A task payload with operation encoded as JSON in text part
        task_payload = {
            "id": str(uuid.uuid4()),            # unique task ID
            "message": {
                "role": "user",
                "parts": [
                    {
                        # Encode operation + args as JSON string in the text part
                        "text": json.dumps({"operation": operation, "args": args})
                    }
                ]
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.agent_url}/tasks/send",
                json=task_payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                response = await resp.json()

        # Extract result from A2A artifact
        artifacts = response.get("artifacts", [])
        if not artifacts:
            return {}

        result_text = artifacts[0]["parts"][0]["text"]
        return json.loads(result_text)   # {"operation": "add", "args": {...}, "result": 7.0}

    async def add(self, a: float, b: float) -> float:
        """Delegate add(a, b) to MathAgent via A2A."""
        result = await self._send_task("add", {"a": a, "b": b})
        return result.get("result", 0.0)

    async def multiply(self, a: float, b: float) -> float:
        """Delegate multiply(a, b) to MathAgent via A2A."""
        result = await self._send_task("multiply", {"a": a, "b": b})
        return result.get("result", 0.0)

    async def power(self, base: float, exp: float) -> float:
        """Delegate power(base, exp) to MathAgent via A2A."""
        result = await self._send_task("power", {"base": base, "exp": exp})
        return result.get("result", 0.0)

    async def average(self, numbers: list) -> float:
        """Delegate average(numbers) to MathAgent via A2A."""
        result = await self._send_task("average", {"numbers": numbers})
        return result.get("result", 0.0)


# ── Quick test ─────────────────────────────────────────────────────────────────
async def _demo():
    client = MathAgentClient()

    # Discover first
    await client.discover()

    # Call math ops via A2A (MCP1 → A2A → MCP2 tools)
    print(f"\n[A2A] add(10, 25)         = {await client.add(10, 25)}")
    print(f"[A2A] multiply(6, 7)      = {await client.multiply(6, 7)}")
    print(f"[A2A] power(2, 8)         = {await client.power(2, 8)}")
    print(f"[A2A] average([10,20,30]) = {await client.average([10, 20, 30])}")


if __name__ == "__main__":
    asyncio.run(_demo())
