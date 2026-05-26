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

**Step 3: Invoke — 4 Ways**

#### Way 1 — AgentExecutor (Auto Loop)
```python
from langchain.agents import create_openai_functions_agent, AgentExecutor

agent = create_openai_functions_agent(llm, [search_orders], prompt)
executor = AgentExecutor(agent=agent, tools=[search_orders])

# single invoke — AgentExecutor loops automatically
result = executor.invoke({"input": "What is the status of order 123?"})
```
> ✅ Least code. ❌ No control between steps. Best for: prototypes.

---

#### Way 2 — bind_tools + LCEL Chain (Modern)
```python
llm_with_tools = llm.bind_tools([search_orders])
chain = prompt | llm_with_tools

# returns AIMessage — you check if tool was called
response = chain.invoke({"input": "What is the status of order 123?"})

if response.tool_calls:
    tool_result = search_orders.invoke(response.tool_calls[0]["args"])
```
> ✅ Modern LCEL style. ✅ Works with Ollama. ❌ You handle tool result manually. Best for: single tool call, custom logic.

---

#### Way 3 — bind_tools + Manual Loop (Full Control)
```python
from langchain_core.messages import HumanMessage, ToolMessage

llm_with_tools = llm.bind_tools([search_orders])
messages = [HumanMessage(content="What is the status of order 123?")]

tools_map = {"search_orders": search_orders}

while True:
    response = llm_with_tools.invoke(messages)
    messages.append(response)

    if not response.tool_calls:
        break  # LLM is done

    for tool_call in response.tool_calls:
        result = tools_map[tool_call["name"]].invoke(tool_call["args"])
        messages.append(ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"]
        ))

final_answer = messages[-1].content
```


---

#### Way 4 — LangGraph (Recommended for Prod)
```python
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

graph = create_react_agent(llm, [search_orders])
result = graph.invoke({"messages": [HumanMessage(content="What is the status of order 123?")]})
```
> ✅ Best for complex flows. ✅ Native HITL. ✅ State management. ❌ Steeper learning curve. Best for: multi-step, multi-agent, prod.

---

**What happens internally (all 4 ways — same flow):**
```
1. User input sent to LLM with tool schema
2. LLM responds: "I need to call search_orders(order_id='123')"
3. Tool executor calls your local Python function search_orders('123')
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
        # load MCP tools — converts to LangChain tool format
        tools = await load_mcp_tools(session)
```

**Step 3: Invoke — same 4 ways as LangChain tools**

#### Way 1 — AgentExecutor (Auto Loop)
```python
agent = create_openai_functions_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)

result = await executor.ainvoke({"input": "What is the status of order 123?"})
```
> ✅ Least code. ❌ No control between steps. Best for: prototypes.

---

#### Way 2 — bind_tools + LCEL Chain (Modern)
```python
llm_with_tools = llm.bind_tools(tools)
chain = prompt | llm_with_tools

response = await chain.ainvoke({"input": "What is the status of order 123?"})

if response.tool_calls:
    # tools here are MCP tools — remote call happens here
    tool_result = await tools[0].ainvoke(response.tool_calls[0]["args"])
```
> ✅ Modern LCEL style. ✅ Works with Ollama. ❌ You handle tool result manually. Best for: single tool call.

---

#### Way 3 — bind_tools + Manual Loop (Full Control)
```python
from langchain_core.messages import HumanMessage, ToolMessage

llm_with_tools = llm.bind_tools(tools)
tools_map = {t.name: t for t in tools}  # MCP tools mapped by name
messages = [HumanMessage(content="What is the status of order 123?")]

while True:
    response = await llm_with_tools.ainvoke(messages)
    messages.append(response)

    if not response.tool_calls:
        break

    for tool_call in response.tool_calls:
        # this triggers the remote MCP server call
        result = await tools_map[tool_call["name"]].ainvoke(tool_call["args"])
        messages.append(ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"]
        ))

final_answer = messages[-1].content
```


---

