import logging

logger = logging.getLogger(__name__)

_ENTRIES: list[dict] = []


class LedgerImbalanceError(RuntimeError):
    pass


def post_installment_plan(order_id: str, total: int, fee_rate: float, schedule: list[dict]) -> dict:
    receivable = sum(row["principal"] + row["fee"] for row in schedule)
    revenue = total
    fee_income = round(total * fee_rate)
    if receivable != revenue + fee_income:
        raise LedgerImbalanceError(
            f"order {order_id}: debit {receivable} != credit {revenue + fee_income}"
        )
    entry = {
        "order_id": order_id,
        "debit": {"receivable": receivable},
        "credit": {"revenue": revenue, "fee_income": fee_income},
    }
    _ENTRIES.append(entry)
    logger.info("ledger posted %s", entry)
    return entry
