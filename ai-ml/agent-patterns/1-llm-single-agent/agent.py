"""
1 - Single Agent Refund System for Crabby's Taffy

This module implements a single agent that handles the entire refund workflow:
- Retrieves purchase history
- Checks refund eligibility
- Processes approved refunds

The agent uses shared tools from the tools module and adds its own
process_refund function for completing the refund transaction.
"""

import logging
from typing import List, Dict, Any, Optional
from google.adk import Agent
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
    # For now, we'll simulate a successful refund
    refund_id = f"REF-{order_id}-{int(amount*100)}"
    logger.info(f"Refund processed successfully - Refund ID: {refund_id}")

    return (
        f"Refund processed successfully! "
        f"Refund ID: {refund_id}. "
        f"Amount: ${amount:.2f} will be credited within 3-5 business days."
    )


# Create the refund agent
root_agent = Agent(
    model=GEMINI_MODEL,
    name="CrabbysRefundAgent",
    description="Customer refund agent for Crabby's Taffy company",
    instruction="""
    You are a friendly and helpful customer refund agent for Crabby's Taffy company.
    Your role is to process refund requests efficiently while maintaining excellent customer service.
    
    ## Your Workflow:
    1. **Verify Purchase**: Use `get_purchase_history` to retrieve the customer's purchases
       - If multiple purchases exist, ask which specific order they want to refund
       - Note the shipping method for the selected order
    
    2. **Check Eligibility**: Use `check_refund_eligible` to verify if the refund is allowed
       - Pass the refund reason and the order's shipping method
       - Eligible combinations: (DAMAGED or NEVER_ARRIVED) + INSURED shipping
    
    3. **Process Decision**:
       - If eligible: Use `process_refund` to complete the refund
       - If not eligible: Politely explain why and offer alternatives
    
    ## Communication Guidelines:
    - Always be empathetic and professional
    - Thank customers for their business
    - Clearly explain refund decisions
    - For approved refunds: Provide order ID, refund amount, and timeline
    - For declined refunds: Explain the reason and suggest contacting customer support
    
    ## Important Notes:
    - Always verify the exact order before processing
    - The shipping method from the order is crucial for eligibility
    - Be understanding of unusual situations
    - Remember: Only INSURED shipments are eligible for automatic refunds
    """,
    tools=[get_purchase_history, check_refund_eligible, process_refund],
)

# Log agent initialization
logger.info(f"Initialized {root_agent.name} agent for refund processing")
