import logging
import uuid

from commerce.inventory import reserve
from commerce.members import member_tier
from commerce.pricing import price_line
from commerce.promotions import TIER_CAPS

logger = logging.getLogger(__name__)


class CheckoutError(Exception):
    pass


class QuoteMismatchError(CheckoutError):
    pass


class PromotionPolicyError(CheckoutError):
    pass


def quote(member_id: int, cart: list[tuple[str, int]]) -> dict:
    tier = member_tier(member_id)
    lines = [price_line(sku, qty, tier) for sku, qty in cart]
    total = sum(line["amount"] for line in lines)
    logger.info("quote member=%s tier=%s total=%s", member_id, tier, total)
    return {"member_id": member_id, "tier": tier, "lines": lines, "total": total}


def checkout(member_id: int, cart: list[tuple[str, int]], accepted_quote: dict | None = None) -> dict:
    current = quote(member_id, cart)
    cap = TIER_CAPS[current["tier"]]
    for line in current["lines"]:
        if line["discount_rate"] > cap:
            raise PromotionPolicyError(
                f"{line['sku']}: discount {line['discount_rate']}% exceeds {current['tier']} cap {cap}%"
            )

    if accepted_quote is not None and accepted_quote["total"] != current["total"]:
        raise QuoteMismatchError(
            f"quoted total {accepted_quote['total']} but checkout total is {current['total']}"
        )

    reservations = reserve(cart)
    order_id = f"ORD-{uuid.uuid4().hex[:8]}"
    logger.info("order %s placed total=%s", order_id, current["total"])
    return {"order_id": order_id, "total": current["total"], "reservations": reservations}
