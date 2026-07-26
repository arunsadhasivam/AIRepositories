# Agent depends only on contracts, orchestrates RAG flow: retrieve -> augment -> generate
from mcp_client import McpClientContract, RagMcpClient
from llm_client import LlmClientContract
from ollama_client import OllamaLlmClient
class RagAgent:

    def __init__(self, mcp_client: McpClientContract, llm_client: LlmClientContract):
        self.mcp_client = mcp_client
        self.llm_client = llm_client

    def convert_mcp_tools_to_llm_format(self, mcp_tools):
        # Reformats MCP tool schema into LLM-compatible tool list
        return [
            {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
            for t in mcp_tools
        ]

    def run(self, user_query):
        # Step 1: Get available tools (here: "retrieve") from MCP client
        mcp_tools = self.mcp_client.list_tools()
        llm_tools = self.convert_mcp_tools_to_llm_format(mcp_tools)

        # Step 2: Send user query + tools to LLM, LLM decides to call "retrieve"
        messages = [{"role": "user", "content": user_query}]
     
        llm_response = self.llm_client.send_message(messages, llm_tools)
        # Step 3: Check if LLM picked the retrieve tool (delegated to LLM client's own parsing)
        tool_use_block = self.llm_client.extract_tool_use_block(llm_response)
        if tool_use_block is None:
            print("Direct answer:", self.llm_client.extract_text_block(llm_response))
            return
        tool_name = tool_use_block["name"]
        tool_input = tool_use_block["input"]
        tool_use_id = tool_use_block["id"]
        print(f"LLM selected tool: {tool_name} with input: {tool_input}")

        # Step 4: Agent calls MCP client to retrieve context (RAG's "Retrieval" step)
        retrieved_context = self.mcp_client.call_tool(tool_name, tool_input)
        print("Retrieved context:", retrieved_context)

        # Step 5: Send retrieved context back to LLM (RAG's "Augmented Generation" step)
        messages.append(self.llm_client.build_tool_result_message(tool_use_id, retrieved_context))
        final_response = self.llm_client.send_message(messages, llm_tools)

        print("Final Answer:", self.llm_client.extract_text_block(final_response))

# ===================== ENTRY POINT =====================
if __name__ == "__main__":
    mcp_client = RagMcpClient()
    llm_client = OllamaLlmClient(
        api_url="http://localhost:11434/api/chat",
        model="mistral:latest"                          # ensure model is pulled: `ollama pull llama3`
    )
    agent = RagAgent(mcp_client, llm_client)
    agent.run("What is MCP in AI?")