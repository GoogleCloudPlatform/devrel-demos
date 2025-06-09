"""
3 - Sequential Workflow Refund System for Crabby's Taffy

This module implements a sequential agent system where sub-agents execute
in a fixed order, passing data between stages:
1. PurchaseVerifierAgent: Retrieves purchase history
2. RefundEligibilityAgent: Checks if refund is allowed based on policies
3. RefundProcessorAgent: Processes approved refunds or explains rejection

The SequentialAgent framework handles the orchestration automatically,
executing each agent in order and passing outputs via template variables.
"""

import logging
from google.adk.agents import Agent, SequentialAgent
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


# --- Sequential Sub-Agents ---
# Note: These agents pass data through output_key variables

# 1. Purchase Verifier Agent
purchase_verifier_agent = Agent(
    model=GEMINI_MODEL,
    name="PurchaseVerifierAgent",
    description="Verifies customer purchase history using the internal database",
    instruction="""
    You are the Purchase Verifier Agent for Crabby's Taffy.
    Your task is to verify a customer's purchase history.
    
    Instructions:
    - Use `get_purchase_history` to retrieve the customer's orders
    - Return the complete purchase history data
    - Include all order details, especially the shipping method
    - If no purchases found, return an empty list with a clear message
    
    Important: The shipping method is crucial for the next agent to determine eligibility.
    Format the response clearly so the next agent can easily extract the shipping method.
    """,
    tools=[get_purchase_history],
    output_key="purchase_history",  # This will be available to next agent
)

# 2. Refund Eligibility Agent
refund_eligibility_agent = Agent(
    model=GEMINI_MODEL,
    name="RefundEligibilityAgent",
    description="Determines refund eligibility based on policies",
    instruction="""
    You are the Refund Eligibility Agent for Crabby's Taffy.
    You determine if a refund request is eligible based on reason and shipping method.
    
    Purchase History: {purchase_history}
    
    Instructions:
    1. Extract the shipping method from the purchase history above
    2. Convert the customer's refund reason to one of these codes:
       - DAMAGED: Package arrived damaged, melted, or opened
       - LOST: Package never arrived, stolen, or missing in transit
       - LATE: Package arrived late
       - OTHER: Any other reason
    
    3. Use `check_refund_eligible` with the reason code and shipping method
    4. Return ONLY "TRUE" or "FALSE" based on the tool's response
    
    Policy reminder: Only INSURED shipments with valid reasons qualify for refunds.
    Do not modify or interpret the tool's response - pass it through exactly.
    """,
    tools=[check_refund_eligible],
    output_key="is_refund_eligible",  # This will be available to next agent
)

# 3. Refund Processor Agent
refund_processor_agent = Agent(
    model=GEMINI_MODEL,
    name="RefundProcessorAgent",
    description="Processes refunds or provides rejection explanations",
    instruction="""
    You are the Refund Processor Agent for Crabby's Taffy.
    You handle the final step of the refund process.
    
    Purchase History: {purchase_history}
    Eligibility Status: {is_refund_eligible}
    
    Instructions:
    
    If eligible (is_refund_eligible = TRUE):
    1. Extract the order ID and total amount from the purchase history
    2. Use `process_refund` to complete the refund
    3. Provide a friendly confirmation with:
       - Refund ID
       - Amount refunded
       - Expected timeline (3-5 business days)
       - Thank the customer
    
    If NOT eligible (is_refund_eligible = FALSE):
    1. Politely explain why the refund cannot be processed
    2. Mention that only INSURED shipments with valid reasons qualify
    3. Suggest contacting customer support for special cases
    4. Thank them for their understanding
    
    Always be empathetic and professional. Never hand off to a human - 
    make a definitive decision based on the eligibility status.
    """,
    tools=[process_refund],
    output_key="refund_confirmation_message",
)

# --- Sequential Orchestrator ---
# This automatically executes agents in order, passing data between them
root_agent = SequentialAgent(
    name="SequentialRefundProcessor",
    description="Processes customer refunds in a fixed sequential workflow",
    sub_agents=[
        purchase_verifier_agent,
        refund_eligibility_agent,
        refund_processor_agent,
    ],
)

# Log initialization
logger.info("Initialized sequential refund workflow")
logger.info(f"Sequential processor: {root_agent.name}")
logger.info(f"Execution order: {[agent.name for agent in root_agent.sub_agents]}")
logger.info(
    "Data flow: purchase_history -> is_refund_eligible -> refund_confirmation_message"
)
