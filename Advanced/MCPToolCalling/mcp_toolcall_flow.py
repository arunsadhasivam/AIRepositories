# MCP (Model Context Protocol) — Prod-Grade Guide

## What is MCP?

MCP is an **open protocol** that lets an LLM call tools that live on **remote servers** — not in your app.

Think of it like a **REST API standard for AI tools**.

```
Your App  →  LLM (Claude/GPT)  →  MCP Client  →  [MCP Server: Weather]
                                               →  [MCP Server: Database]
                                               →  [MCP Server: Calendar]
```

---

## Simple Mental Model

| Concept | MCP Equivalent |
|---|---|
| REST API | MCP Server (exposes tools) |
| API Client | MCP Client (your app calls the server) |
| Swagger/OpenAPI | Tool schema (JSON describing the tool) |
| HTTP Request | Tool call from LLM |
| HTTP Response | Tool result returned to LLM |

---

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│                 YOUR APP                     │
│                                             │
│  User Input → Build Messages → Call LLM     │
│                    ↑                        │
│         Inject Tool Schemas                 │
│                    ↓                        │
│  LLM responds with tool_use block           │
│                    ↓                        │
│  MCP Client → HTTP/SSE → MCP Server         │
│                    ↓                        │
│  Tool Result → Send back to LLM             │
│                    ↓                        │
│  LLM gives final answer → User              │
└─────────────────────────────────────────────┘
```

---

## Key Concept: Tool Discovery

When your app starts, it connects to each MCP server and **asks what tools are available**.
The server returns tool schemas (name, description, input params).
Your app then passes these schemas to the LLM — the LLM decides which tool to call.

---

## How Many LLM Calls Per Request?

For **1 tool call**: always **2 LLM calls minimum**

```
LLM Call #1  →  LLM reads user query + tool schemas
                LLM responds: "call get_weather with city=SF"   ← NOT the final answer

[Your code calls the MCP server — zero LLM cost here]

LLM Call #2  →  LLM reads tool result
                LLM responds: "The weather in SF is 72°F"       ← Final answer
```

For **N tool calls**: `N + 1` LLM calls total.

---

## Do Tools Add Cost?

**Yes.** Every LLM call pays for tool schemas in input tokens.

| What costs tokens | When charged |
|---|---|
| Tool schema JSON (name + description + inputSchema) | Every LLM call, both #1 and #2 |
| LLM's tool_use block output | LLM Call #1 output |
| Tool result string | LLM Call #2 input |
| Final answer text | LLM Call #2 output |

**Rule of thumb:** 1 tool schema ≈ 100–300 input tokens. 10 tools = ~2000 extra tokens per request.

**Cost reduction strategies:**
- Cache tool schemas at startup — don't re-fetch from MCP server per request
- Cache tool results in Redis if same inputs repeat (e.g. same city weather)
- Only pass tools relevant to the user's query (tool pruning)

---

## Simple Example: Weather Tool (Step by Step)

### Step 1 — MCP Server exposes a tool

The weather MCP server tells the world:
> "I have a tool called `get_weather`. Give me a `city` string and I'll return temperature."

```json
{
  "name": "get_weather",
  "description": "Get current weather for a city",
  "inputSchema": {
    "type": "object",
    "properties": {
      "city": { "type": "string", "description": "City name" }
    },
    "required": ["city"]
  }
}
```

### Step 2 — Your app fetches tool schemas from MCP server

```
POST https://weather-mcp-server.com/mcp
Body: { "jsonrpc": "2.0", "method": "tools/list", "params": {} }
→ Returns list of tool schemas (JSON)
```

### Step 3 — LLM Call #1: Send user query + tool schemas to LLM

**This is the first LLM call. Cost = input tokens (user message + all tool schemas) + output tokens (tool_use block).**

```json
{
  "model": "claude-sonnet-4-20250514",
  "tools": [ { "name": "get_weather", "description": "...", "input_schema": {...} } ],
  "messages": [
    { "role": "user", "content": "What is the weather in San Francisco?" }
  ]
}
```

### Step 4 — LLM responds with tool_use block (NOT the final answer)

LLM does NOT call your tool. It just returns JSON telling you what to call.

```json
{
  "stop_reason": "tool_use",
  "content": [
    {
      "type": "tool_use",
      "id": "tool_call_001",
      "name": "get_weather",
      "input": { "city": "San Francisco" }
    }
  ]
}
```

### Step 5 — YOUR code calls the MCP server (zero LLM cost)

```
POST https://weather-mcp-server.com/mcp
Body: { "jsonrpc": "2.0", "method": "tools/call", "params": { "name": "get_weather", "arguments": { "city": "San Francisco" } } }
→ Returns: "72°F, Sunny"
```

### Step 6 — LLM Call #2: Send tool result back to LLM

**This is the second LLM call. Cost = input tokens (full history + tool result + tool schemas again) + output tokens (final answer).**

```json
{
  "messages": [
    { "role": "user", "content": "What is the weather in SF?" },
    { "role": "assistant", "content": [ { "type": "tool_use", "id": "tool_call_001", "name": "get_weather", "input": {...} } ] },
    { "role": "user", "content": [ { "type": "tool_result", "tool_use_id": "tool_call_001", "content": "72°F, Sunny" } ] }
  ]
}
```

### Step 7 — LLM gives final answer (stop_reason: "end_turn")

```
"The current weather in San Francisco is 72°F and Sunny."
```

---

## Python Implementation (Simple, Annotated)

```python
import anthropic   # pip install anthropic — Anthropic SDK
import httpx       # pip install httpx — HTTP client to call MCP server

