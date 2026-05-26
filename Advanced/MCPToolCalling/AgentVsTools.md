## Tools vs Agents — Not the Same Thing

> Both MCP tools and LangChain `@tool` are just tools — not agents.
> This is a common confusion worth clarifying.

```
Tools   →  functions the LLM can call
Agent   →  LLM + tools + loop (think → act → observe)
```

| Term | What It Is |
|---|---|
| Tool — LangChain `@tool` | Just a function — does one thing — no LLM involved |
| Tool — MCP | Just a function on a remote server — no LLM involved |
| Agent | LLM + tools + execution loop combined |
| AgentExecutor | The runtime that runs the agent loop — not a tool |
| LangGraph | The framework that builds the agent — not a tool |

### Simple Example

```
Tool alone:
  search_orders("123")  → returns order status
  (just a function — no LLM involved)

Agent:
  User: "find order 123 and check if it shipped"
  → LLM decides: call search_orders
  → Tool executes
  → LLM decides: call check_shipping
  → Tool executes
  → LLM generates final answer
  (LLM + tools + loop = agent)
```

### Correct Way to Say It

| Wrong | Correct |
|---|---|
| "MCP tools are agents" | "MCP tools are tools used **by** an agent" |
| "LangChain tools are agents" | "LangChain tools are tools used **by** an agent" |
| "AgentExecutor is a tool" | "AgentExecutor is the agent runtime that **runs** tools" |
| "LangGraph is a tool" | "LangGraph is the framework that **builds** the agent" |

> **Tools are what an agent uses.**
> **Agent is the thing that decides which tool to call and when.**
> LangGraph is what builds the agent in prod.
