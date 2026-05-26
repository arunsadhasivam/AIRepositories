# MCP Tools vs Agent Tools (LangChain)

> Both are ways to give an LLM the ability to call external functions.
> The difference is **where the tool lives** and **how it is invoked**.

---

## Quick Answer to All 5 Questions

| Question | MCP Tools | LangChain Agent Tools |
|---|---|---|
| Still used? | Yes — growing standard | Yes — most common today |
| How created? | Defined on a remote MCP server | `@tool` decorator in your Python code |
| Requires LLM? | Yes | Yes |
| Local or remote? | Remote call (HTTP/SSE/stdio) | Local function call (in-process) |
| Extra tokens for tool definition? | Yes — tool schema sent every call | Yes — tool schema sent every call |
| Token caching possible? | Yes — with prompt caching | Yes — with prompt caching |

---

## 1. Are MCP Tools Still Used or Only Agent Tools?

**Both are actively used.** Neither is deprecated.

| | Status | Trend |
|---|---|---|
| LangChain `@tool` | Active, most common | Stable — default for most teams |
| MCP Tools | Active, newer standard | Growing — pushed by Anthropic, adopted by Claude, Cursor, VS Code |

**When each is used:**

| Use Case | Use LangChain `@tool` | Use MCP Tool |
|---|---|---|
| Tool only your app needs | ✅ | ❌ |
| Tool shared across multiple apps | ❌ | ✅ |
| Quick prototype | ✅ | ❌ |
| Tool lives in a separate service/process | ❌ | ✅ |
| Tool needs to be discovered at runtime | ❌ | ✅ |
| Team building a tool marketplace/registry | ❌ | ✅ |
| You are building only one LangChain app | ✅ | ❌ |

**Simple example:**
- Your company has a `search_orders` tool used by 5 different AI apps → **MCP server** (define once, all apps connect)
- You are building one RAG chatbot and need a `search_knowledge_base` tool → **LangChain `@tool`** (define locally, ship fast)

---

## 2. How to Create and Invoke Tools — and How LLM Uses Them

### LangChain Agent Tool — Create and Invoke

**Step 1: Define the tool**
```python
from langchain.tools import tool

@tool
def search_orders(order_id: str) -> str:
    """Search for an order by ID and return its status."""
    # your database call here
    return db.query(f"SELECT * FROM orders WHERE id = {order_id}")
```

**Step 2: Bind tools to LLM and create agent**
```python
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

# LLM + tools + prompt → agent
agent = create_openai_functions_agent(llm, [search_orders], prompt)

# AgentExecutor runs the think → call → observe loop
executor = AgentExecutor(agent=agent, tools=[search_orders])
```

**Step 3: Invoke**
```python
result = executor.invoke({"input": "What is the status of order 123?"})
```

**What happens internally:**
```
1. User input sent to LLM with tool schema
2. LLM responds: "I need to call search_orders(order_id='123')"
3. AgentExecutor calls your local Python function search_orders('123')
4. Result returned to LLM
5. LLM generates final answer
```

---

### MCP Tool — Create and Invoke

**Step 1: Define tool on MCP server (separate Python process)**
```python
# orders_mcp_server.py — runs as a separate server
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("orders-server")

@server.tool()
async def search_orders(order_id: str) -> str:
    """Search for an order by ID and return its status."""
    return db.query(f"SELECT * FROM orders WHERE id = {order_id}")

# Run the MCP server
async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write)
```

**Step 2: Connect to MCP server and load tools into LangChain**
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

