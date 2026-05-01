# MCP + A2A Protocol Demo

  company 1 - recommendation service ( math-add,multiply here) mcp
  company 2 - math service
  
  use MCP - to call say add just 1 tools you can embed in company2 via mcp
  use A2A - if tools is composite (orchestrate) - > we process text, count, generate html all we need 
             instead of add 3 tools to we can delegate entirely to company1 -> which is a composite service 
             it process text, count, html and provide to you.
  
  A2A - is something we do bank verification and delegate booking to payment service(payment gateway of bank)
     

## Architecture

```
BOTH DIRECTIONS:

  MCP2 caller → A2A (port 8003) → RecommendationAgent → MCP1 tools
  MCP1 caller → A2A (port 8004) → MathAgent           → MCP2 tools

Servers:
  MCP1  port 8001   recommendation-server  [process_text, get_count, print_count_html]
  MCP2  port 8002   math-server            [add, multiply, power, average]
  A2A   port 8003   RecommendationAgent    wraps MCP1 tools, called by MCP2 via A2A
  A2A   port 8004   MathAgent              wraps MCP2 tools, called by MCP1 via A2A
```

## Folder Structure

```
mcp_a2a_demo/
├── mcp1/
│   ├── tools/recommendation_tools.py     ← 3 tools (process_text, get_count, print_count_html)
│   ├── server/recommendation_server.py   ← FastMCP server port 8001
│   └── client/recommendation_client.py  ← direct MCP client for MCP1
├── mcp2/
│   ├── tools/math_tools.py               ← math functions (add, multiply, power, average)
│   ├── server/math_server.py             ← FastMCP server port 8002
│   └── client/math_client.py            ← direct MCP client for MCP2
├── a2a/
│   ├── server/recommendation_agent_server.py  ← A2A server port 8003 (wraps MCP1)
│   ├── server/math_agent_server.py            ← A2A server port 8004 (wraps MCP2)
│   ├── client/recommendation_agent_client.py  ← A2A client → port 8003
│   └── client/math_agent_client.py            ← A2A client → port 8004
├── main.py           ← test all 5 methods
└── requirements.txt
```

## Start Servers (4 terminals)

```bash
python mcp1/server/recommendation_server.py       # port 8001
python mcp2/server/math_server.py                 # port 8002
python a2a/server/recommendation_agent_server.py  # port 8003
python a2a/server/math_agent_server.py            # port 8004
```

## Run Tests

```bash
python main.py
```

## Test Methods in main.py

| Method | Direction | Pattern |
|--------|-----------|---------|
| method1_direct_mcp1 | caller → MCP1 | Direct MCP, no A2A |
| method2_direct_mcp2 | caller → MCP2 | Direct MCP, no A2A |
| method3_a2a_delegate | MCP2 caller → A2A(8003) → MCP1 tools | A2A forward |
| method4_mixed | MCP2 + A2A(8003) combined | Mixed |
| method5_reverse_a2a | MCP1 caller → A2A(8004) → MCP2 tools | A2A reverse |

## Key Concept: Why A2A?

- MCP = tool protocol (expose functions as tools to LLM clients)
- A2A = agent protocol (agents delegate tasks to other agents)
- When MCP2 needs 3 chained recommendation tools → don't add to MCP2, delegate via A2A
- When MCP1 needs math → don't add math to MCP1, delegate via A2A to MathAgent
- Each server stays focused on its domain; A2A handles cross-domain orchestration
