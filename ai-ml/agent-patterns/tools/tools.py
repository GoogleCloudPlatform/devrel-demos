import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Constants
ELIGIBLE_SHIPPING_METHODS = ["INSURED"]
ELIGIBLE_REASONS = ["DAMAGED", "NEVER_ARRIVED"]


def get_purchase_history(purchaser: str) -> List[Dict[str, Any]]:
    """
    Retrieve purchase history for a given customer.

    Args:
        purchaser: Customer name

    Returns:
        List of purchase records containing order details
    """
    # Mock database of purchase history
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
                "purchase_id": "SG002-20250610",
                "purchased_date": "2025-06-03",
                "items": [
                    {
                        "product_name": "Peanut Butter Taffy 0.5lb Bag",
                        "quantity": 1,
                        "price": 8.00,
                    },
                    {
                        "product_name": "Sour Apple Taffy 0.5lb Bag",
                        "quantity": 1,
                        "price": 8.00,
                    },
                ],
                "shipping_method": "INSURED",
                "total_amount": 16.00,
            },
        ],
    }

    # Normalize purchaser name
    purchaser = purchaser.strip().title()

    logger.info(f"Retrieving purchase history for: {purchaser}")

    if purchaser not in history_data:
        logger.warning(f"No purchase history found for: {purchaser}")
        return []

    history = history_data[purchaser]
    logger.info(f"Found {len(history)} purchase(s) for {purchaser}")
    return history


def check_refund_eligible(reason: str, shipping_method: str) -> bool:
    """
    Check if a refund request is eligible based on reason and shipping method.

    Args:
        reason: Refund reason
        shipping_method: Shipping method used for the order

    Returns:
        True if refund is eligible, False otherwise
    """
    reason_upper = reason.strip().upper()
    shipping_upper = shipping_method.strip().upper()

    logger.info(
        f"Checking refund eligibility - Reason: {reason_upper}, Shipping: {shipping_upper}"
    )

    # Check eligibility based on shipping method and reason
    is_eligible = (
        shipping_upper in ELIGIBLE_SHIPPING_METHODS and reason_upper in ELIGIBLE_REASONS
    )

    logger.info(f"Refund eligibility result: {is_eligible}")
    return is_eligible
