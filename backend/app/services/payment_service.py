"""Payment processing (business logic).

Contains a deterministic stub suitable for development and UAT. Swap the
internals for Stripe/Razorpay/Paytm calls in production without changing
controller code.
"""

from dataclasses import dataclass
from typing import Optional

from app.models.order import PaymentMethod, PaymentStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PaymentResult:
    payment_status: PaymentStatus
    reference_id: str
    message: str


def _generate_reference(method: PaymentMethod) -> str:
    import uuid

    return f"{method.value.upper()}-{uuid.uuid4().hex[:12].upper()}"


def initiate_payment(
    method: PaymentMethod,
    amount: float,
    *,
    user_id: Optional[int] = None,
) -> PaymentResult:
    """Authorize a payment for an order.

    Cash on delivery is always pending; digital methods are auto-approved
    in this stub environment.
    """
    if method == PaymentMethod.cod:
        status = PaymentStatus.pending
        message = "Payment will be collected on delivery"
    else:
        status = PaymentStatus.paid
        message = "Payment authorized"

    reference = _generate_reference(method)
    if user_id:
        logger.info("Payment %s initiated for user %s: %s", reference, user_id, message)

    return PaymentResult(
        payment_status=status,
        reference_id=reference,
        message=message,
    )


def settle_cod(order_id: str, amount: float) -> PaymentResult:
    """Mark a cash-on-delivery payment as collected once the order is delivered."""
    logger.info("COD collected for order %s (amount=%.2f)", order_id, amount)
    return PaymentResult(
        payment_status=PaymentStatus.paid,
        reference_id=f"COD-COL-{order_id[:12].upper()}",
        message="Cash collected on delivery",
    )


def refund(order_id: str, amount: float, *, reference_id: str) -> bool:
    """Issue a refund for a cancelled/failed order. Stub: always succeeds."""
    logger.info("Refund %s for order %s (amount=%.2f)", reference_id, order_id, amount)
    return True