# ── STEP 1: Define tool schema ──────────────────────────────────────────────
# Pure Python dict. No LLM call yet. Zero cost.
# This tells the LLM: "this tool exists, here's how to call it"
tools = [
    {
        "name": "get_weather",                            # LLM uses this name to invoke the tool
        "description": "Get current weather for a city",  # LLM reads this to decide WHEN to call
        "input_schema": {                                 # LLM follows this to build the input JSON
            "type": "object",
            "properties": {
                "city": { "type": "string", "description": "City name e.g. San Francisco" }
            },
            "required": ["city"]
        }
    }
]

# ── STEP 2: Your actual tool function ───────────────────────────────────────
# This is YOUR code — not LLM. Runs locally or calls a real MCP server.
# In prod: replace with httpx.post() to your MCP server endpoint
def get_weather(city: str) -> str:
    # Real prod code would be:
    # r = httpx.post("https://weather-mcp.example.com/mcp",
    #     json={"jsonrpc":"2.0","method":"tools/call",
    #           "params":{"name":"get_weather","arguments":{"city":city}}})
    # return r.json()["result"]["content"][0]["text"]
    return f"72 degrees F, Sunny in {city}"   # Mocked for this example

# Tool registry — maps tool name to callable function
# Java equivalent: Map<String, McpClient> toolRoutingMap
tool_registry = {
    "get_weather": get_weather    # LLM says "call get_weather" → your function runs
}

# ── STEP 3: Init Anthropic client ───────────────────────────────────────────
# Reads ANTHROPIC_API_KEY from environment automatically. No key in code.
# Java equivalent: new OkHttpClient() + manual Authorization header
client = anthropic.Anthropic()

# ── LLM CALL #1 ─────────────────────────────────────────────────────────────
# Sends: user message + tool schemas
# Cost:  input tokens (user message + tool schemas) + output tokens (tool_use block)
# LLM does NOT call any tool — it only returns a tool_use block telling you what to call
# Java equivalent: LlmOrchestrator.callAnthropicApi(messages)
response = client.messages.create(
    model="claude-sonnet-4-20250514",          # Model selection
    max_tokens=1024,                           # Max output tokens
    tools=tools,                               # Tool schemas — adds to input token cost
    messages=[
        {"role": "user", "content": "What is the weather in San Francisco?"}
    ]
)
# response.stop_reason == "tool_use"  → LLM wants a tool called
# response.content == [ToolUseBlock(type="tool_use", name="get_weather", input={"city":"SF"})]

# ── STEP 4: Extract tool call from LLM response ─────────────────────────────
# Pure Python — no LLM, zero cost
# Java equivalent: block.path("name").asText(), block.path("id").asText()
tool_block  = next(b for b in response.content if b.type == "tool_use")  # Find tool_use block
tool_name   = tool_block.name      # "get_weather"
tool_input  = tool_block.input     # { "city": "San Francisco" }
tool_use_id = tool_block.id        # Unique ID — must echo back to LLM in next call

