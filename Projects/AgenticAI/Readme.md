MCP and A2A(config)
===================

```
# agent card
curl http://localhost:8011/.well-known/agent.json

# mcp config

curl http://localhost:8011/config

# pretty print

curl http://localhost:8011/.well-known/agent.json | python -m json.tool

#important :

/.well-known/agent.json -> localhost:8011/.well-known/agent.json
     -  Follow A2A protocol standard — other A2A agents expect this path(/well-known) for auto-discovery
Although you can use anything like  localhost:8011/discovery

# Browser

http://localhost:8011/.well-known/agent.json
http://localhost:8011/config

```

Console:
=============
```
# Test MCP1 tools directly
  python mcp1/client/recommendation_client.py

# Test MCP2 math tools directly
  python mcp2/client/math_client.py

# Test A2A recommendation agent (MCP2 → A2A → MCP1)
  python a2a/client/recommendation_agent_client.py

# Test A2A math agent (MCP1 → A2A → MCP2)
  python a2a/client/math_agent_client.py
```


Server:
=======
```
python mcp1/server/recommendation_server.py
python mcp2/server/math_server.py

python a2a/server/recommendation_agent_server.py
python a2a/server/math_agent_server.py
```
Add Agent and MCP to web:
=========================

```
 from aiohttp import web
 app = web.Application()
 app.router.add_get("/.well-known/agent.json", handle_agent_card)  # A2A discovery
 app.router.add_get("/config", handle_mcp_config)                   # MCP config
 web.run_app(app, host="0.0.0.0", port=8011, loop=loop)
```
