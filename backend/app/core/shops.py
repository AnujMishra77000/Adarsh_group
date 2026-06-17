from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Final


@dataclass(frozen=True)
class ShopDefinition:
    code: str
    display_name: str
    location_label: str
    center_type: str
    is_active: bool = True
    legacy_codes: tuple[str, ...] = field(default_factory=tuple)


SHOP_DEFINITIONS: Final[tuple[ShopDefinition, ...]] = (
    ShopDefinition(
        code="adarsh-optical-centre",
        display_name="Adarsh Optical Centre",
        location_label="",
        center_type="Optical centre",
        legacy_codes=("adarsh-optical-center",),
    ),
    ShopDefinition(
        code="adarsh-optometric-clinic",
        display_name="Adarsh Optometric Clinic",
        location_label="Khadakpada, Kalyan West",
        center_type="Optometric clinic",
        legacy_codes=("adarsh-optometric-center",),
    ),
    ShopDefinition(
        code="adarsh-opticals-muxar",
        display_name="Adarsh Opticals",
        location_label="Near Muxar Hospital",
        center_type="Optical centre",
    ),
    ShopDefinition(
        code="adarsh-eye-boutique",
        display_name="Adarsh Eye Boutique",
        location_label="",
        center_type="Eye boutique",
        legacy_codes=("aadarsh-eye-boutique-center",),
    ),
)

DEFAULT_SHOP_CODE: Final[str] = "adarsh-eye-boutique"
DEFAULT_SHOP_KEY: Final[str] = DEFAULT_SHOP_CODE

SHOP_DEFINITION_BY_CODE: Final[dict[str, ShopDefinition]] = {
    shop.code: shop for shop in SHOP_DEFINITIONS
}
LEGACY_CODE_TO_CANONICAL_CODE: Final[dict[str, str]] = {
    legacy_code: shop.code
    for shop in SHOP_DEFINITIONS
    for legacy_code in shop.legacy_codes
}
VALID_SHOP_CODES: Final[set[str]] = set(SHOP_DEFINITION_BY_CODE)
VALID_SHOP_KEYS: Final[set[str]] = VALID_SHOP_CODES | set(LEGACY_CODE_TO_CANONICAL_CODE)


def normalize_shop_code(raw_shop_code: str | None) -> str:
    return (raw_shop_code or "").strip().lower()


def normalize_shop_identifier(raw_identifier: str | None) -> str:
    normalized = (raw_identifier or "").strip().lower()
    if not normalized:
        return ""

    digits = re.sub(r"\D", "", normalized)
    if digits:
        return digits[-10:] if len(digits) >= 10 else digits

    return normalized


def get_canonical_shop_code(raw_shop_code: str | None) -> str | None:
    normalized = normalize_shop_code(raw_shop_code)
    if not normalized:
        return None
    if normalized in SHOP_DEFINITION_BY_CODE:
        return normalized
    return LEGACY_CODE_TO_CANONICAL_CODE.get(normalized)


def resolve_shop_key(raw_shop_key: str | None) -> str:
    canonical_code = get_canonical_shop_code(raw_shop_key)
    if canonical_code is None:
        if normalize_shop_code(raw_shop_key) == "":
            return DEFAULT_SHOP_CODE
        raise ValueError("invalid shop key")
    return canonical_code


def get_shop_definition(shop_code: str) -> ShopDefinition | None:
    canonical_code = get_canonical_shop_code(shop_code)
    if canonical_code is None:
        return None
    return SHOP_DEFINITION_BY_CODE.get(canonical_code)


def get_shop_name(shop_key: str) -> str:
    shop = get_shop_definition(shop_key)
    if shop is None:
        return SHOP_DEFINITION_BY_CODE[DEFAULT_SHOP_CODE].display_name
    return shop.display_name


def get_shop_aliases(shop_code: str) -> set[str]:
    shop = get_shop_definition(shop_code)
    if shop is None:
        return {normalize_shop_code(shop_code)}
    return {shop.code, *shop.legacy_codes}


def get_shop_identifier_map(configured_mappings: dict[str, str]) -> dict[str, str]:
    identifier_map: dict[str, str] = {}
    for identifier, shop_code in configured_mappings.items():
        normalized_identifier = normalize_shop_identifier(identifier)
        canonical_code = get_canonical_shop_code(shop_code)
        if normalized_identifier and canonical_code:
            identifier_map[normalized_identifier] = canonical_code

    for shop in SHOP_DEFINITIONS:
        identifier_map[normalize_shop_identifier(shop.code)] = shop.code
        identifier_map[normalize_shop_identifier(shop.display_name)] = shop.code
        for legacy_code in shop.legacy_codes:
            identifier_map[normalize_shop_identifier(legacy_code)] = shop.code

    return identifier_map
