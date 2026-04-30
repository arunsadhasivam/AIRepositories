# Agentic AI: LangGraph, Tools, MCP, A2A (Practical Guide + Working Code)

## 🎯 Goal

Understand how agentic AI works using a simple example (**add & multiply**) with **real LLM-based tool calling (no if-else)**.

---

# 1. What is Agentic AI ✅

Agentic AI means:

* The **LLM decides dynamically**
* It chooses:

  * which tool to use
  * what inputs to pass
  * when to stop

### Example

```
User: "What is 2 + 3?"

LLM decides:
→ Call "add" tool with a=2, b=3
```

👉 No hardcoded logic.

---

# 2. Tools (Core Concept)

```python
def add(a: int, b: int) -> int:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b
```

---

## ✅ When to use tools

* Need accuracy (math, finance)
* Need real-time data (DB/API)
* Avoid hallucination

## ⚖️ Advantages

* Accurate
* Reusable
* Real-world integration

## ❌ Disadvantages

* Integration effort
* Latency (LLM + tool)
* Error handling needed

---

# 3. LangGraph (Workflow Layer)

* Controls execution flow
* Maintains state
* Handles multi-step reasoning

---

## ✅ When to use

* Multi-step workflows
* Stateful agents
* Retry logic

---

# 4. MCP (Model Context Protocol)

* Standard way to **describe tools**
* NOT execution
* NOT API gateway

### Example Schema

```json
{
  "name": "add",
  "description": "Add two numbers",
  "input_schema": {
    "a": "number",
    "b": "number"
  }
}
```

---

## ✅ When to use

* Many tools
* Standardization
* Cross-team usage

---

# 5. A2A (Agent-to-Agent)

Used when:

* Tools are in different services
* Distributed systems

---

# 6. Execution Layer

Real APIs:

```
/api/pdf
/api/text
/api/db
```

---

# 7. LLM Tool Calling (Real Agentic Code) 🚀

## 🔥 Example using OpenAI-style tool calling

```python
from openai import OpenAI
client = OpenAI()

# Define tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "Multiply two numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["a", "b"]
            }
        }
    }
]

# Tool execution logic
def execute_tool(name, args):
    if name == "add":
        return args["a"] + args["b"]
    elif name == "multiply":
        return args["a"] * args["b"]

# User query
messages = [{"role": "user", "content": "What is 4 * 5?"}]

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    tools=tools,
    tool_choice="auto"
)

# LLM decides tool
tool_call = response.choices[0].message.tool_calls[0]

tool_name = tool_call.function.name
tool_args = eval(tool_call.function.arguments)

# Execute tool
result = execute_tool(tool_name, tool_args)

print("Result:", result)
```

---

## 🔍 What happens here

```
User → LLM
LLM → decides "multiply"
LLM → sends arguments {a:4, b:5}
System → executes function
Result → returned
```

👉 THIS is true agentic behavior

---

# 8. LangGraph Version (Agent Flow)

```python
from langgraph.graph import StateGraph

class State(dict):
    pass

def agent_node(state):
    query = state["input"]
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": query}],
        tools=tools
    )
    
    tool_call = response.choices[0].message.tool_calls[0]
    name = tool_call.function.name
    args = eval(tool_call.function.arguments)
    
    result = execute_tool(name, args)
    state["result"] = result
    return state

graph = StateGraph(State)
graph.add_node("agent", agent_node)
graph.set_entry_point("agent")

app = graph.compile()

print(app.invoke({"input": "add 10 and 20"}))
```

---

# 9. Cost Involved 💰

## LLM Cost

* Each request = tokens
* Tool decision adds cost

## Tool Cost

* Local → cheap
* External APIs → may cost

---

## ⚠️ Optimization

* Avoid unnecessary tool calls
* Cache responses
* Use smaller models when possible

---

# 10. Full Architecture

```
          LangGraph (Flow Control)
                    ↓
                LLM Agent
                    ↓
          Tool (Schema / MCP style)
                    ↓
        Execution (Function / API)
                    ↓
                Result
```

---

# 11. When to Use What

| Situation    | Use       |
| ------------ | --------- |
| Simple logic | Tools     |
| Multi-step   | LangGraph |
| Many tools   | MCP       |
| Distributed  | A2A       |

---

# 🔥 Final Summary

* Tools = execution
* LLM = decision maker
* LangGraph = orchestrator
* MCP = tool definition standard
* A2A = communication layer

---

# 🚀 Golden Line

> LLM decides → Tools execute → LangGraph orchestrates → MCP standardizes → A2A scales
