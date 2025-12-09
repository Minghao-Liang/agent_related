import asyncio
import os
import json
import sys

# Add parent directory to path to allow imports if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import tool
from tool_registry import ToolRegistry

# Configuration
API_KEY = os.getenv("SILICONFLOW_API_KEY")
BASE_URL = "https://api.siliconflow.cn/v1"
MODEL_NAME = "Qwen/Qwen3-8B"

# Initialize Client
# We assume we run this from the MCP-Zero directory
# Use sys.executable to ensure we use the same python environment
server_env = os.environ.copy()

client = MultiServerMCPClient({
    "perception-tools": {
        "command": sys.executable,
        "args": ["perception-tools/server.py"],
        "transport": "stdio",
        "env": server_env
    },
})

# Tool Registry
registry = ToolRegistry()

def _extract_usage(resp):
    md = getattr(resp, "response_metadata", {}) or {}
    ak = getattr(resp, "additional_kwargs", {}) or {}
    usage = ak.get("usage") or md.get("token_usage") or {}
    pt = usage.get("prompt_tokens") or usage.get("input_tokens") or usage.get("total_input_tokens")
    ct = usage.get("completion_tokens") or usage.get("output_tokens") or usage.get("total_output_tokens")
    tt = usage.get("total_tokens")
    pt = pt or 0
    ct = ct or 0
    tt = tt or (pt + ct)
    return pt, ct, tt

def _init_metrics():
    return {
        "steps": 0,
        "tool_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "context_tool_count_initial": 0,
        "context_tool_count_final": 0,
        "context_tool_count_over_time": [],
        "discovered_tools_count": 0,
        "discovered_tools": [],
        "used_tools_sequence": [],
        "success": False
    }

def _print_metrics(metrics):
    try:
        print("\nMETRICS:")
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
    except Exception:
        print(metrics)

@tool
def discover_tools(query: str):
    """
    Search for available tools based on a natural language description.
    Returns the top relevant tools and their schemas.
    Use this when you don't have a tool to perform a specific task.
    """
    # Search registry
    results = registry.search(query, top_k=5)
    if not results:
        return json.dumps([])
    
    schemas = []
    for t in results:
        # Create a simplified schema representation
        schema = {
            "name": t.name,
            "description": t.description,
            "args": t.args
        }
        schemas.append(schema)
    return json.dumps(schemas, indent=2)

async def run_control_group(task, all_tools):
    print("\n" + "="*50)
    print("Running Control Group (All Tools Injected)")
    print("="*50)
    
    model = ChatOpenAI(model=MODEL_NAME, api_key=API_KEY, base_url=BASE_URL)
    metrics = _init_metrics()
    metrics["context_tool_count_initial"] = len(all_tools)
    metrics["context_tool_count_final"] = len(all_tools)
    
    # Inject ALL tools
    model_with_tools = model.bind_tools(all_tools)
    
    messages = [
        SystemMessage(content="You are a helpful assistant with access to many tools. Use them to solve the user's task."),
        HumanMessage(content=task)
    ]
    
    # Simple loop
    for step in range(15):
        try:
            print(f"\n--- Step {step + 1} ---")
            response = await model_with_tools.ainvoke(messages)
            messages.append(response)
            metrics["steps"] += 1
            pt, ct, tt = _extract_usage(response)
            metrics["input_tokens"] += pt
            metrics["output_tokens"] += ct
            metrics["total_tokens"] += tt
            
            if not response.tool_calls:
                print("Final Answer:", response.content)
                metrics["success"] = True
                break
                
            print(f"Tool Calls: {[tc['name'] for tc in response.tool_calls]}")
            metrics["tool_calls"] += len(response.tool_calls)
            metrics["used_tools_sequence"].extend([tc["name"] for tc in response.tool_calls])
            
            for tc in response.tool_calls:
                tool_name = tc["name"]
                args = tc["args"]
                
                # Find tool
                selected_tool = next((t for t in all_tools if t.name == tool_name), None)
                if selected_tool:
                    try:
                        print(f"Executing {tool_name}...")
                        res = await selected_tool.ainvoke(args)
                        # Truncate long outputs for display
                        display_res = str(res)
                        if len(display_res) > 200:
                            display_res = display_res[:200] + "..."
                        print(f"Result: {display_res}")
                    except Exception as e:
                        res = f"Error: {str(e)}"
                        print(res)
                else:
                    res = "Tool not found."
                    print(res)
                
                messages.append(ToolMessage(content=str(res), tool_call_id=tc["id"], name=tool_name))
        except Exception as e:
            print("Error in control loop:", e)
            import traceback
            traceback.print_exc()
            break
    _print_metrics(metrics)
    return metrics

