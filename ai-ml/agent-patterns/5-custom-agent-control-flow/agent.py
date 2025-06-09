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

logger = logging.getLogger(__name__)

GEMINI_2_FLASH = "gemini-2.5-flash-preview-05-20"


class CustomerRefundAgent(BaseAgent):
    """
    Custom agent for a customer refund workflow.

    This agent orchestrates a refund process by checking eligibility and purchase history
    in parallel, then determines the appropriate action based on the results.
    """

    # --- Field Declarations for Pydantic ---
    is_refund_eligible: LlmAgent
    get_purchase_history: LlmAgent
    offer_store_credit: LlmAgent
    process_store_credit_response: LlmAgent
    parallel_agent: ParallelAgent

    # model_config allows setting Pydantic configurations if needed
    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        name: str,
        is_refund_eligible: LlmAgent,
        get_purchase_history: LlmAgent,
        offer_store_credit: LlmAgent,
        process_store_credit_response: LlmAgent,
    ):
        """
        Initializes the CustomerRefundAgent.

        Args:
            name: The name of the agent.
            is_refund_eligible: An LlmAgent to check refund eligibility.
            get_purchase_history: An LlmAgent to retrieve purchase history.
            offer_store_credit: An LlmAgent to offer store credit alternative.
            process_store_credit_response: An LlmAgent to handle user's response to store credit offer.
        """
        # Create parallel agent for checking eligibility and history simultaneously
        parallel_agent = ParallelAgent(
            name="RefundChecks", sub_agents=[is_refund_eligible, get_purchase_history]
        )

        # Define the sub_agents list for the framework
        sub_agents_list = [
            parallel_agent,
            offer_store_credit,
            process_store_credit_response,
        ]

        # Pydantic will validate and assign them based on the class annotations
        super().__init__(
            name=name,
            is_refund_eligible=is_refund_eligible,
            get_purchase_history=get_purchase_history,
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
        is_eligible_str = ctx.session.state.get("refund_eligible", "false")
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
            # Full refund case
            logger.info(f"[{self.name}] Customer eligible for full refund.")
            final_message = "Great news! You are eligible for a full refund. The refund has been processed and will appear in your account within 3-5 business days."
            ctx.session.state["final_response"] = final_message

        elif purchase_history and not is_eligible:
            # Offer store credit alternative
            logger.info(
                f"[{self.name}] Customer not eligible for refund. Offering store credit."
            )

            # Offer store credit
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

            # Get the final response from the store credit processing
            final_message = ctx.session.state.get("final_response", "")

        else:
            # No purchase history found
            logger.info(f"[{self.name}] No purchase history found.")
            final_message = "I couldn't find any purchase history associated with your account. Please verify your order number and try again."
            ctx.session.state["final_response"] = final_message

        # 3. Create a final summary agent to output the result
        final_response_agent = LlmAgent(
            name="FinalResponseAgent",
            model=GEMINI_2_FLASH,
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


def get_purchase_history(purchaser: str) -> list:
    history_data = {
        "Alexis": [
            {
                "purchase_id": "JD001-20250415",
                "purchased_date": "2025-04-15",
                "items": [
                    {
                        "product_name": "Assorted Taffy 1lb Box",
                        "quantity": 1,
                        "price": 15.00,
                    },
                    {
                        "product_name": "Watermelon Taffy 0.5lb Bag",
                        "quantity": 1,
                        "price": 8.00,
                    },
                ],
                "shipping_method": "STANDARD",
                "total_amount": 23.00,
            }
        ],
        "David": [
            {
                "purchase_id": "SG001-20250501",
                "purchased_date": "2025-05-01",
                "items": [
                    {
                        "product_name": "Assorted Taffy 1lb Box",
                        "quantity": 2,
                        "price": 15.00,
                    }
                ],
                "shipping_method": "INSURED",
                "total_amount": 30.00,
            },
        ],
    }
    purchaser = purchaser.strip().capitalize()
    if purchaser not in history_data:
        return []
    return history_data[purchaser]


get_purchase_history = LlmAgent(
    name="GetPurchaseHistory",
    model=GEMINI_2_FLASH,
    instruction="""  You are the Purchase Verifier Agent for Crabby's Taffy.
      Your sole task is to verify a customer's purchase history given their name.
      Use the `get_purchase_history` to retrieve the relevant information.
      Return the purchase history data clearly and concisely.""",
    input_schema=None,
    output_key="purchase_history",
    tools=[get_purchase_history],
)


def check_refund_eligible(reason: str) -> str:
    eligible_reasons = ["DAMAGED", "LOST", "LATE"]
    reason = reason.strip().upper()
    print("⭐ Reason: ", reason)
    if reason in eligible_reasons:
        print("✅ Eligible for Refund, returning TRUE")
        return "TRUE"
    print("❌ Not Eligible for Refund, returning FALSE")
    return "FALSE"


is_refund_eligible = LlmAgent(
    name="IsRefundEligible",
    model=GEMINI_2_FLASH,
    instruction="""     
    You are the Refund Policy Applier Agent for Crabby's Taffy.
      Your task is to determine if a refund request is eligible based on the provided reason and shipping method.
      Use the `check_refund_eligibile` to make this determination.
      Based on the user's natural-language reason for refund, transform that into a reason that the check_refund_eligible tool understands, must be one of: 
      - DAMAGED - packaged arrived, but melted or with the box open etc 
      - LATE 
      - LOST - package never arrived, or was stolen, or missing in transit  
      - OTHER - any other reason
      
      Call the check_refund_eligible tool to determine if the refund is eligible. You will get a True or False result back from the tool. Do not modify the tool's response. Simply response TRUE or FALSE.""",
    input_schema=None,
    output_key="refund_eligible",
    tools=[check_refund_eligible],
)


offer_store_credit = LlmAgent(
    name="OfferStoreCredit",
    model=GEMINI_2_FLASH,
    instruction="""You are a customer service representative. The customer is not eligible 
for a refund but has a valid purchase history. Politely explain this and offer them a 
50% store credit for their next purchase as an alternative. Be empathetic and professional.
Ask if they would like to accept this offer.""",
    input_schema=None,
    output_key="store_credit_offer",
)

process_store_credit_response = LlmAgent(
    name="ProcessStoreCreditResponse",
    model=GEMINI_2_FLASH,
    instruction="""You are processing the customer's response to the store credit offer.
Based on the customer's response in session state with key 'customer_response':
- If they accept: Output "I'll send this to your account. Thanks!"
- If they decline: Output "I apologize that we couldn't accommodate your request. Thank you for your understanding."
Store the appropriate message based on their response.""",
    input_schema=None,
    output_key="final_response",
)

# --- Create the custom agent instance ---
customer_refund_agent = CustomerRefundAgent(
    name="CustomerRefundAgent",
    is_refund_eligible=is_refund_eligible,
    get_purchase_history=get_purchase_history,
    offer_store_credit=offer_store_credit,
    process_store_credit_response=process_store_credit_response,
)

root_agent = customer_refund_agent
