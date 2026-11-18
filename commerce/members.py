MEMBERS = {
    7: {"name": "jiwoo", "tier": "gold", "email": "jiwoo@example.com"},
    11: {"name": "minseo", "tier": "vip", "email": "minseo@example.com"},
    15: {"name": "dohyun", "tier": "silver", "email": "dohyun@example.com"},
}


def member_tier(member_id: int) -> str:
    return MEMBERS[member_id]["tier"]
