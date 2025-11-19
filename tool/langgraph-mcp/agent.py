"""
Interactive agent entry:
- Starts and connects to the MCP Perception Tools server (as a subprocess)
- Builds a LangChain agent that prefers tools for retrieval, parsing, and computation
- Drives conversation with the Moonshot Kimi model and supports asynchronous interaction
"""
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
import asyncio
import os

# Initialize a multi-server MCP client and register the project's Perception Tools server.
client = MultiServerMCPClient({
    "perception-tools": {
        "command": "python",
        "args": ["perception-tools/server.py"],
        "transport": "stdio",
    },
})

# Configure the chat model: Moonshot Kimi
# Note: The API key is read from env var KIMI_API_KEY; missing key will cause invocation failures.
model = ChatOpenAI(
    model_name="kimi-k2-0905-preview",
    api_key=os.getenv("KIMI_API_KEY"),
    base_url="https://api.moonshot.cn/v1",
)


async def main():
    """Start the agent, load tools, and handle interactive inputs."""
    # Fetch tool set from the MCP server and create the LangChain agent.
    tools = await client.get_tools()
    print(f"Loaded tools: {len(tools)}")
    agent = create_agent(model, tools)

    # System prompt: prefer tool usage; avoid fabricating external information.
    system_prompt = (
        "Prefer using available tools. For web search, file reading, parsing documents/web pages/media, public/private data retrieval, summarization, OCR, and audio/video processing, call the appropriate tool first; "
        "do not fabricate external information. When numerical computation is required, use a calculation-capable tool instead of computing within the model."
    )

    print("Interactive Agent. Type 'exit' to quit.")
    while True:
        try:
            # Read terminal input asynchronously to keep the event loop responsive.
            user_input = await asyncio.to_thread(input, ">> ")
        except EOFError:
            break

        user_input = (user_input or "").strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break

        # Invoke the agent and obtain the message sequence (including tool calls and final reply).
        result = await agent.ainvoke({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        })

        # Collect names of tools used in this turn for observability.
        messages = result.get("messages", [])
        tools_used = []
        for m in messages:
            tc = getattr(m, "tool_calls", None)
            if tc:
                for call in tc:
                    name = call.get("name") or (call.get("function") or {}).get("name")
                    if name:
                        tools_used.append(name)
            if m.__class__.__name__ == "ToolMessage":
                name = getattr(m, "tool_name", None) or getattr(m, "name", None)
                if name:
                    tools_used.append(name)

        # Print tool usage and the final assistant reply.
        if tools_used:
            print(f"Tools used: {', '.join(dict.fromkeys(tools_used))}")
        else:
            print("Tools used: None")
        final = messages[-1].content if messages else ""
        print(f"Assistant: {final}")

if __name__ == "__main__":
    asyncio.run(main())