import os
import operator
import re
from typing import Annotated, List, TypedDict, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

# Configuration
api_key = os.getenv("KIMI_API_KEY")
base_url = "https://api.moonshot.cn/v1"
model_name = "kimi-k2-0905-preview"

llm = ChatOpenAI(
    model_name=model_name,
    api_key=api_key,
    base_url=base_url,
)

# Prompts
ORCHESTRATOR_PROMPT_TEMPLATE = """
Analyze this task and break it down into 2-3 distinct approaches:

Task: {task}

Return your response in this format:

<analysis>
Explain your understanding of the task and which variations would be valuable.
Focus on how each approach serves different aspects of the task.
</analysis>

<tasks>
    <task>
    <type>formal</type>
    <description>Write a precise, technical version that emphasizes specifications</description>
    </task>
    <task>
    <type>conversational</type>
    <description>Write an engaging, friendly version that connects with readers</description>
    </task>
</tasks>
"""

WORKER_PROMPT_TEMPLATE = """
Generate content based on:
Task: {original_task}
Style: {task_type}
Guidelines: {task_description}

Return your response in this format:

<response>
Your content here, maintaining the specified style and fully addressing requirements.
</response>
"""

# State

class SubTask(TypedDict):
    type: str
    description: str

class WorkerResult(TypedDict):
    type: str
    content: str

class OrchestratorState(TypedDict):
    original_task: str
    subtasks: List[SubTask]
    results: Annotated[List[WorkerResult], operator.add]
    final_output: str

# Nodes

def orchestrator_node(state: OrchestratorState):
    """Generate subtasks for the original task."""
    original_task = state["original_task"]
    prompt = ORCHESTRATOR_PROMPT_TEMPLATE.format(task=original_task)

    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content

    tasks = []
    task_blocks = re.findall(r"<task>(.*?)</task>", content, re.DOTALL)

    for block in task_blocks:
        type_match = re.search(r"<type>(.*?)</type>", block, re.DOTALL)
        desc_match = re.search(r"<description>(.*?)</description>", block, re.DOTALL)

        if type_match and desc_match:
            tasks.append(
                {
                    "type": type_match.group(1).strip(),
                    "description": desc_match.group(1).strip(),
                }
            )

    if not tasks:
        tasks = [{"type": "default", "description": "Process the task normally."}]

    return {"subtasks": tasks}


def map_workers(state: OrchestratorState):
    """Fan out to one worker per subtask."""
    return [
        Send("worker", {"subtask": t, "original_task": state["original_task"]})
        for t in state["subtasks"]
    ]


class WorkerState(TypedDict):
    subtask: SubTask
    original_task: str


def worker_node(state: WorkerState):
    """Execute a single subtask."""
    subtask = state["subtask"]
    original_task = state["original_task"]

    prompt = WORKER_PROMPT_TEMPLATE.format(
        original_task=original_task,
        task_type=subtask["type"],
        task_description=subtask["description"],
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content

    match = re.search(r"<response>(.*?)</response>", content, re.DOTALL)
    if match:
        result_content = match.group(1).strip()
    else:
        result_content = content.strip()

    result = {"type": subtask["type"], "content": result_content}
    return {"results": [result]}

def synthesizer_node(state: OrchestratorState):
    """Aggregate worker results."""
    results = state["results"]
    subtasks = state["subtasks"]

    if len(results) < len(subtasks):
        return {}

    final_str = "=== Final Synthesized Output ===\n\n"
    for res in results:
        final_str += f"--- Style: {res['type']} ---\n"
        final_str += f"{res['content']}\n\n"

    return {"final_output": final_str}

# Graph

workflow = StateGraph(OrchestratorState)

workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("worker", worker_node)
workflow.add_node("synthesizer", synthesizer_node)

workflow.add_edge(START, "orchestrator")

workflow.add_conditional_edges(
    "orchestrator",
    map_workers,
    ["worker"],
)

workflow.add_edge("worker", "synthesizer")
workflow.add_edge("synthesizer", END)

app = workflow.compile()

# Main

if __name__ == "__main__":
    import sys
    
    print("=== Orchestrator-Workers Agent Started ===")
    
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        user_input = input("Please enter your task: ")
        
    if not user_input:
        print("No task provided. Exiting.")
        sys.exit(0)
        
    print(f"\nProcessing task: {user_input}...\n")
    
    inputs = {
        "original_task": user_input,
        "subtasks": [],
        "results": [],
        "final_output": ""
    }
    
    for event in app.stream(inputs):
        for key, value in event.items():
            if key == "orchestrator":
                print(f"[Orchestrator] Generated {len(value['subtasks'])} subtasks.")
                for t in value["subtasks"]:
                    print(f"  - {t['type']}: {t['description'][:50]}...")
            elif key == "worker":
                result = value["results"][0]
                print(f"[Worker] Finished task: {result['type']}")
            elif key == "synthesizer":
                if "final_output" in value:
                    print("\n[Synthesizer] Aggregation complete.")
                    print(value["final_output"])