# ── STEP 5: YOU call the tool (not the LLM) ─────────────────────────────────
# No LLM involved. Zero LLM cost here.
# Java equivalent: toolExecutor.execute(toolName, toolInput)
fn = tool_registry[tool_name]               # Look up function by name
tool_result = fn(**tool_input)              # Call it with LLM's generated args
# tool_result == "72 degrees F, Sunny in San Francisco"

# ── LLM CALL #2 ─────────────────────────────────────────────────────────────
# Sends: full conversation history + tool result
# Cost:  input tokens (everything above + tool result + tool schemas again) + output tokens
# LLM reads the tool result and writes the final natural language answer
# Java equivalent: next iteration of while(true) loop in LlmOrchestrator.chat()
final_response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    tools=tools,                               # Must pass tools again — API is stateless
    messages=[
        # Turn 1: original user question
        {"role": "user", "content": "What is the weather in San Francisco?"},

        # Turn 2: LLM's first response (the tool_use block) — must include in history
        {"role": "assistant", "content": response.content},

        # Turn 3: your tool result — must use tool_result type with matching tool_use_id
        {"role": "user", "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use_id,    # Must match id from LLM Call #1
                "content": tool_result          # The actual result string
            }
        ]}
    ]
)
# final_response.stop_reason == "end_turn"  → LLM is done, no more tools needed
# final_response.content[0].text == "The weather in San Francisco is 72 degrees F and Sunny."

print(final_response.content[0].text)
```

---

## Prod-Grade Java Implementation

### Project Structure

```
mcp-demo/
├── src/main/java/com/example/mcp/
│   ├── McpClient.java          ← Connects to MCP servers, fetches tools
│   ├── ToolSchema.java         ← POJO representing a tool's schema
│   ├── LlmOrchestrator.java    ← Sends messages to LLM, handles tool_use loop
│   ├── ToolExecutor.java       ← Routes tool calls back to correct MCP server
│   └── Main.java               ← Entry point
├── pom.xml
```

**Python equivalent of each Java class:**

| Java Class | Python Equivalent |
|---|---|
| `McpClient.java` | `httpx.post()` calls to MCP server |
| `ToolSchema.java` | Plain `dict` with name/description/input_schema |
| `LlmOrchestrator.java` | The `while True` agentic loop calling `client.messages.create()` |
| `ToolExecutor.java` | A `dict` mapping tool name → function: `{"get_weather": get_weather}` |
| `Main.java` | Top-level script wiring everything together |

---

### pom.xml (Dependencies)

```xml
<dependencies>
    <!-- HTTP client to call MCP servers and Anthropic API -->
    <!-- Python equivalent: pip install httpx anthropic -->
    <dependency>
        <groupId>com.squareup.okhttp3</groupId>
        <artifactId>okhttp</artifactId>
        <version>4.12.0</version>
    </dependency>

    <!-- JSON parsing -->
    <!-- Python equivalent: built-in json module or response.json() -->
    <dependency>
        <groupId>com.fasterxml.jackson.core</groupId>
        <artifactId>jackson-databind</artifactId>
        <version>2.17.0</version>
    </dependency>
</dependencies>
```

---

### ToolSchema.java

```java
package com.example.mcp;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * Represents a single tool schema fetched from an MCP server.
 * The LLM uses this schema to know what tools are available and how to call them.
 *
 * Python equivalent — just a plain dict, no class needed:
 *   tool = {
 *       "name": "get_weather",
 *       "description": "Get current weather for a city",
 *       "input_schema": { "type": "object", "properties": { "city": {...} } }
 *   }
 *   server_url stored separately: tool_to_server = {"get_weather": "https://weather-mcp.com"}
 */
public class ToolSchema {

    // Tool name — LLM uses this to invoke the tool (e.g. "get_weather")
    // Python: tool["name"]
    private String name;

    // Human-readable description — LLM uses this to decide WHEN to call the tool
    // Python: tool["description"]
    private String description;

    // JSON Schema of the tool's input parameters
    // Python: tool["input_schema"]  (a nested dict)
    private JsonNode inputSchema;

