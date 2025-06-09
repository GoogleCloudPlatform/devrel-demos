"""
4 - Parallel Workflow Refund System for Crabby's Taffy

This module implements a hybrid parallel-sequential workflow:
1. PARALLEL: Two agents run simultaneously to check:
   - PurchaseVerifierAgent: Retrieves purchase history
   - RefundEligibilityAgent: Checks if refund reason is valid
2. SEQUENTIAL: After both parallel checks complete:
   - RefundProcessorAgent: Processes refund if both conditions are met

This pattern optimizes performance by running independent checks in parallel,
then making a final decision based on both results.
"""

import logging
from google.adk.agents import Agent, ParallelAgent, SequentialAgent
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
        Success message with refund details and FINAL_RESPONSE marker
    """
    logger.info(f"Processing refund - Order: {order_id}, Amount: ${amount:.2f}")

    # In a real system, this would interact with payment processors
    refund_id = f"REF-{order_id}-{int(amount*100)}"
    result = (
        f"Refund of ${amount:.2f} for order {order_id} processed successfully! "
        f"Refund ID: {refund_id}. "
        f"The amount will be credited within 3-5 business days."
    )

    logger.info(f"Refund processed successfully - Refund ID: {refund_id}")

    # Return with FINAL_RESPONSE marker to indicate completion
    return f"FINAL_RESPONSE: {result}"


# --- Parallel Sub-Agents ---
# These two agents run simultaneously in the first phase

# 1. Purchase Verifier Agent
purchase_verifier_agent = Agent(
    model=GEMINI_MODEL,
    name="PurchaseVerifierAgent",
    description="Verifies customer purchase history using the internal database",
    instruction="""
    You are the Purchase Verifier Agent for Crabby's Taffy.
    Your sole task is to verify a customer's purchase history.
    
    Instructions:
    - Use `get_purchase_history` to retrieve the customer's orders
    - Return the complete purchase history data clearly
    - Include all details: order ID, date, items, shipping method, total amount
    - If no purchases found, return an empty list with a clear message
    
    Note: Focus only on retrieving and returning purchase data.
    The shipping method will be important for other agents.
    """,
    tools=[get_purchase_history],
    output_key="purchase_history",
)

# 2. Refund Eligibility Agent (runs in parallel with purchase verifier)
refund_eligibility_agent = Agent(
    model=GEMINI_MODEL,
    name="RefundEligibilityAgent",
    description="Checks if the refund reason is valid per company policy",
    instruction="""
    You are the Refund Eligibility Agent for Crabby's Taffy.
    Your task is to determine if the refund REASON is valid.
    
    Instructions:
    1. Convert the customer's refund reason to one of these codes:
       - DAMAGED: Package arrived damaged, melted, or opened
       - LOST: Package never arrived, stolen, or missing
       - LATE: Package arrived late
       - OTHER: Any other reason
    
    2. Use `check_refund_eligible` with ONLY the reason
       (Note: This parallel version doesn't check shipping method)
    
    3. Return exactly "TRUE" or "FALSE" based on the tool's response
    
    Valid reasons for refund: DAMAGED, LOST, or LATE only.
    Do not modify the tool's response.
    """,
    tools=[check_refund_eligible],
    output_key="is_refund_eligible",
)

# --- Sequential Phase Agent ---
# This agent runs after both parallel agents complete

# 3. Refund Processor Agent
refund_processor_agent = Agent(
    model=GEMINI_MODEL,
    name="RefundProcessorAgent",
    description="Makes final refund decision based on parallel check results",
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

# --- Workflow Configuration ---

# Phase 1: Parallel execution of independent checks
parallel_agent = ParallelAgent(
    name="ParallelEligibilityChecker",
    description="Runs purchase verification and reason validation simultaneously",
    sub_agents=[
        purchase_verifier_agent,
        refund_eligibility_agent,
    ],
)

# Phase 2: Sequential execution combining parallel results
root_agent = SequentialAgent(
    name="ParallelSequentialRefundProcessor",
    description="Processes refunds using parallel checks followed by final decision",
    sub_agents=[
        parallel_agent,  # First: Run both checks in parallel
        refund_processor_agent,  # Then: Make final decision
    ],
)

# Log initialization
logger.info("Initialized parallel-sequential refund workflow")
logger.info("Phase 1 (Parallel): Purchase verification + Reason validation")
logger.info("Phase 2 (Sequential): Final refund decision")
logger.info(f"Root agent: {root_agent.name}")
