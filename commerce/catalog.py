import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

_PRODUCTS = {
    "K-1": {"name": "Mechanical Keyboard", "price": 120000, "category": "input"},
    "M-1": {"name": "Wireless Mouse", "price": 45000, "category": "input"},
    "D-1": {"name": "27in Display", "price": 380000, "category": "display"},
    "C-1": {"name": "USB-C Cable", "price": 15000, "category": "accessory"},
    "H-1": {"name": "Headset", "price": 98000, "category": "audio"},
    "W-1": {"name": "Webcam", "price": 72000, "category": "video"},
}

BUNDLES = {
    "B-DESK": ["K-1", "M-1", "B-CABLES"],
    "B-CABLES": ["C-1", "C-1"],
    "B-STREAM": ["H-1", "W-1", "B-CREATOR"],
    "B-CREATOR": ["D-1", "B-STUDIO"],
    "B-STUDIO": ["M-1", "B-STREAM"],
}


class UnknownProductError(LookupError):
    pass


@lru_cache(maxsize=256)
def load_product(sku: str) -> dict:
    logger.info("loading product %s", sku)
    if sku not in _PRODUCTS:
        raise UnknownProductError(sku)
    return {"sku": sku, **_PRODUCTS[sku]}


def is_bundle(sku: str) -> bool:
    return sku in BUNDLES


def bundle_components(sku: str) -> list[str]:
    components: list[str] = []
    for child in BUNDLES[sku]:
        if is_bundle(child):
            components.extend(bundle_components(child))
        else:
            components.append(child)
    return components