    // Which MCP server URL hosts this tool — needed to route the call back
    // Python: separate dict { tool_name: mcp_server_url }
    private String mcpServerUrl;

    public ToolSchema(String name, String description, JsonNode inputSchema, String mcpServerUrl) {
        this.name = name;
        this.description = description;
        this.inputSchema = inputSchema;
        this.mcpServerUrl = mcpServerUrl;
    }

    public String getName() { return name; }
    public String getDescription() { return description; }
    public JsonNode getInputSchema() { return inputSchema; }
    public String getMcpServerUrl() { return mcpServerUrl; }
}
```

---

### McpClient.java

```java
package com.example.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import okhttp3.*;

import java.util.ArrayList;
import java.util.List;

/**
 * McpClient connects to a remote MCP server.
 * Responsibilities:
 *   1. Discover tools the server exposes (tools/list)  — NOT an LLM call
 *   2. Execute a tool call and return the result (tools/call) — NOT an LLM call
 *
 * Python equivalent of this entire class (just 2 functions):
 *
 *   def discover_tools(server_url):
 *       r = httpx.post(server_url + "/mcp",
 *           json={"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}})
 *       return r.json()["result"]["tools"]   # list of dicts
 *
 *   def execute_tool(server_url, tool_name, arguments):
 *       r = httpx.post(server_url + "/mcp",
 *           json={"jsonrpc":"2.0","id":2,"method":"tools/call",
 *                 "params":{"name": tool_name, "arguments": arguments}})
 *       return r.json()["result"]["content"][0]["text"]
 */
public class McpClient {

    // Base URL of the remote MCP server
    // Python: just a string variable passed to httpx.post()
    private final String serverUrl;

    // HTTP client — reuse one instance (thread-safe in OkHttp)
    // Python: httpx.Client() or module-level httpx.post() calls
    private final OkHttpClient httpClient;

    // JSON mapper
    // Python: built-in json.dumps() / response.json()
    private final ObjectMapper mapper;

    public McpClient(String serverUrl) {
        this.serverUrl  = serverUrl;
        this.httpClient = new OkHttpClient();
        this.mapper     = new ObjectMapper();
    }

    /**
     * Call MCP server's tools/list endpoint.
     * Returns list of ToolSchema objects — one per tool the server exposes.
     * NOT an LLM call. Zero LLM cost.
     *
     * Python equivalent (2 lines):
     *   r = httpx.post(server_url + "/mcp", json={"jsonrpc":"2.0","method":"tools/list","params":{}})
     *   tools = r.json()["result"]["tools"]
     */
    public List<ToolSchema> discoverTools() throws Exception {

        // MCP JSON-RPC request body — Python: just a dict literal
        String requestBody = "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{}}";

        // HTTP POST to MCP server — Python: httpx.post(url, json=body)
        Request request = new Request.Builder()
                .url(serverUrl + "/mcp")
                .post(RequestBody.create(requestBody, MediaType.parse("application/json")))
                .build();

        // Execute synchronously — Python: response = httpx.post(...) blocks by default
        try (Response response = httpClient.newCall(request).execute()) {

            // Parse response JSON — Python: data = response.json()
            JsonNode root = mapper.readTree(response.body().string());

            // Navigate to tools array — Python: tools = data["result"]["tools"]
            JsonNode toolsArray = root.path("result").path("tools");

            List<ToolSchema> tools = new ArrayList<>();

            // Wrap each tool into ToolSchema — Python: tools is already a list of dicts
            for (JsonNode toolNode : toolsArray) {
                tools.add(new ToolSchema(
                        toolNode.path("name").asText(),         // tool["name"]
                        toolNode.path("description").asText(),  // tool["description"]
                        toolNode.path("inputSchema"),           // tool["inputSchema"]
                        serverUrl                               // which server owns this tool
                ));
            }
            return tools;
        }
    }

