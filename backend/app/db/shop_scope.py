from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import and_, false, or_
from sqlalchemy.orm import Session

from app.core.shops import get_canonical_shop_code, get_shop_aliases, normalize_shop_code
from app.models.shop import Shop


def canonical_shop_code(shop_key: str) -> str:
    return get_canonical_shop_code(shop_key) or normalize_shop_code(shop_key)


def shop_alias_values(shop_key: str) -> set[str]:
    canonical = canonical_shop_code(shop_key)
    aliases = get_shop_aliases(canonical)
    aliases.add(canonical)
    return aliases


def resolve_shop_id(db: Session, shop_key: str | None) -> int | None:
    canonical = canonical_shop_code(shop_key or "")
    if not canonical:
        return None
    return db.query(Shop.id).filter(Shop.code == canonical, Shop.is_active.is_(True)).scalar()


def assign_shop_scope(row: object, db: Session, shop_key: str, *, legacy_attr: str = "shop_key") -> None:
    canonical = canonical_shop_code(shop_key)
    if hasattr(row, legacy_attr):
        setattr(row, legacy_attr, canonical)
    if hasattr(row, "shop_id") and getattr(row, "shop_id") is None:
        setattr(row, "shop_id", resolve_shop_id(db, canonical))


def shop_filter(db: Session, model: type, shop_key: str, *, legacy_attr: str | None = "shop_key"):
    shop_id = resolve_shop_id(db, shop_key)
    shop_id_column = getattr(model, "shop_id", None)
    legacy_column = getattr(model, legacy_attr, None) if legacy_attr else None

    if shop_id is not None and shop_id_column is not None:
        if legacy_column is not None:
            return or_(
                shop_id_column == shop_id,
                and_(shop_id_column.is_(None), legacy_column.in_(shop_alias_values(shop_key))),
            )
        return shop_id_column == shop_id

    if legacy_column is not None:
        return legacy_column.in_(shop_alias_values(shop_key))

    return false()


def require_same_shop(row: object, db: Session, shop_key: str, *, legacy_attrs: Iterable[str] = ("shop_key",)) -> bool:
    expected_shop_id = resolve_shop_id(db, shop_key)
    row_shop_id = getattr(row, "shop_id", None)
    if expected_shop_id is not None and row_shop_id is not None:
        return row_shop_id == expected_shop_id

    aliases = shop_alias_values(shop_key)
    return any(getattr(row, legacy_attr, None) in aliases for legacy_attr in legacy_attrs)
