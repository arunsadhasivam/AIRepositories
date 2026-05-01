MCP and A2A(config)
===================

# agent card
curl http://localhost:8011/.well-known/agent.json

# mcp config
curl http://localhost:8011/config

# pretty print
curl http://localhost:8011/.well-known/agent.json | python -m json.tool

#Browser

http://localhost:8011/.well-known/agent.json
http://localhost:8011/config

Console:
=============

# Test MCP1 tools directly
python mcp1/client/recommendation_client.py

# Test MCP2 math tools directly
python mcp2/client/math_client.py

# Test A2A recommendation agent (MCP2 → A2A → MCP1)
python a2a/client/recommendation_agent_client.py

# Test A2A math agent (MCP1 → A2A → MCP2)
python a2a/client/math_agent_client.py