#### Way 4 — LangGraph (Recommended for Prod)
```python
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

# MCP tools passed directly — LangGraph handles remote calls
graph = create_react_agent(llm, tools)
result = await graph.ainvoke({"messages": [HumanMessage(content="What is the status of order 123?")]})
```
> ✅ Best for complex flows. ✅ Native HITL. ✅ State management. Best for: multi-step prod agents.

---

**What happens internally (all 4 ways — MCP remote call):**
```
1. User input sent to LLM with tool schema
2. LLM responds: "I need to call search_orders(order_id='123')"
3. Tool executor → MCP client → HTTP/stdio → MCP server executes function
4. Result returned across the wire → back to executor → back to LLM
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

## Different Ways to Invoke Tools

### Why Do Different Ways Exist?

Different ways exist because **not every situation needs the same level of control.**

| Situation | Problem With One-Size-Fits-All | Solution |
|---|---|---|
| Prototype in 10 min | Writing a full graph is overkill | AgentExecutor — 3 lines |
| Single tool, no loop | AgentExecutor runs a loop you don't need | bind_tools + LCEL — clean and direct |
| Prod with guardrails | No place to insert logic between steps | Manual loop — you control every step |
| Complex multi-step | Manual loop gets messy and error-prone | LangGraph — structured graph with nodes |

> Think of it like Java: you can use a `while` loop, an `Iterator`, a `Stream`, or a `CompletableFuture` — all iterate, but each fits a different situation.

---

### LLM Vendor Compatibility — Which Way Works With Which LLM?

**Simple Rule:**
```
All 4 ways work with ALL LLM providers
        EXCEPT
Way 1 AgentExecutor → OpenAI / Azure OpenAI only
```

| Way | OpenAI / Azure OpenAI | Anthropic Claude | Ollama (local) | Google Gemini |
|---|---|---|---|---|
| Way 1 — AgentExecutor | ✅ | ❌ Not recommended | ❌ Does not work | ❌ Not recommended |
| Way 2 — bind_tools + LCEL | ✅ | ✅ | ✅ | ✅ |
| Way 3 — Manual Loop | ✅ | ✅ | ✅ | ✅ |
| Way 4 — LangGraph | ✅ | ✅ | ✅ | ✅ |

---

**Ollama — Extra Rule (not all models support tools):**

```
Ollama models WITH tool calling support   → Way 2, 3, 4 work ✅
  mistral, llama3.1, llama3.2, qwen2.5, phi3

Ollama models WITHOUT tool calling        → no tool calling at all ❌
  nomic-embed-text  (embedding only — no chat, no tools)
  mxbai-embed-large (embedding only — no chat, no tools)
```

> Rule: check `ollama show <model>` — if it lists `tools` capability → Ways 2, 3, 4 work.

---

**Anthropic Claude details:**
- Ways 2, 3, 4 work via `langchain_anthropic.ChatAnthropic`
- Claude has native tool use — works cleanly with `bind_tools()` and LangGraph
- Way 1 AgentExecutor uses OpenAI function-calling format internally — **avoid with Claude**

---

**Key rule:**
> `bind_tools()` supported by LLM → Way 2, 3, 4 all work — any provider.
> Way 1 AgentExecutor → **OpenAI / Azure OpenAI only.**

---

There are 4 ways to invoke tools in LangChain — works the same for both LangChain `@tool` and MCP tools.

---

### Way 1 — AgentExecutor (Classic Loop)

> ⚠️ **LLM Vendor:** Works best with **OpenAI / Azure OpenAI only**.
> Uses `create_openai_functions_agent` which relies on OpenAI function-calling format.
> **Does NOT work reliably with Ollama or Anthropic Claude** via this exact setup.
> For Ollama or Claude → use Way 2, 3, or 4 instead.

```python
from langchain.agents import create_openai_functions_agent, AgentExecutor

agent = create_openai_functions_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

result = executor.invoke({"input": "find order 123"})
```

**How it works:**
```
invoke() → LLM thinks → calls tool → result → LLM thinks → calls tool → final answer
           (AgentExecutor loops automatically until done)