server_params = StdioServerParameters(
    command="python",
    args=["orders_mcp_server.py"]
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:

        # MCP tools converted to LangChain tool format
        tools = await load_mcp_tools(session)

        # From here — identical to LangChain agent tools
        agent = create_openai_functions_agent(llm, tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools)
        result = await executor.ainvoke({"input": "What is the status of order 123?"})
```

**What happens internally:**
```
1. User input sent to LLM with tool schema
2. LLM responds: "I need to call search_orders(order_id='123')"
3. AgentExecutor calls MCP client → HTTP/stdio call → MCP server executes function
4. Result returned across the wire → back to AgentExecutor → back to LLM
5. LLM generates final answer
```

---

## 3. Both Require LLM to Execute — How It Works

**Yes — in both cases the LLM decides which tool to call. It does not call the tool itself.**

```
You                LLM                 AgentExecutor          Tool
 │                  │                        │                  │
 │── "find order"──▶│                        │                  │
 │                  │── tool schema sent ───▶│                  │
 │                  │◀─ "call search_orders"─│                  │
 │                  │                        │──call function──▶│
 │                  │                        │◀─── result ──────│
 │                  │◀── result sent ────────│                  │
 │◀─ final answer ──│                        │                  │
```

**The LLM only does two things:**
1. Looks at tool schemas and decides which tool to call with which parameters
2. Takes the tool result and generates the final answer

**AgentExecutor does the actual calling** — whether that is a local function or a remote MCP server.

---

## 4. Local vs Remote Call

| | LangChain `@tool` | MCP Tool |
|---|---|---|
| Call type | Local — in-process Python function | Remote — cross-process via HTTP/SSE/stdio |
| Latency | ~0ms overhead | Network latency (localhost: ~1ms, remote: ~10-100ms) |
| Failure modes | Python exception | Network timeout, connection error, server down |
| Scaling | Scales with your app process | Scales independently as its own service |
| Deployment | Part of your app | Separate server deployment |

**Simple analogy:**

| | Like |
|---|---|
| LangChain `@tool` | Calling a method on the same Java class |
| MCP Tool | Calling a REST API on another microservice |

---

## 5. Tool Schema Tokens — Do Tools Add Extra Tokens? Can You Cache Them?

### Yes — Tool Definitions Cost Tokens Every Call

Every time you call the LLM, the **tool schema (name, description, parameters)** is sent as part of the prompt.

```
What gets sent to LLM every single request:
┌─────────────────────────────────────┐
│ System prompt          (~500 tokens)│
│ Tool schema × N tools  (~200 tokens │
│                         per tool)   │
│ Conversation history   (~500 tokens)│
│ User query             (~50 tokens) │
└─────────────────────────────────────┘
```

**Example cost of tool schemas:**
| Tools | Approx Tokens per Tool | Total Added |
|---|---|---|
| 1 tool | ~150–200 tokens | ~200 tokens |
| 5 tools | ~150–200 tokens each | ~1,000 tokens |
| 20 tools | ~150–200 tokens each | ~4,000 tokens |

> Rule: **Every tool you register adds tokens to every LLM call** — even if that tool is never called.

---

### Can You Cache Tool Tokens? Yes — Prompt Caching

Both MCP tools and LangChain tools support **prompt caching** (e.g. Anthropic prompt caching, OpenAI prompt caching).

**How it works:**
```
First request:
System prompt + tool schemas → sent to LLM → cached on provider side
                                              (tokens billed at full rate)

Second request (same system + tools):
System prompt + tool schemas → cache HIT → not reprocessed
                                           (tokens billed at ~10% rate)
User query only → processed fresh → full token cost
```

**Result of caching:**

| | Without Cache | With Cache |
|---|---|---|
| System prompt (500 tokens) | Billed every call | Billed once, ~10% after |
| Tool schemas (1000 tokens) | Billed every call | Billed once, ~10% after |
| User query (50 tokens) | Billed every call | Always billed (changes every call) |
| Tool result tokens | Billed every call | Always billed (changes every call) |

**Important:** Tool schemas are ideal for caching because they **never change between requests**.

---

### Does Caching Prevent Tool Execution Tokens?

**No.** Caching only saves the cost of re-reading the tool schema.

```
Cached:    system prompt + tool definitions  → cheap
Not cached: user query + tool result + LLM response → always full cost
```

When a tool is actually called:
- Tool result tokens → always billed (new content every time)
- LLM response tokens → always billed (new content every time)

**Caching reduces input token cost. It does not reduce execution cost.**

---

### MCP vs LangChain Tool Token Behavior

| | LangChain `@tool` | MCP Tool |
|---|---|---|
| Tool schema sent to LLM? | Yes — on every call | Yes — on every call (after load) |
| Schema cacheable? | Yes | Yes |
| Tool result tokens? | Yes — billed per call | Yes — billed per call |
| Difference in token cost? | None | None |

**MCP tools and LangChain tools cost exactly the same tokens** once loaded —
because after `load_mcp_tools()` converts MCP tools to LangChain format,
the LLM sees identical tool schemas either way.

---

## Full Comparison Summary

| Question | LangChain `@tool` | MCP Tool |
|---|---|---|
| Still used? | Yes | Yes — growing |
| Where defined? | Your Python code | Separate MCP server |
| How invoked? | AgentExecutor → local function | AgentExecutor → MCP client → remote server |
| Requires LLM? | Yes — LLM decides which tool | Yes — LLM decides which tool |
| Local or remote? | Local (in-process) | Remote (cross-process) |
| Tool schema tokens? | Yes — per call | Yes — per call |
| Cacheable? | Yes | Yes |
| Token cost difference? | Same | Same |
| Best for | Single app, fast dev | Shared tools, multi-app, microservices |