async def run_experimental_group(task, all_tools):
    print("\n" + "="*50)
    print("Running Experimental Group (Active Discovery)")
    print("="*50)
    
    # Initialize Registry
    registry.register_tools(all_tools)
    
    basic_tool_names = ["code_interpreter"]
    current_tools = [t for t in all_tools if t.name in basic_tool_names]
    metrics = _init_metrics()
    metrics["context_tool_count_initial"] = len(current_tools)
    
    # Add discover_tools
    current_tools.append(discover_tools)
    
    print(f"Initial Tools: {[t.name for t in current_tools]}")
    
    model = ChatOpenAI(model=MODEL_NAME, api_key=API_KEY, base_url=BASE_URL)
    
    messages = [
        SystemMessage(content="You are a helpful assistant. You have limited tools initially. "
                              "If you need to perform a task and don't have the right tool, "
                              "use 'discover_tools' to find relevant tools by describing what you need. "
                              "Once you discover them, they will be added to your toolkit and you can use them in the next step."),
        HumanMessage(content=task)
    ]
    
    for step in range(15):
        # Bind CURRENT tools
        model_with_tools = model.bind_tools(current_tools)
        
        try:
            print(f"\n--- Step {step + 1} ---")
            metrics["steps"] += 1
            metrics["context_tool_count_over_time"].append(len(current_tools))
            response = await model_with_tools.ainvoke(messages)
            messages.append(response)
            pt, ct, tt = _extract_usage(response)
            metrics["input_tokens"] += pt
            metrics["output_tokens"] += ct
            metrics["total_tokens"] += tt
            
            if not response.tool_calls:
                print("Final Answer:", response.content)
                metrics["success"] = True
                break
                
            print(f"Tool Calls: {[tc['name'] for tc in response.tool_calls]}")
            metrics["tool_calls"] += len(response.tool_calls)
            metrics["used_tools_sequence"].extend([tc["name"] for tc in response.tool_calls])
            
            new_tools_found = False
            
            for tc in response.tool_calls:
                tool_name = tc["name"]
                args = tc["args"]
                
                if tool_name == "discover_tools":
                    # Execute discovery
                    print(f"Executing discover_tools with args: {args}")
                    res = discover_tools.invoke(args)
                    print(f"Discovery Result (Preview): {res[:150]}...")
                    
                    # Parse result to update current_tools
                    try:
                        found_schemas = json.loads(res)
                        for schema in found_schemas:
                            t_name = schema["name"]
                            # Check if already in current_tools
                            if t_name not in [t.name for t in current_tools]:
                                tool_obj = registry.get_tool(t_name)
                                if tool_obj:
                                    current_tools.append(tool_obj)
                                    print(f"  >>> ACTIVATING NEW TOOL: {t_name}")
                                    new_tools_found = True
                                    metrics["discovered_tools"].append(t_name)
                                    metrics["discovered_tools_count"] += 1
                    except Exception as e:
                        print(f"Error parsing discovery result: {e}")
                        
                    messages.append(ToolMessage(content=res, tool_call_id=tc["id"], name=tool_name))
                    
                else:
                    # Regular tool execution
                    selected_tool = next((t for t in current_tools if t.name == tool_name), None)
                    if selected_tool:
                        try:
                            print(f"Executing {tool_name}...")
                            res = await selected_tool.ainvoke(args)
                            display_res = str(res)
                            if len(display_res) > 200:
                                display_res = display_res[:200] + "..."
                            print(f"Result: {display_res}")
                        except Exception as e:
                            res = f"Error: {str(e)}"
                            print(res)
                    else:
                        res = "Tool not found. Please use discover_tools to find it first."
                        print(f"Failed to execute {tool_name}: {res}")
                    
                    messages.append(ToolMessage(content=str(res), tool_call_id=tc["id"], name=tool_name))
            
            if new_tools_found:
                tool_names_str = ", ".join([t.name for t in current_tools])
                print(f"Updating system with available tools: {tool_names_str}")
                messages.append(SystemMessage(content=f"System Update: You have successfully discovered new tools. Available tools are now: {tool_names_str}"))

        except Exception as e:
            print("Error in experimental loop:", e)
            import traceback
            traceback.print_exc()
            break
    metrics["context_tool_count_final"] = len(current_tools)
    _print_metrics(metrics)
    return metrics