```

| Pros | Cons |
|---|---|
| Auto handles multi-step tool calls | Less control over each step |
| Built-in error handling and retries | Hard to intercept between steps |
| Verbose mode shows full reasoning | Older style — being replaced by LangGraph |
| Simple to set up | Can run infinite loops if no stop condition |
| | ⚠️ OpenAI / Azure only — not Ollama, not Claude |

**Best for:** Quick prototypes using OpenAI or Azure OpenAI only.

---

### Way 2 — `llm.bind_tools()` + LCEL Chain (Modern Style)

> ✅ **LLM Vendor:** Works with **any LLM that supports `bind_tools()`**
> OpenAI ✅ | Azure OpenAI ✅ | Anthropic Claude ✅ | Ollama ✅ (mistral, llama3.1, qwen2.5)
> ⚠️ Ollama embedding-only models like `nomic-embed-text` — **no tool calling support**

```python
# bind tools directly to LLM
llm_with_tools = llm.bind_tools(tools)

# LCEL chain — prompt | llm
chain = prompt | llm_with_tools

# invoke — returns AIMessage with tool_calls if LLM wants a tool
response = chain.invoke({"input": "find order 123"})

# YOU check and handle the tool call manually
if response.tool_calls:
    for tool_call in response.tool_calls:
        tool_name = tool_call["name"]          # which tool LLM chose
        tool_args = tool_call["args"]           # what args LLM passed
        tool_result = tools_map[tool_name].invoke(tool_args)
        # send result back to LLM yourself
```

**How it works:**
```
chain.invoke() → LLM responds with tool_call intent
YOU check response.tool_calls
YOU execute the tool
YOU send result back to LLM
YOU decide when to stop
```

| Pros | Cons |
|---|---|
| Works with OpenAI, Azure, Claude, Ollama | You write the tool result handling |
| Modern LCEL style | Easy to forget edge cases |
| Can add logic between steps | Need to handle multi-step manually |
| Can add observability at each step | |

**Best for:** Single tool call with custom logic. Any LLM vendor.

---

### Way 3 — `llm.bind_tools()` + Manual Loop (Full Control)

> ✅ **LLM Vendor:** Works with **any LLM that supports `bind_tools()`**
> OpenAI ✅ | Azure OpenAI ✅ | Anthropic Claude ✅ | Ollama ✅ (tool-capable models only)
> Same rule as Way 2 — if the model supports `bind_tools()` this works.

```python
llm_with_tools = llm.bind_tools(tools)
messages = [HumanMessage(content="find order 123 and check if it shipped")]

# manual think → act → observe loop
while True:
    response = llm_with_tools.invoke(messages)
    messages.append(response)

    # no more tool calls → LLM is done
    if not response.tool_calls:
        break

    # execute each tool call
    for tool_call in response.tool_calls:
        tool_result = tools_map[tool_call["name"]].invoke(tool_call["args"])
        messages.append(ToolMessage(
            content=str(tool_result),
            tool_call_id=tool_call["id"]
        ))

final_answer = messages[-1].content
```

**How it works:**
```
You control the full loop:
  → call LLM
  → if tool_calls: execute tools, append results, loop again
  → if no tool_calls: done
```

| Pros | Cons |
|---|---|
| Maximum control over every step | Most code to write and maintain yourself |
| Works with OpenAI, Azure, Claude, Ollama | You are responsible for all edge cases |
| Can add guardrails between each step | Risk of infinite loop if break condition missed |
| Can inject HITL at any point | Not recommended if LangGraph is an option |

> ⚠️ **Best for:** Transitional step — use this only if your team is **not yet on LangGraph**.
> Once on LangGraph — Way 4 replaces this with less code and more structure.
> Do NOT use Way 3 and call it "best for prod" — Way 4 LangGraph is better for prod in every way.

---

### Way 4 — LangGraph (Modern Agentic Orchestration)

> ✅ **LLM Vendor:** Works with **any LLM that supports `bind_tools()`**
> OpenAI ✅ | Azure OpenAI ✅ | Anthropic Claude ✅ | Ollama ✅ (tool-capable models only)
> LangGraph internally calls `llm.bind_tools()` — same vendor rules as Way 2 and 3.

```python
from langgraph.prebuilt import create_react_agent

