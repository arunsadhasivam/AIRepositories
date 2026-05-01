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

python main.py # test full flow.
1) METHOD 1: Direct MCP1 call (MCP client → MCP1 server)
2) METHOD 2: Direct MCP2 call (MCP client → MCP2 math server)
============================================================
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


MCP vs A2A:
============






OUTPUT:
=======
python main.py # test full flow.



     






<details> <summary><b>METHOD 1: Direct MCP1 call (MCP client → MCP1 server)</b></summary>
  <p>
     
       [1] Calling tool_process_text with: 'apple banana apple orange banana apple mango'
          C:\Arun\Python\Python3.11\Lib\contextlib.py:105: DeprecationWarning: Use `streamable_http_client` instead.
            self.gen = func(*args, **kwds)
              Result: {'apple': 3, 'banana': 2, 'orange': 1, 'mango': 1}
     
     [2] Calling tool_get_count...
         Result: {'total_words': 7, 'unique_words': 4}
     
     [3] Calling tool_print_count_html...
         Result (first 300 chars): 
     <html>
     <body>
     <h2>Word Frequency Report</h2>
     <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; font-family:monospace;">
       <thead>
         <tr style="background:#4CAF50; color:white;">
           <th>Word</th>
           <th>Count</th>
         </tr>
       </thead>
       <tbody>
         <tr><td>ap
     
         HTML saved to output_method1.html
</p>
</details>

 


<details><summary><b>METHOD 2: Direct MCP2 call (MCP client → MCP2 math server)</b></summary>
 <p>    
          [1] tool_add(10, 25)         = 35.0
          [2] tool_multiply(6, 7)      = 42.0
          [3] tool_power(2, 10)        = 1024.0
          [4] tool_average([10,20,30]) = 20.0
      
</p>
</details>




<details><summary><b>METHOD 3: A2A delegation (MCP2 caller → A2A agent → MCP1 tools)</b></summary>

<p>    
     
          [MCP2 Math] tool_multiply(3, 7) = 21.0
          [A2A] Discovering agent capabilities...
          [A2A Client] Discovered agent: RecommendationAgent - Orchestrates text processing: process_text → get_count → print_count_html
                Agent: RecommendationAgent, Skills: ['full_recommendation_pipeline']
          
          [A2A] Delegating recommendation pipeline for: 'python java python go rust java python scala python'
          
            word_counts : {'python': 4, 'java': 2, 'go': 1, 'rust': 1, 'scala': 1}
            counts      : {'total_words': 9, 'unique_words': 5}
            html (first 300 chars): 
          <html>
          <body>
          <h2>Word Frequency Report</h2>
          <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; font-family:monospace;">
            <thead>
              <tr style="background:#4CAF50; color:white;">
                <th>Word</th>
                <th>Count</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>py
          
            HTML saved to output_method3.html

     </p>
</details>


    


<details><summary><b>METHOD 4: Mixed (MCP2 math + A2A recommendation combined)</b></summary>
  <p>    
       
       word_counts     : {'apple': 3, 'banana': 2, 'orange': 1, 'grape': 1}
       count values    : [3, 2, 1, 1]
       average (MCP2)  : 1.75
       total (from A2A): {'total_words': 7, 'unique_words': 4}

 </p>
</details>


 


<details><summary><b>METHOD 5: Reverse A2A (MCP1 caller → A2A → MCP2 math tools)</b></summary>
<p>
     
     [MCP1] Processing text: 'python java python go rust java python scala python go'
       word_counts: {'python': 4, 'java': 2, 'go': 2, 'rust': 1, 'scala': 1}
     
     [A2A] MCP1 discovering MathAgent capabilities...
     [A2A MathClient] Discovered: MathAgent - Exposes math operations via A2A: add, multiply, power, average
           Agent: MathAgent, Skills: ['math_operation']
     
     [A2A] Delegating average([4, 2, 2, 1, 1]) to MathAgent...
       average frequency = 2.0
     
     [A2A] Delegating power(10, 2) to MathAgent...
       total_words^2 = 100
     
       Summary:
         word_counts     = {'python': 4, 'java': 2, 'go': 2, 'rust': 1, 'scala': 1}
         avg_frequency   = 2.0  (via A2A → MCP2)
         total_words^2   = 100   (via A2A → MCP2)
         
</p>
</details>

