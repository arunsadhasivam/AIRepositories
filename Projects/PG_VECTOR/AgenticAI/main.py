"""
main.py
--------
Test entry point to demonstrate all 3 communication patterns:

  method1_direct_mcp1()   → Call MCP1 recommendation tools directly via MCP client
  method2_direct_mcp2()   → Call MCP2 math tools directly via MCP client
  method3_a2a_delegate()  → MCP2 delegates recommendation work to MCP1 via A2A

Architecture reminder:
  MCP1 (port 8001) = recommendation server  [process_text, get_count, print_count_html]
  MCP2 (port 8002) = math server            [add, multiply, power, average]
  A2A  (port 8003) = recommendation agent   [wraps MCP1 tools, exposes via A2A protocol]

Run servers first:
  python mcp1/server/recommendation_server.py  &  (port 8001)
  python mcp2/server/math_server.py            &  (port 8002)
  python a2a/server/recommendation_agent_server.py &  (port 8003)

Then: python main.py
"""

import asyncio
import sys
import os

# Add project root to path so all imports resolve
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mcp1.client.recommendation_client import RecommendationMCPClient
from mcp2.client.math_client import MathMCPClient
from a2a.client.recommendation_agent_client import RecommendationAgentClient
from a2a.client.math_agent_client import MathAgentClient


# ──────────────────────────────────────────────────────────────────────────────
# Method 1: Direct MCP1 call (no A2A, no orchestration via agent)
# Use case: caller knows MCP1 exists and wants to call tools one by one
# ──────────────────────────────────────────────────────────────────────────────
async def method1_direct_mcp1():
    """
    Directly call MCP1 recommendation server tools step by step.
    No A2A involved — pure MCP client → MCP server.
    """
    print("\n" + "="*60)
    print("METHOD 1: Direct MCP1 call (MCP client → MCP1 server)")
    print("="*60)

    client = RecommendationMCPClient()  # connects to port 8001

    sample_text = "apple banana apple orange banana apple mango"

    # Tool 1: process text → word frequency dict
    print(f"\n[1] Calling tool_process_text with: '{sample_text}'")
    word_counts = await client.process_text(sample_text)
    print(f"    Result: {word_counts}")

    # Tool 2: get count summary
    print(f"\n[2] Calling tool_get_count...")
    counts = await client.get_count(word_counts)
    print(f"    Result: {counts}")

    # Tool 3: print HTML table
    print(f"\n[3] Calling tool_print_count_html...")
    html = await client.print_count_html(word_counts)
    print(f"    Result (first 300 chars): {html[:300]}")

    # Save HTML to file for inspection
    with open("output_method1.html", "w") as f:
        f.write(html)
    print(f"\n    HTML saved to output_method1.html")


# ──────────────────────────────────────────────────────────────────────────────
# Method 2: Direct MCP2 call (math only, no delegation)
# Use case: pure math computation, no orchestration needed
# ──────────────────────────────────────────────────────────────────────────────
async def method2_direct_mcp2():
    """
    Directly call MCP2 math server tools.
    No A2A — just direct math operations.
    """
    print("\n" + "="*60)
    print("METHOD 2: Direct MCP2 call (MCP client → MCP2 math server)")
    print("="*60)

    client = MathMCPClient()  # connects to port 8002

    # Call each math tool directly
    print(f"\n[1] tool_add(10, 25)         = {await client.add(10, 25)}")
    print(f"[2] tool_multiply(6, 7)      = {await client.multiply(6, 7)}")
    print(f"[3] tool_power(2, 10)        = {await client.power(2, 10)}")
    print(f"[4] tool_average([10,20,30]) = {await client.average([10, 20, 30])}")


