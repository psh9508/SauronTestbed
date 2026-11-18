import logging

from commerce.catalog import bundle_components, load_product
from commerce.promotions import discount_rate_for

logger = logging.getLogger(__name__)


def price_line(sku: str, qty: int, tier: str | None = None) -> dict:
    product = load_product(sku)
    rate = discount_rate_for(product["price"] * qty, tier)
    if rate:
        product["price"] = product["price"] * (100 - rate) // 100
    return {
        "sku": sku,
        "qty": qty,
        "unit_price": product["price"],
        "discount_rate": rate,
        "amount": product["price"] * qty,
    }


def bundle_price(sku: str, tier: str | None = None) -> int:
    skus = bundle_components(sku)
    logger.info("bundle %s -> %s", sku, skus)
    return sum(price_line(s, 1, tier)["amount"] for s in skus)
