import os
import json
import requests
from abc import ABC, abstractmethod

# Contract for LLM client (must override this method)
class LlmClientContract(ABC):

    @abstractmethod
    def send_message(self, messages, tools):
        # CONTRACT - must override: call LLM API and return raw response
        pass


# Concrete LLM client - only handles communication with LLM API
class LlmClient(LlmClientContract):

    def __init__(self, api_url, api_key, model):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.session = requests.Session()

    def send_message(self, messages, tools):
        # Overriding contract - sends messages + tool definitions to LLM
        request_body = {
            "model": self.model,
            "max_tokens": 500,
            "messages": messages,
            "tools": tools
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        response = self.session.post(self.api_url, headers=headers,
                                      data=json.dumps(request_body), timeout=30)
        return response.json()
