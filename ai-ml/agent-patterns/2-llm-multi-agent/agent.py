"""
2 - Multi-Agent Refund System

This module implements a multi-agent system where specialized sub-agents handle
different aspects of the refund process:
- PurchaseVerifierAgent: Retrieves and verifies purchase history
- RefundPolicyApplierAgent: Checks refund eligibility based on policies
- RefundProcessorAgent: Processes approved refunds
- CoordinatorAgent: Orchestrates the sub-agents to complete the workflow
"""

import logging
from google.adk.agents import Agent
from tools.tools import get_purchase_history, check_refund_eligible

# Configure logging for this module
logger = logging.getLogger(__name__)

# Constants
GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"


def process_refund(amount: float, order_id: str) -> str:
    """
    Process a refund for the given amount and order.

    Args:
        amount: Refund amount in dollars
        order_id: Order ID to refund

    Returns:
        Success message with refund details
    """
    logger.info(f"Processing refund - Order: {order_id}, Amount: ${amount:.2f}")

    # In a real system, this would interact with payment processors
    refund_id = f"REF-{order_id}-{int(amount*100)}"
    logger.info(f"Refund processed successfully - Refund ID: {refund_id}")

    return (
        f"Refund processed successfully! "
        f"Refund ID: {refund_id}. "
        f"Amount: ${amount:.2f} will be credited within 3-5 business days."
    )


# --- Sub-Agents ---

# 1. Purchase Verifier Agent
purchase_verifier_agent = Agent(
    model=GEMINI_MODEL,
    name="PurchaseVerifierAgent",
    description="Verifies customer purchase history using the internal database",
    instruction="""
    You are the Purchase Verifier Agent for Crabby's Taffy.
    Your sole task is to verify a customer's purchase history given their name.
    
    Instructions:
    - Use `get_purchase_history` to retrieve the customer's orders
    - Return the purchase history data clearly formatted
    - If no purchases found, clearly state this
    - Include all relevant details: order ID, date, items, shipping method, total
    
    Remember: The shipping method is crucial for refund eligibility checks.
    """,
    tools=[get_purchase_history],
)

# 2. Refund Policy Applier Agent
refund_policy_applier_agent = Agent(
    model=GEMINI_MODEL,
    name="RefundPolicyApplierAgent",
    description="Applies Crabby's Taffy refund policies to determine eligibility",
    instruction="""
    You are the Refund Policy Applier Agent for Crabby's Taffy.
    Your task is to determine if a refund request is eligible based on reason and shipping method.
    
    Instructions:
    - Use `check_refund_eligible` with the provided reason and shipping method
    - Valid refund reasons: DAMAGED, NEVER_ARRIVED
    - Eligible shipping methods: INSURED
    - Return "Eligible" or "Not Eligible" with a clear explanation
    
    Policy: Only INSURED shipments with DAMAGED or NEVER_ARRIVED reasons qualify for automatic refunds.
    """,
    tools=[check_refund_eligible],
)

# 3. Refund Processor Agent
refund_processor_agent = Agent(
    model=GEMINI_MODEL,
    name="RefundProcessorAgent",
    description="Processes customer refunds through the payment system",
    instruction="""
    You are the Refund Processor Agent for Crabby's Taffy.
    Your task is to initiate and confirm refunds for approved requests.
    
    Instructions:
    - Use `process_refund` with the exact amount and order ID
    - Return the complete confirmation message including refund ID
    - Ensure all details are accurate before processing
    
    Note: Only process refunds that have been approved by the RefundPolicyApplierAgent.
    """,
    tools=[process_refund],
)

# --- Coordinator (Parent) Agent ---
root_agent = Agent(
    name="RefundCoordinator",
    model=GEMINI_MODEL,
    description="Coordinates the refund process using specialized sub-agents",
    instruction="""
    You are the Refund Coordinator for Crabby's Taffy company.
    You orchestrate the refund process by delegating tasks to specialized sub-agents.
    
    ## Available Sub-Agents:
    1. **PurchaseVerifierAgent**: Retrieves customer purchase history
    2. **RefundPolicyApplierAgent**: Checks if refund request is eligible
    3. **RefundProcessorAgent**: Processes approved refunds
    
    ## Workflow:
    1. **Verify Purchase**: Use PurchaseVerifierAgent to get customer's orders
       - If multiple orders exist, ask customer to specify which one
       - Note the shipping method - it's crucial for eligibility
    
    2. **Check Eligibility**: Use RefundPolicyApplierAgent with:
       - The customer's refund reason
       - The shipping method from the selected order
    
    3. **Process Decision**:
       - If eligible: Use RefundProcessorAgent to complete the refund
       - If not eligible: Politely explain why and suggest alternatives
    
    ## Important Guidelines:
    - NEVER ask customers for shipping method - get it from purchase history
    - Only prompt users when you need clarification or for final responses
    - Execute sub-agent calls as intermediate steps without user interaction
    - Be empathetic and professional in all communications
    - Thank customers regardless of the outcome
    
    ## Customer Inputs:
    - Name
    - Refund reason (convert to: DAMAGED, NEVER_ARRIVED, or OTHER)
    - Order selection (if multiple orders exist)
    
    Remember: Coordinate efficiently between agents to provide quick, accurate service.
    """,
    sub_agents=[
        purchase_verifier_agent,
        refund_policy_applier_agent,
        refund_processor_agent,
    ],
)

# Log initialization
logger.info("Initialized multi-agent refund system")
logger.info(f"Coordinator: {root_agent.name}")
logger.info(f"Sub-agents: {[agent.name for agent in root_agent.sub_agents]}")
