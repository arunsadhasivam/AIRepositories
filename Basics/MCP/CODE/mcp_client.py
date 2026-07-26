from abc import ABC, abstractmethod
import os
import json
import requests


# ===================== MCP LAYER (RAG tool: retrieve) =====================

# Contract for MCP client (must override these methods)
class McpClientContract(ABC):

    @abstractmethod
    def list_tools(self):
        # CONTRACT - must override: return tool definitions from MCP server
        pass

    @abstractmethod
    def call_tool(self, tool_name, arguments):
        # CONTRACT - must override: execute tool on MCP server and return result
        pass


# Simple in-memory MCP server simulation exposing a single "retrieve" tool
class RagMcpClient(McpClientContract):

    def __init__(self):
        # Tiny hardcoded "knowledge base" acting as our vector store for hello-world RAG
        self.documents = [
            "MCP stands for Model Context Protocol, used to connect agents to tools.",
            "RAG stands for Retrieval Augmented Generation, it fetches context before answering.",
            "Agents use LLMs to decide which tool to call based on user prompt."
        ]

    def list_tools(self):
        # Overriding contract - defines one tool: "retrieve" with its input schema
        return [
            {
                "name": "retrieve",
                "description": "Retrieve relevant documents/context for a given query text",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "search query text"}
                    },
                    "required": ["query"]
                }
            }
        ]

    def call_tool(self, tool_name, arguments):
        # Overriding contract - only handles "retrieve" tool
        if tool_name == "retrieve":
            query = arguments["query"].lower()
            # Naive keyword match instead of real embeddings (hello-world simplicity)
            matches = [doc for doc in self.documents if any(word in doc.lower() for word in query.split())]
            return {"context": matches if matches else ["No relevant context found."]}
        return {"error": "unknown tool"}