    /**
     * Execute a specific tool with given arguments on this MCP server.
     * Called AFTER LLM returns a tool_use block.
     * NOT an LLM call. Zero LLM cost.
     *
     * Python equivalent (2 lines):
     *   r = httpx.post(server_url + "/mcp",
     *       json={"jsonrpc":"2.0","method":"tools/call",
     *             "params":{"name":tool_name,"arguments":args}})
     *   return r.json()["result"]["content"][0]["text"]
     */
    public String executeTool(String toolName, JsonNode arguments) throws Exception {

        // Build MCP tools/call request — Python: just a dict passed to json=
        String requestBody = mapper.writeValueAsString(
                mapper.createObjectNode()
                        .put("jsonrpc", "2.0")
                        .put("id", 2)
                        .put("method", "tools/call")
                        .set("params", mapper.createObjectNode()
                                .put("name", toolName)          // which tool
                                .set("arguments", arguments))   // LLM-generated args
        );

        // POST to the MCP server — Python: httpx.post(url, json=body)
        Request request = new Request.Builder()
                .url(serverUrl + "/mcp")
                .post(RequestBody.create(requestBody, MediaType.parse("application/json")))
                .build();

        try (Response response = httpClient.newCall(request).execute()) {

            // Parse and extract result — Python: r.json()["result"]["content"][0]["text"]
            JsonNode root    = mapper.readTree(response.body().string());
            JsonNode content = root.path("result").path("content");

            if (content.isArray() && content.size() > 0) {
                return content.get(0).path("text").asText();   // return tool result string
            }
            return "No result returned from tool";
        }
    }
}
```

---

### ToolExecutor.java

```java
package com.example.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;

/**
 * Routes a tool_use call from the LLM to the correct MCP server.
 *
 * Problem: LLM says "call get_weather" but you have 3 MCP servers.
 * Solution: routing map tells you which server owns which tool.
 *
 * Python equivalent — entire class replaced by a dict + 3 lines:
 *
 *   # Build once at startup
 *   tool_registry = {
 *       "get_weather":  weather_mcp_client,    # tool name → MCP client
 *       "create_event": calendar_mcp_client,
 *   }
 *
 *   # Route and execute
 *   def execute_tool(tool_name, arguments):
 *       client = tool_registry.get(tool_name)
 *       if not client:
 *           return f"Error: tool '{tool_name}' not found"
 *       return client.execute_tool(tool_name, arguments)
 */
public class ToolExecutor {

    // Map: tool name → McpClient that owns that tool
    // Python: { "get_weather": weather_client, "create_event": calendar_client }
    private final Map<String, McpClient> toolToClientMap;

    public ToolExecutor(Map<String, McpClient> toolToClientMap) {
        this.toolToClientMap = toolToClientMap;
    }

    /**
     * Route and execute the tool call.
     * NOT an LLM call. Zero LLM cost.
     *
     * Python equivalent:
     *   client = tool_registry.get(tool_name)
     *   return client.execute_tool(tool_name, arguments)
     */
    public String execute(String toolName, JsonNode arguments) throws Exception {

        // Look up which MCP server owns this tool — Python: tool_registry.get(tool_name)
        McpClient client = toolToClientMap.get(toolName);

        // LLM may hallucinate a tool name — handle gracefully
        // Python: if not client: return f"Error: tool '{tool_name}' not found"
        if (client == null) {
            return "Error: Tool '" + toolName + "' not found on any connected MCP server";
        }

        // Delegate to correct MCP server — Python: client.execute_tool(tool_name, arguments)
        return client.executeTool(toolName, arguments);
    }
}
```

---

### LlmOrchestrator.java

```java
package com.example.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import okhttp3.*;
import java.util.List;

/**
 * Manages the full agentic loop.
 * This is where ALL LLM calls happen — one per loop iteration.
 *
 * Python equivalent of the entire class (the while loop is everything):
 *
 *   def chat(user_query, tools, tool_registry):
 *       client   = anthropic.Anthropic()
 *       messages = [{"role": "user", "content": user_query}]
 *
 *       while True:
 *           # ── LLM CALL (costs tokens every iteration) ──
 *           response = client.messages.create(
 *               model="claude-sonnet-4-20250514", max_tokens=1024,
 *               tools=tools, messages=messages
 *           )
 *
 *           # Add LLM response to history for next call
 *           messages.append({"role": "assistant", "content": response.content})
 *
 *           if response.stop_reason == "end_turn":
 *               return response.content[0].text    # Final answer — exit loop
 *
 *           # LLM wants tools — collect all tool_use blocks
 *           tool_results = []
 *           for block in response.content:
 *               if block.type != "tool_use": continue
 *               fn     = tool_registry[block.name]    # Route to correct function
 *               result = fn(**block.input)             # Execute — zero LLM cost
 *               tool_results.append({
 *                   "type":        "tool_result",
 *                   "tool_use_id": block.id,           # Must match LLM's id
 *                   "content":     result
 *               })
 *
 *           # Add tool results to history — triggers next LLM call
 *           messages.append({"role": "user", "content": tool_results})
 */
