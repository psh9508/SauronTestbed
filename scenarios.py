"""shop 앱의 버그를 재현하는 시나리오 모음. 각 함수는 예외를 일으켜야 한다."""
from collections.abc import Callable

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


SCENARIOS: dict[str, Callable[[], None]] = {
    "unknown_product": unknown_product,   # KeyError
    "zero_stock": zero_stock,             # ZeroDivisionError
    "string_price": string_price,         # TypeError (데이터 타입 문제가 쿠폰 계산에서 터짐)
    "invalid_coupon": invalid_coupon,     # TypeError (None subscript)
    "broken_coupon": broken_coupon,       # KeyError
    "missing_address": missing_address,   # TypeError (orders → users, 깊은 호출)
    "bad_quantity": bad_quantity,         # ValueError
    "missing_email": missing_email,       # AttributeError
}

# stacktrace 없는 message 이벤트
MESSAGE_SCENARIOS: dict[str, tuple[str, str]] = {
    "payment_timeout": (
        "PaymentGatewayTimeout",
        "Payment gateway did not respond within 30s while placing order for user 1 (shop/orders.py place_order)",
    ),
}
