import os
from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain.agents import create_agent

api_key = os.getenv("KIMI_API_KEY")
base_url = "https://api.moonshot.cn/v1"
model_name = "kimi-k2-0905-preview"

llm = ChatOpenAI(
    model_name=model_name,
    api_key=api_key,
    base_url=base_url,
)

# --- Specialized tool definitions ---

@tool
def policy_lookup(query: str):
    """Look up general company policies."""
    return "Policy: We provide 24/7 support. Return requests must be submitted within 30 days."

@tool
def process_refund(order_id: str, reason: str):
    """Process a refund request for a specific order."""
    return f"Refund processed for order #{order_id}. Reason: {reason}."

@tool
def system_diagnostic(service_name: str):
    """Check the operational status of a technical service."""
    return f"Diagnostic result: Service '{service_name}' is running normally. Current availability: 99.9%."

# --- Nodes implementation ---

general_agent = create_agent(
    llm,
    tools=[policy_lookup],
    system_prompt="You are a general customer support agent responsible for answering general inquiries."
)

refund_agent = create_agent(
    llm,
    tools=[process_refund],
    system_prompt="You are a refunds specialist handling refunds and billing issues. If the user did not provide an order ID, ask for it."
)

tech_agent = create_agent(
    llm,
    tools=[system_diagnostic],
    system_prompt="You are a technical support engineer responsible for system issues and technical diagnostics."
)

# --- Workflow state definition ---

class RouterState(MessagesState):
    """Workflow state that includes the routing decision."""
    route: Literal["general", "refund", "tech"]

# --- Router node implementation ---

def router_node(state: RouterState):
    messages = state["messages"]
    last_message = messages[-1]

    system_prompt = (
        "You are a router. Classify the user's message into exactly one of the following categories:\n"
        "1. 'general' - General questions, policy lookups, or greetings.\n"
        "2. 'refund' - Refund requests, billing issues, or returns.\n"
        "3. 'tech' - Technical issues, bugs, or system status checks.\n\n"
        "Return only the category name: 'general', 'refund', or 'tech'."
    )

    response = llm.invoke([SystemMessage(content=system_prompt), last_message])
    decision = response.content.strip().lower()

    # Normalize output to match the Literal
    if "refund" in decision:
        return {"route": "refund"}
    elif "tech" in decision:
        return {"route": "tech"}
    else:
        return {"route": "general"}

# --- Agent wrapper nodes ---

def call_general(state: RouterState):
    response = general_agent.invoke({"messages": state["messages"]})
    return {"messages": [response["messages"][-1]]}

def call_refund(state: RouterState):
    response = refund_agent.invoke({"messages": state["messages"]})
    return {"messages": [response["messages"][-1]]}

def call_tech(state: RouterState):
    response = tech_agent.invoke({"messages": state["messages"]})
    return {"messages": [response["messages"][-1]]}

# --- Graph structure definition ---

workflow = StateGraph(RouterState)

workflow.add_node("router", router_node)
workflow.add_node("general_support", call_general)
workflow.add_node("refund_support", call_refund)
workflow.add_node("tech_support", call_tech)

workflow.add_edge(START, "router")

# Conditional routing
workflow.add_conditional_edges(
    "router",
    lambda state: state["route"],
    {
        "general": "general_support",
        "refund": "refund_support",
        "tech": "tech_support"
    }
)

workflow.add_edge("general_support", END)
workflow.add_edge("refund_support", END)
workflow.add_edge("tech_support", END)

app = workflow.compile()

# --- Demo run ---

if __name__ == "__main__":
    print("=== Customer support routing workflow started ===\n")

    examples = [
        "What is your return policy?",
        "My order #12345 is broken. I want a refund.",
        "The login service seems down. Can you check it for me?"
    ]

    for i, query in enumerate(examples, 1):
        print(f"\nUser input {i}: {query}")
        result = app.invoke({"messages": [HumanMessage(content=query)]})
        last_msg = result["messages"][-1]
        print(f"Agent reply {i}: {last_msg.content}")