# LangGraph manages the loop as a state graph
graph = create_react_agent(llm, tools)

result = graph.invoke({"messages": [HumanMessage(content="find order 123")]})
```

Or custom graph:
```python
from langgraph.graph import StateGraph, MessagesState

graph = StateGraph(MessagesState)
graph.add_node("llm", call_llm)
graph.add_node("tools", call_tools)
graph.add_conditional_edges("llm", should_call_tool)
graph.add_edge("tools", "llm")

app = graph.compile()
result = app.invoke({"messages": [HumanMessage(content="find order 123")]})
```

**How it works:**
```
State graph with nodes:
  llm node → decides tool
  tools node → executes tool
  conditional edge → loop or stop
  (LangGraph manages state between nodes)
```

| Pros | Cons |
|---|---|
| Works with OpenAI, Azure, Claude, Ollama | Steeper learning curve |
| Best for complex multi-agent workflows | More setup than AgentExecutor |
| Built-in state management | Overkill for simple single-tool use |
| Supports parallel tool calls | |
| Supports human-in-the-loop natively | |
| Recommended by LangChain team for prod | |
| Checkpointing — resume from any step | |

**Best for:** Complex prod agents, multi-agent pipelines, workflows that need HITL, branching, or parallel execution. Any LLM vendor.

---

## Which Way — For Which Purpose

| Purpose | Best Way | LLM Vendor | Why |
|---|---|---|---|
| Quick prototype / demo | AgentExecutor | OpenAI / Azure only | Least code, works immediately |
| Single tool call, no loop | `bind_tools()` + LCEL | Any | Clean, no loop overhead |
| Need control between steps | Manual loop | Any | You insert guardrails/logging |
| Production RAG pipeline | LangGraph Custom Graph | Any | Full control, structured, prod-ready |
| Multi-agent / parallel tools | LangGraph | Any | Built for this |
| Human-in-the-loop required | LangGraph | Any | Native HITL support |
| Using Ollama local LLM | Way 2, 3, or 4 only | Ollama only | AgentExecutor does NOT work with Ollama |
| Using Anthropic Claude | Way 2, 3, or 4 | Anthropic only | Claude has native tool use via `bind_tools()` |
| MCP tools | Any of the 4 ways | Any | `load_mcp_tools()` first — then identical |

---

## MCP Tools — Which Invocation Way Works

```python
# Step 1: Load MCP tools — same for ALL 4 ways
tools = await load_mcp_tools(session)

# Step 2: Use any invocation style — identical from here
# Way 1 — AgentExecutor
executor = AgentExecutor(agent=create_openai_functions_agent(llm, tools, prompt), tools=tools)

# Way 2 — bind_tools LCEL
chain = prompt | llm.bind_tools(tools)

# Way 3 — manual loop
llm_with_tools = llm.bind_tools(tools)

# Way 4 — LangGraph
graph = create_react_agent(llm, tools)
```

> Once MCP tools are loaded via `load_mcp_tools()` they become standard LangChain tools.
> All 4 invocation ways work identically with MCP tools and local `@tool` tools.

---

## Advantages vs Disadvantages Summary

| Way | Advantage | Disadvantage | Use When | Prod? |
|---|---|---|---|---|
| AgentExecutor | Simple, auto loop, least code | No step control, OpenAI only, older style | Prototypes only | ❌ |
| bind_tools + LCEL | Modern, clean, any LLM vendor | You handle tool result manually | Single step, no loop needed | ⚠️ Simple only |
| bind_tools + manual loop | Full control, any LLM vendor | Most code to write — you own every edge case | Transitional — use until team adopts LangGraph | ⚠️ Not preferred |
| LangGraph Custom Graph | Less code than manual loop, structured, guardrails, HITL, checkpointing, any LLM vendor | Steeper learning curve | Everything prod | ✅ Recommended |

> **Correction from earlier:** Way 3 manual loop is NOT "best for prod."
> It was listed that way because it gives control — but LangGraph gives the same control
> with less code and more structure. Way 4 LangGraph is the correct prod choice.

---

## LangGraph — Production Grade Tool Calling (Recommended)

> LangGraph is the recommended way for production.
> It works identically for both LangChain `@tool` and MCP tools.
> The only difference is how you load the tools — everything else is the same.

---

### LangGraph Flow

```
User Input
    ↓
