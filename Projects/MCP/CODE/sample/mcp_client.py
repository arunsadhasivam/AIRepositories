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