public class LlmOrchestrator {

    private static final String ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages";

    // API key — Python: SDK reads ANTHROPIC_API_KEY env var automatically
    private final String apiKey;

    // Routes tool calls to correct MCP server — Python: tool_registry dict
    private final ToolExecutor toolExecutor;

    // Tool schemas from all MCP servers — Python: tools list of dicts
    private final List<ToolSchema> availableTools;

    private final OkHttpClient httpClient;
    private final ObjectMapper mapper;

    public LlmOrchestrator(String apiKey, ToolExecutor toolExecutor, List<ToolSchema> availableTools) {
        this.apiKey          = apiKey;
        this.toolExecutor    = toolExecutor;
        this.availableTools  = availableTools;
        this.httpClient      = new OkHttpClient();
        this.mapper          = new ObjectMapper();
    }

    /**
     * Runs the agentic loop until LLM returns a final answer.
     *
     * LLM call count:
     *   - 1 tool used  → 2 LLM calls
     *   - 2 tools used → 3 LLM calls
     *   - N tools used → N+1 LLM calls
     *
     * Python equivalent: the while True loop in the docstring above.
     */
    public String chat(String userQuery) throws Exception {

        // Build conversation history — Python: messages = [{"role":"user","content":user_query}]
        ArrayNode messages = mapper.createArrayNode();

        // Add the initial user message
        ObjectNode userMessage = mapper.createObjectNode();
        userMessage.put("role", "user");        // role = "user"
        userMessage.put("content", userQuery);  // the question
        messages.add(userMessage);

        // ── AGENTIC LOOP — each iteration = 1 LLM call ──────────────────────
        // Python: while True:
        while (true) {

            // ── LLM CALL (costs tokens) ──────────────────────────────────────
            // Python: response = client.messages.create(tools=tools, messages=messages)
            JsonNode llmResponse = callAnthropicApi(messages);

            // Read stop_reason — Python: response.stop_reason
            String stopReason = llmResponse.path("stop_reason").asText();

            // Read content blocks — Python: response.content
            JsonNode contentBlocks = llmResponse.path("content");

            // Add LLM response to history — required so next call has context
            // Python: messages.append({"role":"assistant","content":response.content})
            ObjectNode assistantMessage = mapper.createObjectNode();
            assistantMessage.put("role", "assistant");
            assistantMessage.set("content", contentBlocks);
            messages.add(assistantMessage);

            // ── CASE 1: LLM done — return final answer ───────────────────────
            // Python: if response.stop_reason == "end_turn": return response.content[0].text
            if ("end_turn".equals(stopReason)) {
                for (JsonNode block : contentBlocks) {
                    if ("text".equals(block.path("type").asText())) {
                        return block.path("text").asText();    // Final answer
                    }
                }
                return "No text response from LLM";
            }

            // ── CASE 2: LLM wants tools ──────────────────────────────────────
            // Python: if response.stop_reason == "tool_use":
            if ("tool_use".equals(stopReason)) {

                // Collect results for all tool_use blocks in this response
                // Python: tool_results = []
                ArrayNode toolResultContents = mapper.createArrayNode();

                for (JsonNode block : contentBlocks) {

                    // Skip non tool_use blocks — Python: if block.type != "tool_use": continue
                    if (!"tool_use".equals(block.path("type").asText())) continue;

                    // Extract tool call details — Python: block.name, block.id, block.input
                    String   toolName  = block.path("name").asText();
                    String   toolUseId = block.path("id").asText();    // Must echo back
                    JsonNode toolInput = block.path("input");           // LLM-generated args

                    // Execute tool — NOT an LLM call, zero LLM cost
                    // Python: result = tool_registry[block.name](**block.input)
                    String toolResult = toolExecutor.execute(toolName, toolInput);

                    // Build tool_result block — Python: {"type":"tool_result","tool_use_id":...}
                    ObjectNode resultBlock = mapper.createObjectNode();
                    resultBlock.put("type", "tool_result");
                    resultBlock.put("tool_use_id", toolUseId);   // Must match LLM's tool_use id
                    resultBlock.put("content", toolResult);       // Actual tool output
                    toolResultContents.add(resultBlock);
                }

                // Send tool results back as user message
                // Python: messages.append({"role":"user","content":tool_results})
                ObjectNode toolResultMessage = mapper.createObjectNode();
                toolResultMessage.put("role", "user");
                toolResultMessage.set("content", toolResultContents);
                messages.add(toolResultMessage);

                // Loop — triggers next LLM call with tool results included
            }
        }
    }

