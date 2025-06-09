"""
3 - Sequential Workflow Refund System for Crabby's Taffy
"""

import logging
from google.adk.agents import Agent, SequentialAgent
from tools.tools import get_purchase_history, check_refund_eligibility, process_refund
from tools.prompts import (
    top_level_prompt,
    purchase_history_subagent_prompt,
    check_eligibility_subagent_prompt,
    process_refund_subagent_prompt,
)

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"

purchase_verifier_agent = Agent(
    model=GEMINI_MODEL,
    name="PurchaseVerifierAgent",
    description="Verifies customer purchase history using the internal database",
    instruction=purchase_history_subagent_prompt,
    tools=[get_purchase_history],
    output_key="purchase_history",
)

refund_eligibility_agent = Agent(
    model=GEMINI_MODEL,
    name="RefundEligibilityAgent",
    description="Determines refund eligibility based on policies",
    instruction=check_eligibility_subagent_prompt,
    tools=[check_refund_eligibility],
    output_key="is_refund_eligible",
)

refund_processor_agent = Agent(
    model=GEMINI_MODEL,
    name="RefundProcessorAgent",
    description="Processes refunds or provides rejection explanations",
    instruction=top_level_prompt
    + "Specifically, your subagent has this task: "
    + process_refund_subagent_prompt,
    tools=[process_refund],
    output_key="refund_confirmation_message",
)

root_agent = SequentialAgent(
    name="SequentialRefundProcessor",
    description="Processes customer refunds in a fixed sequential workflow",
    sub_agents=[
        purchase_verifier_agent,
        refund_eligibility_agent,
        refund_processor_agent,
    ],
)
