from __future__ import annotations

from typing import Final

DEFAULT_SHOP_KEY: Final[str] = "aadarsh-eye-boutique-center"

SHOP_NAME_BY_KEY: Final[dict[str, str]] = {
    "aadarsh-eye-boutique-center": "Aadarsh Eye Boutique Center",
    "adarsh-optometric-center": "Adarsh Optometric Center",
    "adarsh-optical-center": "Adarsh Optical Center",
}

SHOP_MOBILE_PASSCODE_BY_KEY: Final[dict[str, str]] = {
    "aadarsh-eye-boutique-center": "9082967356",
    "adarsh-optometric-center": "6124157631",
    "adarsh-optical-center": "6124157622",
}

VALID_SHOP_KEYS: Final[set[str]] = set(SHOP_NAME_BY_KEY.keys())


def resolve_shop_key(raw_shop_key: str | None) -> str:
    if raw_shop_key is None:
        return DEFAULT_SHOP_KEY

    normalized = raw_shop_key.strip().lower()
    if normalized == "":
        return DEFAULT_SHOP_KEY

    if normalized not in VALID_SHOP_KEYS:
        raise ValueError("invalid shop key")

    return normalized


def get_shop_name(shop_key: str) -> str:
    return SHOP_NAME_BY_KEY.get(shop_key, SHOP_NAME_BY_KEY[DEFAULT_SHOP_KEY])
