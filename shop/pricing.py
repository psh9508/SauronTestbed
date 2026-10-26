import logging

from shop.catalog import get_product

logger = logging.getLogger(__name__)

COUPONS = {
    "WELCOME10": {"type": "rate", "value": 10},
    "FLAT5000": {"type": "amount", "value": 5000},
    "BROKEN": {"type": "rate"},  # BUG: value 누락
}


def apply_coupon(price: int, coupon_code: str | None) -> int:
    if coupon_code is None:
        return price
    coupon = COUPONS.get(coupon_code)
    logger.info("applying coupon %s -> %s", coupon_code, coupon)
    # BUG: 존재하지 않는 쿠폰이면 coupon이 None → TypeError
    if coupon["type"] == "rate":
        return price - price * coupon["value"] // 100
    return price - coupon["value"]


def line_total(product_id: str, quantity: int, coupon_code: str | None = None) -> int:
    product = get_product(product_id)
    # BUG: price가 문자열인 상품이면 문자열 반복이 되고, 이후 쿠폰 계산에서 TypeError
    subtotal = product["price"] * quantity
    logger.info("subtotal for %s x%d = %r", product_id, quantity, subtotal)
    return apply_coupon(subtotal, coupon_code)
