import requests
import json


# Concrete LLM client using Ollama (local self-hosted LLM) instead of Anthropic API
class OllamaLlmClient:

    def __init__(self, api_url="http://localhost:11434/api/chat", model="llama3"):
        self.api_url = api_url                # Ollama local server endpoint
        self.model = model                    # model name pulled via `ollama pull llama3`
        self.session = requests.Session()

    def send_message(self, messages, tools):
        # Overriding contract - Ollama's /api/chat supports tools param (function calling)
        request_body = {
            "model": self.model,
            "messages": messages,             # conversation history
            "tools": tools,                    # tool definitions (Ollama supports OpenAI-style tools)
            "stream": False                    # get full response at once, not streamed chunks
        }

        response = self.session.post(
            self.api_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(request_body),
            timeout=60                         # local inference can be slower than hosted API
        )
        return response.json()

    # Ollama response format differs from Anthropic - normalize tool_use extraction
    def extract_tool_use_block(self, ollama_response):
        message = ollama_response.get("message", {})
        tool_calls = message.get("tool_calls", [])
        if tool_calls:
            call = tool_calls[0]
            return {
                "name": call["function"]["name"],
                "input": call["function"]["arguments"],
                "id": "ollama-call-1"          # Ollama doesn't return an id, so we generate one
            }
        return None

    # Extracts plain text answer from Ollama response
    def extract_text_block(self, ollama_response):
        return ollama_response.get("message", {}).get("content", "")

    # Builds tool_result message in Ollama's expected format (role: tool)
    def build_tool_result_message(self, tool_use_id, tool_result):
        return {
            "role": "tool",                    # Ollama expects role "tool" for tool results
            "content": json.dumps(tool_result)
        }