[llm_node]  → LLM decides: call tool or answer?
    ↓
[conditional edge] → tool_calls exist? → YES → [tools_node]
                                       → NO  → END
    ↓
[tools_node] → executes tool (local or MCP remote)
    ↓
back to [llm_node] → LLM sees result → decides again
    ↓
END → final answer
```

---

### Way 1 — LangGraph Prebuilt (Simplest Prod Setup)

**With LangChain `@tool`:**
```python
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from langchain.tools import tool

# Step 1: define local tool
@tool
def search_orders(order_id: str) -> str:
    """Search for an order by ID."""
    return db.query(order_id)

# Step 2: create react agent — LangGraph manages the loop
graph = create_react_agent(llm, tools=[search_orders])

# Step 3: invoke
result = graph.invoke({
    "messages": [HumanMessage(content="find order 123")]
})

print(result["messages"][-1].content)  # final answer
```

**With MCP Tools — only Step 1 changes:**
```python
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Step 1: load MCP tools — connects to remote MCP server
server_params = StdioServerParameters(
    command="python",
    args=["orders_mcp_server.py"]
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        tools = await load_mcp_tools(session)  # MCP → LangChain format

        # Step 2: identical from here — LangGraph does not care where tools came from
        graph = create_react_agent(llm, tools=tools)

        # Step 3: invoke
        result = await graph.ainvoke({
            "messages": [HumanMessage(content="find order 123")]
        })

        print(result["messages"][-1].content)
```

---

### Way 2 — LangGraph Custom Graph (Full Prod Control)

Use this when you need guardrails, observability, or HITL between steps.

**Works identically for both LangChain tools and MCP tools — only tool loading differs.**

```python
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage
from typing import Literal

# --- tool loading ---
# LangChain tool:  tools = [search_orders]
# MCP tool:        tools = await load_mcp_tools(session)

# Step 1: bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# Step 2: define LLM node
def llm_node(state: MessagesState):
    # → add Layer 2 input guardrail here before LLM call
    response = llm_with_tools.invoke(state["messages"])
    # → add Layer 2 output guardrail here after LLM call
    # → log to Langfuse here (Layer 3 observability)
    return {"messages": [response]}

# Step 3: define tool node — LangGraph executes tools here
# ToolNode handles both local @tool and MCP tools identically
tool_node = ToolNode(tools)

# Step 4: conditional edge — should we call a tool or stop?
def should_call_tool(state: MessagesState) -> Literal["tools", END]:
    last_message = state["messages"][-1]

    if last_message.tool_calls:
        # → add Layer 1 tool validation here (budget, schema, policy)
        # → add Layer 4 HITL check here (blast radius, confidence)
        return "tools"

    return END

# Step 5: build the graph
graph_builder = StateGraph(MessagesState)

graph_builder.add_node("llm",   llm_node)
graph_builder.add_node("tools", tool_node)

graph_builder.set_entry_point("llm")

graph_builder.add_conditional_edges(
    "llm",
    should_call_tool  # decides: call tool or end
)

graph_builder.add_edge("tools", "llm")  # after tool → back to LLM

graph = graph_builder.compile()

# Step 6: invoke
result = graph.invoke({
    "messages": [HumanMessage(content="find order 123")]
})

print(result["messages"][-1].content)
```

**Where to plug in your prod layers:**
```
llm_node()
    → BEFORE llm call  : Layer 2 input guardrail, PII masking
    → AFTER llm call   : Layer 2 output guardrail, Langfuse trace

should_call_tool()
    → BEFORE tool call : Layer 1 budget check, schema validation, RBAC
    → BEFORE tool call : Layer 4 HITL — irreversible? blast radius? low confidence?

tool_node
    → executes tool    : local @tool OR MCP remote call — same node
```

---

### Way 3 — LangGraph with Checkpointing (Resume on Failure)

```python
from langgraph.checkpoint.memory import MemorySaver

# add checkpointer — saves state after every node
checkpointer = MemorySaver()
graph = graph_builder.compile(checkpointer=checkpointer)

# invoke with thread_id — can resume this exact conversation later
config = {"configurable": {"thread_id": "order-session-123"}}

result = graph.invoke(
    {"messages": [HumanMessage(content="find order 123")]},
    config=config
)

# if it fails mid-way — resume from last checkpoint
result = graph.invoke(
    {"messages": [HumanMessage(content="continue")]},
    config=config  # same thread_id — picks up where it left off
)
```

> ✅ If LLM call fails mid-pipeline → resumes from last saved state
> ✅ User can pause and resume a long-running workflow
> ✅ Works with both LangChain tools and MCP tools

---

### LangGraph Prod Summary

| Feature | Prebuilt `create_react_agent` | Custom Graph |
|---|---|---|
| Setup effort | Minimal | More code |
| Guardrails between steps | ❌ Hard to add | ✅ Add anywhere |
| Observability per step | ❌ Hard to add | ✅ Add in each node |
| HITL support | ❌ | ✅ In conditional edge |
| Checkpointing | ✅ Add checkpointer | ✅ Add checkpointer |
| Works with LangChain tools | ✅ | ✅ |
| Works with MCP tools | ✅ | ✅ |
| Best for | Simple prod agent | Full prod pipeline |

---

## Which Way is Preferred for Production — Final Summary

### By Invocation Way

| Way | Prod Ready? | Preferred? | Why |
|---|---|---|---|
| Way 1 — AgentExecutor | ⚠️ Not recommended | ❌ | No step control, older style, being deprecated |
| Way 2 — bind_tools + LCEL | ✅ OK for simple | ⚠️ Only if single step | You manage tool result manually — easy to miss edge cases |
| Way 3 — bind_tools + Manual Loop | ✅ Yes | ⚠️ Only if no LangGraph | Full control but you write and maintain all edge case handling yourself |
| Way 4 — LangGraph Custom Graph | ✅ Yes | ✅ **Recommended** | Structured, guardrails pluggable, HITL native, checkpointing, less error-prone |

---

### By Tool Type — Which Invocation to Use in Prod

| Tool Type | Recommended Prod Way | Why |
|---|---|---|
| LangChain `@tool` | **LangGraph Custom Graph** | Full control, guardrails at each node, no boilerplate loop to maintain |
| MCP Tools | **LangGraph Custom Graph** | Same as above — `load_mcp_tools()` then identical LangGraph setup |
| Both mixed together | **LangGraph Custom Graph** | LangGraph ToolNode handles local and MCP tools in the same node |

---

### Decision Tree — What to Use

```
Are you prototyping?
    YES → Way 1 AgentExecutor (fastest to set up)

Are you in prod with a single simple tool call?
    YES → Way 2 bind_tools + LCEL

Are you in prod and need guardrails + observability?
    YES → Do you know LangGraph?
        NO  → Way 3 Manual Loop (for now)
        YES → Way 4 LangGraph Custom Graph ← recommended

Are you in prod with multi-step, multi-agent, or HITL?
    YES → Way 4 LangGraph Custom Graph ← only real option
```

---

### One Line Answer

> **For prod — always LangGraph Custom Graph.**
> Works the same for LangChain `@tool` and MCP tools.
> Gives you guardrails, observability, HITL, and checkpointing
> without writing and maintaining the loop yourself.

---

## Production Usage Split — LangChain `@tool` vs MCP Tools

> Both are prod grade when used with LangGraph.
> The split below reflects real-world adoption as of 2024–2025.

```
LangChain @tool (local)     ████████████████░░░░  70%
MCP Tools                   ████░░░░░░░░░░░░░░░░  30%
```

### Why 70% Still Use LangChain `@tool`
- Existed for years — most teams already built with it
- Simpler setup — no separate server to deploy
- Most tutorials, docs, and examples use `@tool`
- Works perfectly for single-app use cases
- LangGraph works with it out of the box

### Why MCP is Growing Fast (30% → rising)
- Anthropic pushed it as an open standard in late 2024
- Claude Desktop, Cursor, VS Code Copilot all adopted MCP natively
- Teams building **tool registries** shared across multiple AI apps
- Companies want tools decoupled from the AI app itself

### Honest Reality Check

| | LangChain `@tool` | MCP Tools |
|---|---|---|
| Prod apps today | Majority — 70% | Minority — 30% but rising fast |
| New greenfield projects 2025 | Still most common | Increasingly chosen |
| Enterprise multi-app platforms | Less common | Growing preference |
| Startups / single app | Dominant | Rare |
| Tool shared across 5+ apps | Rare | Primary use case |

### Bottom Line — Which to Pick

| Your Situation | Use |
|---|---|
| Building one RAG app | LangChain `@tool` + LangGraph ✅ |
| Building a platform — multiple AI apps share tools | MCP + LangGraph ✅ |
| Your current RAG pipeline (single app) | LangChain `@tool` + LangGraph — right call today |
| Long term as you add more agents | MCP + LangGraph — direction industry is moving |


## Performance — LangChain `@tool` vs MCP Tools

### Key Difference — Local vs Remote Call

```
LangChain @tool   →  in-process function call  →  ~0ms overhead
MCP Tool          →  cross-process remote call  →  ~1ms (local) to ~100ms (remote)
```

This is the **only real performance difference** between the two.
The LLM call, token cost, and LangGraph overhead are identical.

---

### Latency Breakdown Per Tool Call

| Step | LangChain `@tool` | MCP Tool (local server) | MCP Tool (remote server) |
|---|---|---|---|
| LLM decides which tool | Same | Same | Same |
| Tool call overhead | ~0ms | ~1–5ms | ~10–100ms |
| Tool execution time | Depends on your function | Depends on your function | Depends on your function |
| Result back to LLM | ~0ms | ~1–5ms | ~10–100ms |
| LLM generates answer | Same | Same | Same |

> **Tool execution time dominates** — if your tool queries a database (50ms) or calls an API (200ms),
> the MCP overhead (~5ms local) is negligible.

---

### When Performance Difference Actually Matters

| Situation | Impact |
|---|---|
| Tool calls a slow DB / API (>50ms) | MCP overhead irrelevant — DB is the bottleneck |
| Tool is a fast in-memory lookup (<1ms) | MCP adds noticeable overhead — use `@tool` |
| MCP server on same machine (localhost) | Overhead ~1–5ms — negligible |
| MCP server on remote machine | Overhead ~10–100ms — consider if latency-sensitive |
| High frequency tool calls (100+ per request) | MCP overhead compounds — prefer `@tool` |

---

### Performance by Invocation Way

| Way | Performance | Notes |
|---|---|---|
| Way 1 — AgentExecutor | Slowest | Extra abstraction layers, verbose logging overhead |
| Way 2 — bind_tools + LCEL | Fast | Minimal overhead — direct chain |
| Way 3 — Manual loop | Fast | You control everything — no hidden overhead |
| Way 4 — LangGraph | Fast | Small graph state overhead (~1–2ms) — worth it for control |

---

### Bottom Line on Performance

```
LangGraph + @tool    →  fastest overall
LangGraph + MCP      →  ~1–5ms slower per tool call (localhost MCP)
                         ~10–100ms slower per tool call (remote MCP)

In practice:
  LLM call         = 500ms – 3000ms   (dominates everything)
  DB / API call    = 50ms – 500ms     (second biggest factor)
  MCP overhead     = 1ms – 100ms      (usually negligible)
```

> **For your RAG pipeline** — LLM call is 500ms+.
> MCP overhead of 5ms is less than 1% of total latency.
> Performance is NOT a reason to choose one over the other.


---

## SOA Analogy — Static Stub vs Dynamic Invocation

> Same trade-off you know from SOA / Java web services — directly applies here.

### Mapping Table

| SOA / Java | Tool Calling Equivalent |
|---|---|
| Static stub (compile-time bound) | LangChain `@tool` — defined in your code, fixed at deploy time |
| Dynamic invocation interface (DII) | MCP Tools — discovered from server at runtime via `load_mcp_tools()` |
| WSDL contract | Tool schema (name, description, parameters) sent to LLM |
| Service bus / ESB routing | AgentExecutor / LangGraph — routes LLM decision to correct tool |
| Client calls service | LLM decides → executor calls tool |
| Service registry (UDDI) | MCP server — tools registered and discovered dynamically |
| JAX-WS generated stub | LangChain `@tool` decorator — fixed interface known at compile time |
| JAX-WS DII `Dispatch` | `load_mcp_tools()` — loads tool interface dynamically at runtime |

---

### Static Stub vs DII — Same Advantages Carry Over

| SOA Advantage | Static Stub → LangChain `@tool` | DII → MCP Tools |
|---|---|---|
| Speed | Fast — compile-time bound, no discovery overhead | Slightly slower — runtime discovery + network call |
| Simplicity | Simpler — interface visible in your code | More setup — server to deploy and maintain |
| Debuggability | Easy — tool defined in your codebase, full stack trace | Harder — error may be on remote MCP server |
| Coupling | Tightly coupled — tool change = app redeploy | Loosely coupled — tool server updated independently |
| Reusability | Low — tied to one app | High — any app connects to same MCP server |
| Runtime flexibility | None — tools fixed at deploy | High — tools discovered and changed without app redeploy |
| Multi-app sharing | Requires copy-paste to each app | Single MCP server — all apps connect |
| Failure impact | Tool failure = in-process exception | Tool failure = network error, server down |

**Bottom line — same trade-off as SOA:**
> Static stub = `@tool` — simple, fast, tightly coupled, single app
> DII = MCP — flexible, loosely coupled, shared across apps, runtime discovery

---

## Error Handling — What Happens When a Tool Fails

| Way | What Happens When Tool Fails | Who Handles It |
|---|---|---|
| Way 1 — AgentExecutor | Built-in retry — retries the tool call automatically | Framework handles it |
| Way 2 — bind_tools + LCEL | Exception thrown — your code must catch it | You handle it |
| Way 3 — Manual loop | Exception thrown inside loop — your code must catch it | You handle it |
| Way 4 — LangGraph | Add error node in graph — most structured error handling | You define error node |

### LangGraph Error Handling Example
```python
from langgraph.graph import StateGraph, MessagesState, END
from typing import Literal

def should_call_tool(state: MessagesState) -> Literal["tools", END]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

def tool_node_with_error(state: MessagesState):
    try:
        # execute tool — local @tool or MCP remote call
        result = tools_map[state["messages"][-1].tool_calls[0]["name"]].invoke(
            state["messages"][-1].tool_calls[0]["args"]
        )
        return {"messages": [ToolMessage(content=str(result))]}
    except Exception as e:
        # return error to LLM — LLM decides: retry, different tool, or tell user
        return {"messages": [ToolMessage(content=f"Tool failed: {str(e)} — try a different approach")]}

graph_builder.add_node("tools", tool_node_with_error)
graph_builder.add_conditional_edges("llm", should_call_tool)
graph_builder.add_edge("tools", "llm")  # LLM sees error and recovers
```

> **Why LangGraph error handling is best:**
> Error returned to LLM as a message — LLM decides to retry, use a different tool, or tell the user.
> AgentExecutor retries blindly. Manual loop crashes. LangGraph recovers intelligently.

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
| Performance difference? | Faster — ~0ms overhead | ~1–5ms slower (localhost) |
| SOA equivalent | Static stub | Dynamic invocation (DII) |
| Coupling | Tight — deploy with app | Loose — independent server |
| Reusability | Single app | Shared across apps |
| Error handling | Exception in your code | Error node in LangGraph |
| Best for | Single app, fast dev | Shared tools, multi-app, microservices |
| Prod invocation | LangGraph Custom Graph | LangGraph Custom Graph |
