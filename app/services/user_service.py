from typing import Dict, List, Optional


_users_store: List[Dict[str, object]] = []
_next_user_id: int = 1


def list_users() -> List[Dict[str, object]]:
    """Return all users from the in-memory store."""
    return _users_store


def get_user_by_id(user_id: int) -> Optional[Dict[str, object]]:
    for user in _users_store:
        if user["id"] == user_id:
            return user
    return None


def create_user(name: str) -> Dict[str, object]:
    global _next_user_id
    new_user = {"id": _next_user_id, "name": name}
    _users_store.append(new_user)
    _next_user_id += 1
    return new_user