    /**
     * The ONLY place an actual LLM API call happens.
     * Called once per while-loop iteration.
     * Every call pays for: input tokens (messages + tool schemas) + output tokens.
     *
     * Python equivalent (1 call):
     *   response = client.messages.create(
     *       model="claude-sonnet-4-20250514", max_tokens=1024,
     *       tools=tools,       ← tool schemas add to input token cost every call
     *       messages=messages  ← full history grows with each tool round-trip
     *   )
     */
    private JsonNode callAnthropicApi(ArrayNode messages) throws Exception {

        // Build tools array — Python: already a list of dicts passed directly to tools=
        ArrayNode toolsArray = mapper.createArrayNode();
        for (ToolSchema tool : availableTools) {
            ObjectNode toolDef = mapper.createObjectNode();
            toolDef.put("name", tool.getName());
            toolDef.put("description", tool.getDescription());
            toolDef.set("input_schema", tool.getInputSchema());  // JSON Schema
            toolsArray.add(toolDef);
        }

        // Build Anthropic API request body
        ObjectNode requestBody = mapper.createObjectNode();
        requestBody.put("model", "claude-sonnet-4-20250514");  // Model
        requestBody.put("max_tokens", 1024);                   // Max output tokens
        requestBody.set("tools", toolsArray);                  // Tool schemas — input token cost
        requestBody.set("messages", messages);                 // Full history

        // POST to Anthropic — Python: client.messages.create(...) handles this internally
        Request request = new Request.Builder()
                .url(ANTHROPIC_API_URL)
                .post(RequestBody.create(mapper.writeValueAsString(requestBody),
                        MediaType.parse("application/json")))
                .addHeader("x-api-key", apiKey)                // Auth header
                .addHeader("anthropic-version", "2023-06-01")  // Required version header
                .addHeader("Content-Type", "application/json")
                .build();

        try (Response response = httpClient.newCall(request).execute()) {
            return mapper.readTree(response.body().string());
        }
    }
}
```

---

### Main.java

```java
package com.example.mcp;

import java.util.*;

/**
 * Entry point — wires everything together.
 *
 * Python equivalent of this entire file:
 *
 *   weather_client  = McpClient("https://weather-mcp.example.com")
 *   calendar_client = McpClient("https://calendar-mcp.example.com")
 *
 *   weather_tools  = discover_tools(weather_client)
 *   calendar_tools = discover_tools(calendar_client)
 *   all_tools = weather_tools + calendar_tools
 *
 *   tool_registry = {t["name"]: weather_client  for t in weather_tools}
 *   tool_registry.update({t["name"]: calendar_client for t in calendar_tools})
 *
 *   answer = chat("What is the weather in SF?", all_tools, tool_registry)
 *   print(answer)
 *
 * In prod: Spring Boot @Service, McpClient as @Bean, discoverTools() in @PostConstruct
 */
public class Main {

