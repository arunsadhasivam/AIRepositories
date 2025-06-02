# MCP HTTP Server Client Usage

## Starting the Server

```bash
python mcp_server.py
```

The server will start on `http://localhost:5000`

## Client Invocation Methods

### 1. Using cURL (Command Line)

#### Health Check
```bash
curl http://localhost:5000/
```

#### List Available Tools
```bash
curl http://localhost:5000/tools
```

#### Execute Weather Tool
```bash
curl -X POST http://localhost:5000/tools/get_weather \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"location": "New York"}}'
```

#### Execute Calculator Tool
```bash
curl -X POST http://localhost:5000/tools/calculate \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"expression": "2+2*3"}}'
```

#### Get Current Time
```bash
curl -X POST http://localhost:5000/tools/get_time \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Generic Invoke Endpoint
```bash
curl -X POST http://localhost:5000/invoke \
  -H "Content-Type: application/json" \
  -d '{"type": "tool", "name": "get_weather", "parameters": {"location": "London"}}'
```

#### List Resources
```bash
curl http://localhost:5000/resources
```

#### Get Specific Resource
```bash
curl http://localhost:5000/resources/system_info
```

### 2. Using Python Requests

```python
import requests
import json

# Server URL
BASE_URL = "http://localhost:5000"

# Health check
response = requests.get(f"{BASE_URL}/")
print("Health:", response.json())

# List tools
response = requests.get(f"{BASE_URL}/tools")
print("Tools:", response.json())

# Execute weather tool
payload = {
    "parameters": {
        "location": "San Francisco"
    }
}
response = requests.post(f"{BASE_URL}/tools/get_weather", json=payload)
print("Weather:", response.json())

# Execute calculator
payload = {
    "parameters": {
        "expression": "10 * 5 + 3"
    }
}
response = requests.post(f"{BASE_URL}/tools/calculate", json=payload)
print("Calculation:", response.json())

# Generic invoke
payload = {
    "type": "tool",
    "name": "get_time",
    "parameters": {}
}
response = requests.post(f"{BASE_URL}/invoke", json=payload)
print("Time:", response.json())
```

### 3. Using JavaScript/Node.js

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:5000';

async function testMCPServer() {
    try {
        // Health check
        const health = await axios.get(`${BASE_URL}/`);
        console.log('Health:', health.data);

        // Get weather
        const weather = await axios.post(`${BASE_URL}/tools/get_weather`, {
            parameters: { location: 'Tokyo' }
        });
        console.log('Weather:', weather.data);

        // Calculate
        const calc = await axios.post(`${BASE_URL}/tools/calculate`, {
            parameters: { expression: '15 / 3 + 7' }
        });
        console.log('Calculation:', calc.data);

        // Generic invoke
        const invoke = await axios.post(`${BASE_URL}/invoke`, {
            type: 'resource',
            name: 'system_info'
        });
        console.log('System Info:', invoke.data);
        
    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
}

testMCPServer();
```

### 4. Using Browser JavaScript (Fetch API)

```javascript
// Health check
fetch('http://localhost:5000/')
    .then(response => response.json())
    .then(data => console.log('Health:', data));

// Execute tool
fetch('http://localhost:5000/tools/get_weather', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        parameters: { location: 'Paris' }
    })
})
.then(response => response.json())
.then(data => console.log('Weather:', data));

// Generic invoke
fetch('http://localhost:5000/invoke', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        type: 'tool',
        name: 'calculate',
        parameters: { expression: '100 - 25' }
    })
})
.then(response => response.json())
.then(data => console.log('Result:', data));
```

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/tools` | List all available tools |
| POST | `/tools/<tool_name>` | Execute specific tool |
| GET | `/resources` | List all available resources |
| GET | `/resources/<resource_name>` | Get specific resource |
| POST | `/invoke` | Generic invoke endpoint for any tool/resource |

## Request/Response Format

### Tool Execution Request
```json
{
    "parameters": {
        "param1": "value1",
        "param2": "value2"
    }
}
```

### Generic Invoke Request
```json
{
    "type": "tool|resource",
    "name": "tool_or_resource_name",
    "parameters": {
        "param1": "value1"
    }
}
```

### Success Response
```json
{
    "success": true,
    "result": {
        // Tool/resource specific data
    }
}
```

### Error Response
```json
{
    "success": false,
    "error": "Error description"
}
```

## Installation Requirements

```bash
pip install flask
```

## Production Considerations

- Add authentication/authorization
- Implement rate limiting
- Add input validation and sanitization
- Use proper WSGI server (gunicorn, uWSGI)
- Add CORS headers if needed for browser clients
- Implement proper logging and monitoring
- Add request/response middleware
