import logging

logger = logging.getLogger(__name__)

PRODUCTS = {
    "P-100": {"name": "Keyboard", "price": 89000, "stock": 12},
    "P-200": {"name": "Mouse", "price": 39000, "stock": 0},
    "P-300": {"name": "Monitor", "price": "329000", "stock": 3},
}


def get_product(product_id: str) -> dict:
    logger.info("looking up product %s", product_id)
    return PRODUCTS[product_id]


def stock_ratio(product_id: str, requested: int) -> float:
    product = get_product(product_id)
    return requested / product["stock"]
