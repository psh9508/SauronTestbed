import logging

logger = logging.getLogger(__name__)

USERS = {
    1: {"name": "alice", "email": "alice@example.com", "address": {"city": "Seoul", "zip": "04524"}},
    2: {"name": "bob", "email": None, "address": None},  # BUG: 주소/이메일 미등록 유저
}


def find_user(user_id: int) -> dict | None:
    logger.info("finding user %s", user_id)
    return USERS.get(user_id)


def shipping_label(user_id: int) -> str:
    user = find_user(user_id)
    # BUG: address가 None인 유저 → TypeError: 'NoneType' object is not subscriptable
    return f"{user['name']} / {user['address']['city']} ({user['address']['zip']})"


def email_domain(user_id: int) -> str:
    user = find_user(user_id)
    # BUG: email이 None이면 AttributeError
    return user["email"].split("@")[1]
