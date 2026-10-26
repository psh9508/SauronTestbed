import logging

from shop.catalog import get_product
from shop.pricing import line_total
from shop.users import shipping_label

logger = logging.getLogger(__name__)


def place_order(user_id: int, items: list[dict], coupon_code: str | None = None) -> dict:
    logger.info("placing order user=%s items=%s coupon=%s", user_id, items, coupon_code)
    total = 0
    for item in items:
        # BUG: quantity를 검증 없이 int()로 변환 → "two" 같은 값이면 ValueError
        quantity = int(item["quantity"])
        product = get_product(item["product_id"])
        if product["stock"] < quantity:
            raise RuntimeError(f"out of stock: {item['product_id']}")
        total += line_total(item["product_id"], quantity, coupon_code)

    label = shipping_label(user_id)
    logger.info("order placed total=%s label=%s", total, label)
    return {"user_id": user_id, "total": total, "label": label}
