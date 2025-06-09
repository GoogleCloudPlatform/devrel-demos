"""
2 - Multi LLM Agent Refund System for Crabby's Taffy (Coordinator/Dispatcher pattern)

https://google.github.io/adk-docs/agents/multi-agents/#coordinatordispatcher-pattern
"""

import logging
from google.adk.agents import Agent
from tools.tools import get_purchase_history, check_refund_eligibility,, process_refund
from tools.prompts import (
    top_level_prompt,
    purchase_history_subagent_prompt,
    check_eligibility_subagent_prompt,
    process_refund_subagent_prompt,
)

# Configure logging for this module
logger = logging.getLogger(__name__)

# Constants
GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"

purchase_history_agent = Agent(
    model=GEMINI_MODEL,
    name="PurchaseHistoryAgent",
    description="Retrieves and verifies purchase history",
    instruction=purchase_history_subagent_prompt,
    tools=[get_purchase_history],
    output_key="purchase_history",
)

eligibility_agent = Agent(
    model=GEMINI_MODEL,
    name="EligibilityAgent",
    description="Checks refund eligibility based on policies",
    instruction=check_eligibility_subagent_prompt,
    tools=[check_refund_eligibility,],
    output_key="is_refund_eligible",
)

process_refund_agent = Agent(
    model=GEMINI_MODEL,
    name="ProcessRefundAgent",
    description="Processes approved refunds",
    instruction=process_refund_subagent_prompt,
    tools=[process_refund],
)

root_agent = Agent(
    model=GEMINI_MODEL,
    name="RefundMultiAgent",
    description="Customer refund multi LLM agent for Crabby's Taffy company",
    instruction="""
    You are a multi agent system that coordinates sub-agents. Execute the following instructions in as few "turns" as you can, only prompting the user when needed. Coordinate the sub agents behind the scenes...
    """
    + top_level_prompt,
    sub_agents=[purchase_history_agent, eligibility_agent, process_refund_agent],
)
