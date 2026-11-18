import logging

logger = logging.getLogger(__name__)

USERS = {
    1: {"name": "alice", "email": "alice@example.com", "address": {"city": "Seoul", "zip": "04524"}},
    2: {"name": "bob", "email": None, "address": None},
}


def find_user(user_id: int) -> dict | None:
    logger.info("finding user %s", user_id)
    return USERS.get(user_id)


def shipping_label(user_id: int) -> str:
    user = find_user(user_id)
    return f"{user['name']} / {user['address']['city']} ({user['address']['zip']})"


def email_domain(user_id: int) -> str:
    user = find_user(user_id)
    return user["email"].split("@")[1]