    public static void main(String[] args) throws Exception {

        // Connect to each MCP server — Python: just store URL string
        McpClient weatherMcpClient  = new McpClient("https://weather-mcp-server.example.com");
        McpClient calendarMcpClient = new McpClient("https://calendar-mcp-server.example.com");

        // Discover tools — HTTP call to MCP server, NOT an LLM call
        // Python: weather_tools = discover_tools(weather_url)
        List<ToolSchema> allTools = new ArrayList<>();

        List<ToolSchema> weatherTools  = weatherMcpClient.discoverTools();
        allTools.addAll(weatherTools);   // e.g. [get_weather, get_forecast]

        List<ToolSchema> calendarTools = calendarMcpClient.discoverTools();
        allTools.addAll(calendarTools);  // e.g. [create_event, list_events]

        // Build routing map — Python: tool_registry = {"get_weather": weather_client, ...}
        Map<String, McpClient> toolRoutingMap = new HashMap<>();
        for (ToolSchema t : weatherTools)  toolRoutingMap.put(t.getName(), weatherMcpClient);
        for (ToolSchema t : calendarTools) toolRoutingMap.put(t.getName(), calendarMcpClient);

        // Wire up everything
        ToolExecutor    toolExecutor = new ToolExecutor(toolRoutingMap);
        String          apiKey       = System.getenv("ANTHROPIC_API_KEY"); // Python: SDK reads this automatically
        LlmOrchestrator orchestrator = new LlmOrchestrator(apiKey, toolExecutor, allTools);

        // Run a query — internally: 2 LLM calls (1 tool decision + 1 final answer)
        // Python: answer = chat("What is the weather in SF?", all_tools, tool_registry)
        String answer = orchestrator.chat("What is the weather in San Francisco today?");

        System.out.println("Answer: " + answer);
        // Output: "The current weather in San Francisco is 72 degrees F and Sunny."
    }
}
```

---

## Full Flow Diagram (Prod)

```
User: "Weather in SF?"
        │
        ▼
LlmOrchestrator.chat()           # Python: chat(user_query, tools, tool_registry)
        │
        ├─── Build messages[] with user query
        │
        ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 LLM CALL #1  (costs tokens)
 Java:   callAnthropicApi(messages)
 Python: client.messages.create(tools=tools, messages=messages)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        │
        │  stop_reason: "tool_use"
        │  content: [{ type:"tool_use", name:"get_weather", input:{city:"SF"} }]
        │
        ▼
ToolExecutor.execute()
Python: tool_registry["get_weather"]({"city":"SF"})
        │  NOT an LLM call — zero LLM cost
        ▼
McpClient.executeTool()
Python: httpx.post(mcp_url, json={method:"tools/call", params:{name, arguments}})
        │
        │  Result: "72 degrees F, Sunny"
        │
        ▼
Append tool_result to messages[]
Python: messages.append({"role":"user","content":[{"type":"tool_result",...}]})
        │
        ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 LLM CALL #2  (costs tokens)
 Java:   callAnthropicApi(messages)
 Python: client.messages.create(tools=tools, messages=messages)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        │
        │  stop_reason: "end_turn"
        │  content: [{ type:"text", text:"The weather in SF is 72 degrees F and Sunny." }]
        │
        ▼
Return final answer to user ✓
```

---

## Prod Considerations

| Concern | Java Solution | Python Solution |
|---|---|---|
| MCP server is down | Resilience4j circuit breaker | `tenacity` retry library |
| Tool discovery per request | Cache at startup in a `List<ToolSchema>` | Cache in module-level list, refresh on schedule |
| Multiple tool calls in one response | Loop over all `tool_use` blocks (handled above) | Same — loop over `response.content` |
| API key management | Azure Key Vault via Spring Cloud | `os.environ` + Azure Key Vault SDK |
| Async tool calls | `CompletableFuture.supplyAsync()` | `asyncio` + `httpx.AsyncClient` |
| Observability | Langfuse / OpenTelemetry per tool call | Langfuse `@observe` decorator |
| LLM hallucinating tool names | Null-check in ToolExecutor | `tool_registry.get(name)` check |
| Token cost of tool schemas | Cache results in Redis, pass fewer tools | Same — Redis cache + selective tool passing |

---

## MCP vs Direct API Call

| | MCP Tool | Direct API Call |
|---|---|---|
| Tool location | Remote MCP server | Inside your app |
| Tool discovery | Dynamic at runtime via tools/list | Hardcoded schemas in code |
| Reusability | Any LLM app can connect to same server | App-specific |
| Protocol | JSON-RPC 2.0 over HTTP/SSE | Whatever you build |
| Prod use case | Shared org-wide tools | App-specific logic |
| Python | `httpx.post(mcp_url, json={method:"tools/call"})` | Direct function call |
| Java | `McpClient.executeTool()` | Direct method call |
