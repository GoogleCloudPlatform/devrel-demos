# Full runnable code for the CustomerRefundAgent example
import logging
from typing import AsyncGenerator, Dict, Any
from typing_extensions import override

from google.adk.agents import LlmAgent, BaseAgent, ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.events import Event
from pydantic import BaseModel, Field
from tools.tools import get_purchase_history, check_refund_eligibility, process_refund
from tools.prompts import (
    purchase_history_subagent_prompt,
    check_eligibility_subagent_prompt_parallel,
    process_refund_subagent_prompt,
)

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"


class CustomerRefundAgent(BaseAgent):
    # --- Field Declarations for Pydantic ---
    refund_eligibility_checker: LlmAgent
    get_purchase_history: LlmAgent
    process_full_refund: LlmAgent
    offer_store_credit: LlmAgent
    process_store_credit_response: LlmAgent
    parallel_agent: ParallelAgent

    # model_config allows setting Pydantic configurations if needed
    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        name: str,
        refund_eligibility_checker: LlmAgent,
        get_purchase_history: LlmAgent,
        process_full_refund: LlmAgent,
        offer_store_credit: LlmAgent,
        process_store_credit_response: LlmAgent,
    ):
        """
        Initializes the CustomerRefundAgent.

        Args:
            name: The name of the agent.
            refund_eligibility_checker: An LlmAgent to check refund eligibility.
            get_purchase_history: An LlmAgent to retrieve purchase history.
            process_full_refund: An LlmAgent to process a full refund, if eligible.
            offer_store_credit: An LlmAgent to offer store credit alternative, if not eligible for a full refund.
            process_store_credit_response: An LlmAgent to handle user's response to store credit offer.
        """
        parallel_agent = ParallelAgent(
            name="RefundChecks",
            sub_agents=[refund_eligibility_checker, get_purchase_history],
        )
        sub_agents_list = [
            parallel_agent,
            offer_store_credit,
            process_store_credit_response,
        ]
        super().__init__(
            name=name,
            refund_eligibility_checker=refund_eligibility_checker,
            get_purchase_history=get_purchase_history,
            process_full_refund=process_full_refund,
            offer_store_credit=offer_store_credit,
            process_store_credit_response=process_store_credit_response,
            parallel_agent=parallel_agent,
            sub_agents=sub_agents_list,
        )

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Implements the custom orchestration logic for the refund workflow.
        """
        logger.info(f"[{self.name}] Starting customer refund workflow.")

        # 1. Run parallel checks for eligibility and purchase history
        logger.info(f"[{self.name}] Running parallel refund checks...")
        async for event in self.parallel_agent.run_async(ctx):
            logger.info(
                f"[{self.name}] Event from RefundChecks: {event.model_dump_json(indent=2, exclude_none=True)}"
            )
            yield event

        # Get results from session state
        is_eligible_str = ctx.session.state.get("is_refund_eligible", "false")
        # Convert string to boolean
        is_eligible = (
            is_eligible_str.lower() == "true"
            if isinstance(is_eligible_str, str)
            else bool(is_eligible_str)
        )
        purchase_history = ctx.session.state.get("purchase_history", [])

        logger.info(f"[{self.name}] Refund eligible: {is_eligible}")
        logger.info(f"[{self.name}] Purchase history: {purchase_history}")

        # 2. Decision logic based on results
        final_message = ""

        if is_eligible and purchase_history:
            logger.info(f"[{self.name}] Customer eligible for full refund.")
            async for event in self.process_full_refund.run_async(ctx):
                logger.info(
                    f"[{self.name}] Event from ProcessFullRefund: {event.model_dump_json(indent=2, exclude_none=True)}"
                )
                yield event

            final_message = ctx.session.state.get("final_response", "")

        elif purchase_history and not is_eligible:
            logger.info(
                f"[{self.name}] Customer not eligible for refund. Offering store credit."
            )
            async for event in self.offer_store_credit.run_async(ctx):
                logger.info(
                    f"[{self.name}] Event from OfferStoreCredit: {event.model_dump_json(indent=2, exclude_none=True)}"
                )
                yield event

            # Process user's response to store credit offer
            async for event in self.process_store_credit_response.run_async(ctx):
                logger.info(
                    f"[{self.name}] Event from ProcessStoreCreditResponse: {event.model_dump_json(indent=2, exclude_none=True)}"
                )
                yield event

            final_message = ctx.session.state.get("final_response", "")

        else:
            # No purchase history found
            logger.info(f"[{self.name}] No purchase history found.")
            final_message = "I couldn't find any purchase history associated with your account. Please verify your order number and try again."
            ctx.session.state["final_response"] = final_message

        # 3. Create a final summary agent to output the result
        final_response_agent = LlmAgent(
            name="FinalResponseAgent",
            model=GEMINI_MODEL,
            instruction=f"""Output the following message exactly as provided: {final_message}""",
            input_schema=None,
            output_key="refund_decision",
        )

        # Yield events from the final response agent
        async for event in final_response_agent.run_async(ctx):
            logger.info(
                f"[{self.name}] Final response event: {event.model_dump_json(indent=2, exclude_none=True)}"
            )
            yield event

        logger.info(f"[{self.name}] Refund workflow completed. Exiting.")


get_purchase_history = LlmAgent(
    name="GetPurchaseHistory",
    model=GEMINI_MODEL,
    instruction=purchase_history_subagent_prompt,
    input_schema=None,
    output_key="purchase_history",
    tools=[get_purchase_history],
)


refund_eligibility_checker = LlmAgent(
    name="IsRefundEligible",
    model=GEMINI_MODEL,
    instruction=check_eligibility_subagent_prompt_parallel,
    input_schema=None,
    output_key="is_refund_eligible",
    tools=[check_refund_eligibility],
)

process_full_refund = LlmAgent(
    name="RefundProcessorAgent",
    model=GEMINI_MODEL,
    instruction=process_refund_subagent_prompt,
    tools=[process_refund],
    output_key="refund_confirmation_message",
)

offer_store_credit = LlmAgent(
    name="OfferStoreCredit",
    model=GEMINI_MODEL,
    instruction="""
    The customer is not eligible for a refund but has a valid purchase history. Politely explain this and offer them a 50% store credit for their next purchase as an alternative. Be empathetic and professional.
    Ask if they would like to accept this offer.
""",
    input_schema=None,
    output_key="store_credit_offer",
)

process_store_credit_response = LlmAgent(
    name="ProcessStoreCreditResponse",
    model=GEMINI_MODEL,
    instruction="""
        You are processing the customer's response to the store credit offer.
        Based on the customer's response in session state with key 'customer_response':
        - If they accept: Output "I'll send this to your account. Thanks!"
        - If they decline: Output "I apologize that we couldn't accommodate your request. Thank you for your understanding."
        Store the appropriate message based on their response.
""",
    input_schema=None,
    output_key="final_response",
)

customer_refund_agent = CustomerRefundAgent(
    name="CustomerRefundAgent",
    refund_eligibility_checker=refund_eligibility_checker,
    get_purchase_history=get_purchase_history,
    process_full_refund=process_full_refund,
    offer_store_credit=offer_store_credit,
    process_store_credit_response=process_store_credit_response,
)

root_agent = customer_refund_agent
