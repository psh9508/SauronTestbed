"""shop 앱 사용 흐름 모음."""
from collections.abc import Callable

from commerce.checkout import checkout, quote
from commerce.notifications import notify_restock
from commerce.payments import create_installment_plan
from commerce.pricing import bundle_price
from shop.catalog import get_product, stock_ratio
from shop.orders import place_order
from shop.pricing import line_total
from shop.users import email_domain


def unknown_product() -> None:
    get_product("P-999")


def zero_stock() -> None:
    stock_ratio("P-200", 1)


def string_price() -> None:
    line_total("P-300", 2, "WELCOME10")


def invalid_coupon() -> None:
    line_total("P-100", 1, "NOPE")


def broken_coupon() -> None:
    line_total("P-100", 1, "BROKEN")


def missing_address() -> None:
    place_order(2, [{"product_id": "P-100", "quantity": 1}])


def bad_quantity() -> None:
    place_order(1, [{"product_id": "P-100", "quantity": "two"}])


def missing_email() -> None:
    email_domain(2)


def preview_then_checkout() -> None:
    cart = [("D-1", 3)]
    accepted = quote(11, cart)
    checkout(11, cart, accepted_quote=accepted)


def team_keyboard_order() -> None:
    checkout(7, [("K-1", 9)])


def desk_setup_order() -> None:
    checkout(15, [("K-1", 1), ("M-1", 2)])


def installment_checkout() -> None:
    create_installment_plan("ORD-7f3a91c2", 729000, 12)


def restock_broadcast() -> None:
    for sku in ("H-1", "W-1"):
        notify_restock(sku)


def streaming_bundle_price() -> None:
    bundle_price("B-STREAM", "vip")


SCENARIOS: dict[str, Callable[[], None]] = {
    "unknown_product": unknown_product,
    "zero_stock": zero_stock,
    "string_price": string_price,
    "invalid_coupon": invalid_coupon,
    "broken_coupon": broken_coupon,
    "missing_address": missing_address,
    "bad_quantity": bad_quantity,
    "missing_email": missing_email,
    "preview_then_checkout": preview_then_checkout,
    "team_keyboard_order": team_keyboard_order,
    "desk_setup_order": desk_setup_order,
    "installment_checkout": installment_checkout,
    "restock_broadcast": restock_broadcast,
    "streaming_bundle_price": streaming_bundle_price,
}


MESSAGE_SCENARIOS: dict[str, str] = {
    "payment_timeout": (
        "PaymentGatewayTimeout: Payment gateway did not respond within 30s "
        "while placing order for user 1 (shop/orders.py place_order)"
    ),
}
