import os
from typing import TypedDict, Optional, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

# --- LLM Setup ---
api_key = os.getenv("KIMI_API_KEY")
base_url = "https://api.moonshot.cn/v1"
model_name = "kimi-k2-0905-preview"

llm = ChatOpenAI(
    model_name=model_name,
    api_key=api_key,
    base_url=base_url,
)

# --- State Definition ---
class TranslationState(TypedDict):
    source_text: str
    translation: Optional[str]
    feedback: Optional[str]
    status: Literal["accept", "reject"]
    iteration: int

# --- Nodes ---

def generator_node(state: TranslationState):
    """Generates a translation or refines it based on feedback."""
    source_text = state["source_text"]
    current_translation = state.get("translation")
    feedback = state.get("feedback")
    iteration = state.get("iteration", 0)

    if not current_translation or not feedback:
        # Initial translation
        system_prompt = "You are an expert literary translator. Translate the following text into English, preserving the nuance, tone, and style of the original."
        user_prompt = f"Original Text:\n{source_text}"
    else:
        # Refinement
        system_prompt = "You are an expert literary translator. Refine the translation based on the critic's feedback. Do not add conversational filler, just output the refined translation."
        user_prompt = (
            f"Original Text:\n{source_text}\n\n"
            f"Current Translation:\n{current_translation}\n\n"
            f"Critic's Feedback:\n{feedback}\n\n"
            "Please provide the refined translation:"
        )

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    
    return {
        "translation": response.content.strip(),
        "iteration": iteration + 1
    }

def evaluator_node(state: TranslationState):
    """Evaluates the translation and provides feedback."""
    source_text = state["source_text"]
    translation = state["translation"]
    
    system_prompt = (
        "You are a strict literary critic. Evaluate the translation against the original text.\n"
        "1. If the translation captures the nuance, tone, and style accurately, return 'ACCEPT'.\n"
        "2. If there are issues, return 'REJECT' followed by specific, constructive feedback on how to improve it.\n"
        "Format your response exactly as:\n"
        "Status: [ACCEPT/REJECT]\n"
        "Feedback: [Your feedback here if rejected, otherwise leave empty]"
    )
    
    user_prompt = (
        f"Original Text:\n{source_text}\n\n"
        f"Translation:\n{translation}"
    )

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    
    content = response.content.strip()
    
    # Simple parsing
    if "Status: ACCEPT" in content:
        status = "accept"
        feedback = ""
    else:
        status = "reject"
        # Extract feedback after "Feedback:"
        parts = content.split("Feedback:", 1)
        feedback = parts[1].strip() if len(parts) > 1 else content

    return {
        "status": status,
        "feedback": feedback
    }

# --- Graph Construction ---

workflow = StateGraph(TranslationState)

workflow.add_node("generator", generator_node)
workflow.add_node("evaluator", evaluator_node)

workflow.add_edge(START, "generator")
workflow.add_edge("generator", "evaluator")

def should_continue(state: TranslationState) -> Literal["generator", END]:
    """Decides whether to loop back or end."""
    status = state["status"]
    iteration = state["iteration"]
    
    # Max iterations to prevent infinite loops
    MAX_ITERATIONS = 3
    
    if status == "accept" or iteration >= MAX_ITERATIONS:
        return END
    return "generator"

workflow.add_conditional_edges(
    "evaluator",
    should_continue,
    {
        "generator": "generator",
        END: END
    }
)

app = workflow.compile()

# --- Demo Run ---
if __name__ == "__main__":
    print("=== Literary Translation Evaluator-Optimizer Started ===\n")
    
    # A slightly tricky literary sentence (Chinese to English)
    source_text = "那是一个美好的时代，那是一个糟糕的时代；那是智慧的年头，那是愚昧的年头。"
    
    print(f"Source Text: {source_text}\n")
    
    initial_state = {
        "source_text": source_text,
        "iteration": 0,
        "translation": None,
        "feedback": None,
        "status": "reject" # default
    }
    
    # Run the workflow using stream to see intermediate steps
    for event in app.stream(initial_state):
        for key, value in event.items():
            print(f"--- Node: {key} ---")
            if key == "generator":
                print(f"Translation (Iter {value['iteration']}):\n{value['translation']}\n")
            elif key == "evaluator":
                print(f"Status: {value['status'].upper()}")
                if value['status'] == 'reject':
                    print(f"Feedback: {value['feedback']}\n")
    
    print("\n=== Workflow Completed ===")
