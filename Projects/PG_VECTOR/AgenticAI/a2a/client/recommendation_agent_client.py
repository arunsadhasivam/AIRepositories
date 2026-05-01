"""
a2a/client/recommendation_agent_client.py
-------------------------------------------
A2A Client: Used by MCP2 (or any caller) to delegate recommendation tasks
to the A2A server (which internally calls MCP1 tools).

This is the "delegation" mechanism:
  MCP2 agent  →  [THIS CLIENT]  →  A2A HTTP  →  A2A Server  →  MCP1 tools

Instead of MCP2 knowing about MCP1's tools directly,
it just sends a text task here and gets back full results.
"""

import asyncio
import aiohttp
import json
import uuid


class RecommendationAgentClient:
    """
    A2A client for the RecommendationAgent server (port 8003).
    Implements the A2A protocol: send task, receive artifact result.
    """

    def __init__(self, agent_url: str = "http://localhost:8003"):
        # Base URL of the A2A recommendation agent server
        self.agent_url = agent_url

    async def discover(self) -> dict:
        """
        Fetch the agent card from /.well-known/agent.json
        A2A protocol: callers discover agent capabilities before sending tasks.
        Returns the agent card dict describing skills and capabilities.
        """
        async with aiohttp.ClientSession() as session:
            # GET /.well-known/agent.json
            async with session.get(f"{self.agent_url}/.well-known/agent.json") as resp:
                card = await resp.json()
                print(f"[A2A Client] Discovered agent: {card['name']} - {card['description']}")
                return card

    async def run_full_pipeline(self, text: str) -> dict:
        """
        Send a text task to the A2A recommendation agent.
        The agent will:
          1. process_text(text)
          2. get_count(word_counts)
          3. print_count_html(word_counts)
        and return all 3 results.

        Args:
            text: raw input string

        Returns:
            dict with keys: word_counts, counts, html
        """
        # Build A2A task payload following the A2A protocol message format
        task_payload = {
            "id": str(uuid.uuid4()),       # unique task ID
            "message": {
                "role": "user",
                "parts": [
                    {"text": text}         # input text passed as task part
                ]
            }
        }

        async with aiohttp.ClientSession() as session:
            # POST /tasks/send with task payload
            async with session.post(
                f"{self.agent_url}/tasks/send",
                json=task_payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                # Parse A2A response
                response = await resp.json()

        # Extract artifacts from A2A response
        artifacts = response.get("artifacts", [])
        if not artifacts:
            return {}

        # Get the text content of the first artifact part
        result_text = artifacts[0]["parts"][0]["text"]

        # Parse JSON string back to dict
        result = json.loads(result_text)

        return result  # {"word_counts": {...}, "counts": {...}, "html": "..."}


# ── Quick test ─────────────────────────────────────────────────────────────────
async def _demo():
    client = RecommendationAgentClient()

    # Step 0: discover agent capabilities
    await client.discover()

    # Step 1: run full pipeline via A2A
    print("\n[A2A Client] Running full recommendation pipeline via A2A...")
    result = await client.run_full_pipeline(
        "apple banana apple orange banana apple mango mango apple"
    )

    print(f"\n  word_counts : {result.get('word_counts')}")
    print(f"  counts      : {result.get('counts')}")
    print(f"  html (first 300 chars): {result.get('html', '')[:300]}")


if __name__ == "__main__":
    asyncio.run(_demo())