async def main():
    print("Connecting to MCP servers and loading tools...")
    try:
        # Note: client.get_tools() connects and fetches tools
        all_tools = await client.get_tools()
        print(f"Successfully loaded {len(all_tools)} tools from MCP servers.")
    except Exception as e:
        print(f"Failed to load tools: {e}")
        return

    task = "Inquire about the latest stock price of NVIDIA Corporation and conduct a search for related news to analyze the underlying causes"
    
    print("\n" + "*"*60)
    print("STARTING EXPERIMENT 1: Task for Control Group")
    print("*"*60)
    m1 = await run_control_group(task, all_tools)

    print("\n" + "*"*60)
    print("STARTING EXPERIMENT 2: Task for Experimental Group")
    print("*"*60)
    m2 = await run_experimental_group(task, all_tools)

    def _print_ascii_dashboard(name1, name2, a, b):
        metrics = [
            ("steps", str(a.get("steps")), str(b.get("steps"))),
            ("tool_calls", str(a.get("tool_calls")), str(b.get("tool_calls"))),
            ("input_tokens", str(a.get("input_tokens")), str(b.get("input_tokens"))),
            ("output_tokens", str(a.get("output_tokens")), str(b.get("output_tokens"))),
            ("total_tokens", str(a.get("total_tokens")), str(b.get("total_tokens"))),
            ("tools_initial", str(a.get("context_tool_count_initial")), str(b.get("context_tool_count_initial"))),
            ("tools_final", str(a.get("context_tool_count_final")), str(b.get("context_tool_count_final"))),
            ("discovered_tools", str(a.get("discovered_tools_count")), str(b.get("discovered_tools_count"))),
            ("success", str(a.get("success")), str(b.get("success"))),
        ]
        h1 = "Metric"
        h2 = name1
        h3 = name2
        w1 = max(len(h1), max(len(m[0]) for m in metrics))
        w2 = max(len(h2), max(len(m[1]) for m in metrics))
        w3 = max(len(h3), max(len(m[2]) for m in metrics))
        sep = "+" + "-"*(w1+2) + "+" + "-"*(w2+2) + "+" + "-"*(w3+2) + "+"
        print("\n" + sep)
        print("| " + h1.ljust(w1) + " | " + h2.ljust(w2) + " | " + h3.ljust(w3) + " |")
        print(sep)
        for m in metrics:
            print("| " + m[0].ljust(w1) + " | " + m[1].rjust(w2) + " | " + m[2].rjust(w3) + " |")
        print(sep)

    _print_ascii_dashboard("Task for Control Group", "Task for Experimental Group", m1, m2)

if __name__ == "__main__":
    asyncio.run(main())
