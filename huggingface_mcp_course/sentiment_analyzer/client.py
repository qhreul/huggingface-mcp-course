import os

import gradio as gr
from mcp import StdioServerParameters
from smolagents import CodeAgent, LiteLLMModel, ToolCollection
from smolagents.mcp_client import MCPClient

# Create a MCP Client for the Sentiment Analysis server running locally
mcp_client = MCPClient(
    {"url": "http://127.0.0.1:7860/gradio_api/mcp/sse"}
)
tools = mcp_client.get_tools()

# Print name of description of the available tools
print('\n'.join(f'{t.name}: {t.description}' for t in tools))

# Create instance to access LLM model served through Ollama (api_base = "http://localhost:11434")
model = LiteLLMModel(
    model_id='hf.co/unsloth/Devstral-Small-2505-GGUF:Q4_K_M'
)
# Create an instance of code agent for the intaraction
agent = CodeAgent(tools=[*tools], model=model, additional_authorized_imports=["json", "ast", "urllib", "base64"])

try:
    # Define the Gradio Chat Interface Client
    demo = gr.ChatInterface(
        fn=lambda message, history: str(agent.run(message)),
        type="messages",
        examples=["Analyze the sentiment of the following text 'This is awesome'"],
        title="Agent Client for Sentiment Analysis",
        description="This is a simple agent that uses MCP tools to assess the sentiment of text"
    )
    demo.launch()
finally:
    mcp_client.disconnect()
