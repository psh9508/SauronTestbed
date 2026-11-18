import logging

from commerce.ledger import post_installment_plan

logger = logging.getLogger(__name__)

FEE_RATES = {1: 0.0, 3: 0.0, 6: 0.0275, 10: 0.0325, 12: 0.0375}


def split_principal(total: int, months: int) -> list[int]:
    base, remainder = divmod(total, months)
    return [base + (1 if i < remainder else 0) for i in range(months)]


def build_schedule(total: int, months: int) -> list[dict]:
    rate = FEE_RATES[months]
    return [
        {"seq": i + 1, "principal": principal, "fee": round(principal * rate)}
        for i, principal in enumerate(split_principal(total, months))
    ]


def create_installment_plan(order_id: str, total: int, months: int) -> dict:
    if months not in FEE_RATES:
        raise ValueError(f"unsupported installment months: {months}")
    schedule = build_schedule(total, months)
    logger.info("installment plan order=%s total=%s months=%s", order_id, total, months)
    entry = post_installment_plan(order_id, total, FEE_RATES[months], schedule)
    return {"order_id": order_id, "schedule": schedule, "ledger_entry": entry}
