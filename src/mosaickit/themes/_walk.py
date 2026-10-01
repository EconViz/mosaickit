def role_chain(role: str, fallback_category: str) -> tuple[str, ...]:
    """Return high-to-low priority keys without duplicates."""
    parts = role.split(".")
    keys = [".".join(parts[:i]) for i in range(len(parts), 0, -1)]
    return tuple(dict.fromkeys([*keys, fallback_category]))
