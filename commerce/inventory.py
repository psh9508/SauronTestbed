import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Warehouse:
    code: str
    priority: int
    stock: dict[str, int] = field(default_factory=dict)
    active: bool = True


WAREHOUSES = [
    Warehouse("PUS", 2, {"K-1": 4, "C-1": 120, "H-1": 6}),
    Warehouse("ICN", 1, {"K-1": 20, "M-1": 35, "D-1": 8, "W-1": 10}),
    Warehouse("DJN", 3, {"D-1": 2, "H-1": 1}, active=False),
]


class OutOfStockError(RuntimeError):
    pass


@dataclass
class Reservation:
    sku: str
    qty: int
    warehouse: str


def _ordered() -> list[Warehouse]:
    return sorted(WAREHOUSES, key=lambda w: w.priority)


def reserve(items: list[tuple[str, int]]) -> list[Reservation]:
    candidates = (w for w in _ordered() if w.active)
    reservations: list[Reservation] = []
    for sku, qty in items:
        warehouse = next((w for w in candidates if w.stock.get(sku, 0) >= qty), None)
        if warehouse is None:
            raise OutOfStockError(f"{sku} x{qty}: no warehouse can fulfil the request")
        warehouse.stock[sku] -= qty
        reservations.append(Reservation(sku, qty, warehouse.code))
        logger.info("reserved %s x%d at %s", sku, qty, warehouse.code)
    return reservations
