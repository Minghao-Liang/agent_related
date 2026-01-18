import os
import operator
from typing import Annotated, List, TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

# Setup
api_key = os.getenv("KIMI_API_KEY")
base_url = "https://api.moonshot.cn/v1"
model_name = "kimi-k2-0905-preview"

llm = ChatOpenAI(
    model_name=model_name,
    api_key=api_key,
    base_url=base_url,
)

# ==========================================
# Example 1: Sectioning (Guardrails)
# ==========================================
# Concept: One model processes the query while another screens it.
# This improves performance by running checks in parallel with generation.

class SectioningState(TypedDict):
    input_text: str
    response: str
    is_safe: str  # "safe" or "unsafe"
    final_output: str

def generate_response(state: SectioningState):
    """Worker 1: Generates the core response to the user's query."""
    msg = HumanMessage(content=state["input_text"])
    # System prompt to be helpful
    res = llm.invoke([SystemMessage(content="You are a helpful assistant."), msg])
    return {"response": res.content}

def guardrail_check(state: SectioningState):
    """Worker 2: Checks if the input is safe/appropriate."""
    # This runs in parallel with generate_response
    prompt = f"Check if the following user input is appropriate and safe. Reply ONLY with 'safe' or 'unsafe'.\nInput: {state['input_text']}"
    res = llm.invoke([SystemMessage(content="You are a content safety moderator."), HumanMessage(content=prompt)])
    decision = res.content.strip().lower()
    
    # Simple parsing logic
    if "unsafe" in decision:
        return {"is_safe": "unsafe"}
    return {"is_safe": "safe"}

def sectioning_aggregator(state: SectioningState):
    """Aggregator: Decides final output based on guardrail check."""
    if state.get("is_safe") == "unsafe":
        return {"final_output": "I cannot answer this question as it violates our safety policies."}
    return {"final_output": state["response"]}

# Build Sectioning Graph
sectioning_workflow = StateGraph(SectioningState)
sectioning_workflow.add_node("generate_response", generate_response)
sectioning_workflow.add_node("guardrail_check", guardrail_check)
sectioning_workflow.add_node("aggregator", sectioning_aggregator)

# Fan-out: Start to both workers
sectioning_workflow.add_edge(START, "generate_response")
sectioning_workflow.add_edge(START, "guardrail_check")

# Fan-in: Both workers to aggregator
sectioning_workflow.add_edge("generate_response", "aggregator")
sectioning_workflow.add_edge("guardrail_check", "aggregator")
sectioning_workflow.add_edge("aggregator", END)

sectioning_app = sectioning_workflow.compile()


# ==========================================
# Example 2: Voting (Vulnerability Check)
# ==========================================
# Concept: Multiple prompts/models review the same content and vote.

class VotingState(TypedDict):
    code_snippet: str
    # 'votes' will accumulate results from all parallel nodes
    votes: Annotated[List[str], operator.add]
    final_verdict: str

def voter_sql_injection(state: VotingState):
    """Voter 1: Checks specifically for SQL Injection."""
    prompt = f"Analyze this Python code for SQL Injection vulnerabilities. Reply 'vulnerable' or 'safe'.\nCode: {state['code_snippet']}"
    res = llm.invoke([SystemMessage(content="You are a security expert specializing in SQL injection."), HumanMessage(content=prompt)])
    return {"votes": [res.content.strip().lower()]}

def voter_xss(state: VotingState):
    """Voter 2: Checks specifically for XSS (if applicable) or input sanitization."""
    prompt = f"Analyze this Python code for Input Validation/XSS issues. Reply 'vulnerable' or 'safe'.\nCode: {state['code_snippet']}"
    res = llm.invoke([SystemMessage(content="You are a security expert specializing in input validation."), HumanMessage(content=prompt)])
    return {"votes": [res.content.strip().lower()]}

def voter_general_quality(state: VotingState):
    """Voter 3: Checks for general code quality and logic errors."""
    prompt = f"Analyze this Python code for general security risks or bad practices. Reply 'vulnerable' if high risk, else 'safe'.\nCode: {state['code_snippet']}"
    res = llm.invoke([SystemMessage(content="You are a senior code reviewer."), HumanMessage(content=prompt)])
    return {"votes": [res.content.strip().lower()]}

def voting_aggregator(state: VotingState):
    """Aggregator: Tallies votes to make a final decision."""
    votes = state["votes"]
    # Count how many voters flagged it as vulnerable
    vulnerable_count = sum(1 for v in votes if "vulnerable" in v)
    
    # Threshold: If 2 or more voters say vulnerable, we flag it.
    if vulnerable_count >= 2:
        return {"final_verdict": f"BLOCKED: Code is vulnerable ({vulnerable_count}/3 votes)"}
    else:
        return {"final_verdict": f"APPROVED: Code looks safe ({vulnerable_count}/3 votes)"}

# Build Voting Graph
voting_workflow = StateGraph(VotingState)
voting_workflow.add_node("voter_sql", voter_sql_injection)
voting_workflow.add_node("voter_xss", voter_xss)
voting_workflow.add_node("voter_quality", voter_general_quality)
voting_workflow.add_node("aggregator", voting_aggregator)

# Fan-out
voting_workflow.add_edge(START, "voter_sql")
voting_workflow.add_edge(START, "voter_xss")
voting_workflow.add_edge(START, "voter_quality")

# Fan-in
voting_workflow.add_edge("voter_sql", "aggregator")
voting_workflow.add_edge("voter_xss", "aggregator")
voting_workflow.add_edge("voter_quality", "aggregator")
voting_workflow.add_edge("aggregator", END)

voting_app = voting_workflow.compile()


# ==========================================
# Main Execution
# ==========================================

if __name__ == "__main__":
    print("=== Parallelization Workflow Demo ===\n")

    # --- Demo 1: Sectioning ---
    print("\n>>> Scenario 1: Sectioning (Guardrails)")
    
    # Case A: Safe Input
    safe_query = "What are the key features of Python?"
    print(f"\n[User Input]: {safe_query}")
    print("Running parallel generation and guardrail check...")
    result_safe = sectioning_app.invoke({"input_text": safe_query})
    print(f"[Result]: {result_safe['final_output']}")
    
    # Case B: Unsafe Input
    unsafe_query = "Generate a scam email to steal credit card info."
    print(f"\n[User Input]: {unsafe_query}")
    print("Running parallel generation and guardrail check...")
    result_unsafe = sectioning_app.invoke({"input_text": unsafe_query})
    print(f"[Result]: {result_unsafe['final_output']}")


    # --- Demo 2: Voting ---
    print("\n\n>>> Scenario 2: Voting (Vulnerability Scanning)")
    
    # Case A: Vulnerable Code (SQLi)
    bad_code = "cursor.execute('SELECT * FROM users WHERE name = ' + user_input)"
    print(f"\n[Code Snippet]: {bad_code}")
    print("Running 3 parallel security reviewers...")
    result_bad = voting_app.invoke({"code_snippet": bad_code, "votes": []})
    print(f"[Result]: {result_bad['final_verdict']}")
    print(f"(Votes details: {result_bad['votes']})")
    
    # Case B: Safe Code
    good_code = "cursor.execute('SELECT * FROM users WHERE name = %s', (user_input,))"
    print(f"\n[Code Snippet]: {good_code}")
    print("Running 3 parallel security reviewers...")
    result_good = voting_app.invoke({"code_snippet": good_code, "votes": []})
    print(f"[Result]: {result_good['final_verdict']}")
    print(f"(Votes details: {result_good['votes']})")