# ──────────────────────────────────────────────────────────────────────────────
# Method 3: A2A delegation — MCP2 caller delegates recommendation work to MCP1
# Use case: caller (MCP2 side) needs recommendation pipeline but delegates via A2A
# MCP2 does NOT need to know about MCP1's internal tools — just sends text to A2A agent
# ──────────────────────────────────────────────────────────────────────────────
async def method3_a2a_delegate():
    """
    MCP2 caller delegates recommendation orchestration to MCP1 via A2A.

    KEY CONCEPT:
      - MCP2 has no recommendation tools
      - Instead of adding them to MCP2, we call the A2A agent
      - A2A agent internally runs: process_text → get_count → print_count_html
      - MCP2 gets back full result without knowing MCP1's tool structure
    """
    print("\n" + "="*60)
    print("METHOD 3: A2A delegation (MCP2 caller → A2A agent → MCP1 tools)")
    print("="*60)

    # First, do a math operation on MCP2 (direct)
    math_client = MathMCPClient()
    print(f"\n[MCP2 Math] tool_multiply(3, 7) = {await math_client.multiply(3, 7)}")

    # Now, for recommendation work — delegate via A2A instead of adding to MCP2
    a2a_client = RecommendationAgentClient()  # connects to port 8003

    # Step 0: discover what the A2A agent can do (optional but shows A2A protocol)
    print("\n[A2A] Discovering agent capabilities...")
    card = await a2a_client.discover()
    print(f"      Agent: {card['name']}, Skills: {[s['id'] for s in card['skills']]}")

    # Step 1: send text task to A2A agent — it runs all 3 MCP1 tools internally
    sample_text = "python java python go rust java python scala python"
    print(f"\n[A2A] Delegating recommendation pipeline for: '{sample_text}'")
    result = await a2a_client.run_full_pipeline(sample_text)

    print(f"\n  word_counts : {result.get('word_counts')}")
    print(f"  counts      : {result.get('counts')}")
    print(f"  html (first 300 chars): {result.get('html', '')[:300]}")

    # Save HTML output
    with open("output_method3.html", "w") as f:
        f.write(result.get("html", ""))
    print("\n  HTML saved to output_method3.html")


# ──────────────────────────────────────────────────────────────────────────────
# Method 4: Mixed — math from MCP2 directly + recommendation via A2A
# Use case: real-world scenario where one request needs both capabilities
# ──────────────────────────────────────────────────────────────────────────────
async def method4_mixed():
    """
    Real-world scenario: use MCP2 for math, A2A for recommendation, combine results.
    """
    print("\n" + "="*60)
    print("METHOD 4: Mixed (MCP2 math + A2A recommendation combined)")
    print("="*60)

    math_client = MathMCPClient()
    a2a_client = RecommendationAgentClient()

    # Get word frequency via A2A
    text = "apple banana apple orange apple banana grape"
    result = await a2a_client.run_full_pipeline(text)
    word_counts = result.get("word_counts", {})

    # Use MCP2 math to compute something with the counts
    counts_list = list(word_counts.values())  # e.g. [3, 2, 1, 1]
    avg = await math_client.average(counts_list)

    print(f"\n  word_counts     : {word_counts}")
    print(f"  count values    : {counts_list}")
    print(f"  average (MCP2)  : {avg}")
    print(f"  total (from A2A): {result.get('counts')}")


