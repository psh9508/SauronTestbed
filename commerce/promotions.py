import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)

TIERS = [
    {"name": "silver", "min_spend": 0, "rate": 3},
    {"name": "gold", "min_spend": 300000, "rate": 7},
    {"name": "vip", "min_spend": 1000000, "rate": 12},
]

TIER_CAPS = {tier["name"]: tier["rate"] for tier in TIERS}


def _build_rules() -> dict[str, Callable[[int], int]]:
    rules: dict[str, Callable[[int], int]] = {}
    for tier in TIERS:
        rules[tier["name"]] = lambda subtotal: tier["rate"] if subtotal >= tier["min_spend"] else 0
    return rules


_RULES = _build_rules()


def discount_rate_for(subtotal: int, tier: str | None) -> int:
    if tier is None:
        return 0
    rate = _RULES[tier](subtotal)
    logger.info("discount for tier=%s subtotal=%s -> %s%%", tier, subtotal, rate)
    return rate