# ──────────────────────────────────────────────────────────────────────────────
# Method 5: REVERSE A2A — MCP1 caller delegates math to MCP2 via A2A
# Use case: recommendation pipeline needs average frequency → calls MathAgent
# Direction: MCP1 side → A2A client → MathAgent A2A server (port 8004) → MCP2 tools
# ──────────────────────────────────────────────────────────────────────────────
async def method5_reverse_a2a():
    """
    REVERSE A2A direction: MCP1 (recommendation) caller needs math.
    Instead of adding math tools to MCP1, it delegates via A2A to MathAgent.

    Flow:
      MCP1 client runs recommendation pipeline
      → word_counts produced → need average frequency
      → delegates average() to MathAgent via A2A (port 8004)
      → MathAgent internally uses MCP2 math tools
    """
    print("\n" + "="*60)
    print("METHOD 5: Reverse A2A (MCP1 caller → A2A → MCP2 math tools)")
    print("="*60)

    # Step 1: MCP1 recommendation — get word frequency
    mcp1_client = RecommendationMCPClient()
    text = "python java python go rust java python scala python go"

    print(f"\n[MCP1] Processing text: '{text}'")
    word_counts = await mcp1_client.process_text(text)
    print(f"  word_counts: {word_counts}")

    # Step 2: Need average frequency — MCP1 does NOT have math tools
    # So MCP1 caller delegates to MathAgent via A2A (reverse direction)
    math_a2a = MathAgentClient()   # A2A client pointing to port 8004

    # Discover MathAgent capabilities first
    print("\n[A2A] MCP1 discovering MathAgent capabilities...")
    card = await math_a2a.discover()
    print(f"      Agent: {card['name']}, Skills: {[s['id'] for s in card['skills']]}")

    # Extract frequency values from word_counts dict
    freq_values = list(word_counts.values())   # e.g. [4, 2, 1, 2, 1]

    # Delegate average computation to MCP2 via A2A
    print(f"\n[A2A] Delegating average({freq_values}) to MathAgent...")
    avg_freq = await math_a2a.average(freq_values)
    print(f"  average frequency = {avg_freq}")

    # Also delegate a power operation for demo
    total = sum(freq_values)
    print(f"\n[A2A] Delegating power({total}, 2) to MathAgent...")
    squared = await math_a2a.power(total, 2)
    print(f"  total_words^2 = {squared}")

    print(f"\n  Summary:")
    print(f"    word_counts     = {word_counts}")
    print(f"    avg_frequency   = {avg_freq}  (via A2A → MCP2)")
    print(f"    total_words^2   = {squared}   (via A2A → MCP2)")



# ──────────────────────────────────────────────────────────────────────────────
# Main runner — run all test methods
# ──────────────────────────────────────────────────────────────────────────────
async def main():
    print("\n🚀 MCP + A2A Demo — Testing all communication patterns\n")
    print("Make sure these servers are running:")
    print("  python mcp1/server/recommendation_server.py       (port 8001)")
    print("  python mcp2/server/math_server.py                 (port 8002)")
    print("  python a2a/server/recommendation_agent_server.py  (port 8003)")
    print("  python a2a/server/math_agent_server.py            (port 8004)")

    try:
        await method1_direct_mcp1()    # MCP client → MCP1 server direct
    except Exception as e:
        print(f"[method1 ERROR] {e} (is MCP1 server running on port 8001?)")

    try:
        await method2_direct_mcp2()    # MCP client → MCP2 server direct
    except Exception as e:
        print(f"[method2 ERROR] {e} (is MCP2 server running on port 8002?)")

    try:
        await method3_a2a_delegate()   # A2A client → A2A server → MCP1 tools
    except Exception as e:
        print(f"[method3 ERROR] {e} (is A2A server running on port 8003?)")

    try:
        await method4_mixed()          # Both MCP2 math + A2A recommendation
    except Exception as e:
        print(f"[method4 ERROR] {e}")

    try:
        await method5_reverse_a2a()    # MCP1 caller → A2A → MCP2 math tools (reverse)
    except Exception as e:
        print(f"[method5 ERROR] {e} (is MathAgent A2A server running on port 8004?)")

    try:
        await method6_mcp1_calls_mcp2_direct()    # MCP1 caller → A2A → MCP2 math tools (reverse)
    except Exception as e:
        print(f"[method6 ERROR] {e} (is MCP1 to MCP2 tool calling server running on port 8001 to 8002?)")

   
async def method6_mcp1_calls_mcp2_direct():
    """
    MCP1 server has tool_add_from_mcp2 and tool_multiply_from_mcp2 registered.
    These tools internally call MCP2 directly via MCP client (no A2A).
    Caller only talks to MCP1 — MCP2 is hidden inside MCP1's tool.
    """
    print("\n" + "="*60)
    print("METHOD 6: MCP1 → MCP2 direct (no A2A)")
    print("  Flow: client → MCP1(8001) → MCP2(8002)")
    print("="*60)
 
    client = RecommendationMCPClient()   # MCP1 client on port 8001
 
    # Call add via MCP1 which internally calls MCP2
    print(f"\n[MCP1→MCP2] math_tool_add_via_mcp2(10, 25)")
    result = await client.math_tool_add_via_mcp2(10, 25)
    print(f"  Result: {result}")         # 35.0
 
    print("\n✅ Done.")


if __name__ == "__main__":
    asyncio.run(main())
 