from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic

from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.shops import get_shop_definition, get_shop_identifier_map, normalize_shop_identifier
from app.schemas.shop import ShopPublicRead, ShopResolveRequest

router = APIRouter(prefix="/public/shops", tags=["public-shops"])

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_ATTEMPTS = 12
_attempts_by_client: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _check_rate_limit(request: Request) -> None:
    now = monotonic()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    attempts = _attempts_by_client[_client_key(request)]

    while attempts and attempts[0] < cutoff:
        attempts.popleft()

    if len(attempts) >= RATE_LIMIT_MAX_ATTEMPTS:
        raise AppException(
            status_code=429,
            code="shop_resolve_rate_limited",
            message="Too many shop lookup attempts. Please wait and try again.",
        )

    attempts.append(now)


@router.post("/resolve", response_model=ShopPublicRead)
def resolve_public_shop(payload: ShopResolveRequest, request: Request) -> ShopPublicRead:
    _check_rate_limit(request)

    raw_identifier = payload.mobile or payload.identifier
    normalized_identifier = normalize_shop_identifier(raw_identifier)
    configured_identifier_mappings = settings.shop_identifier_mappings
    identifier_map = get_shop_identifier_map(configured_identifier_mappings)
    shop_code = identifier_map.get(normalized_identifier)
    shop = get_shop_definition(shop_code or "")

    if shop is None or not shop.is_active:
        is_mobile_lookup = normalized_identifier.isdigit()
        has_configured_mobile_lookup = any(
            normalize_shop_identifier(identifier).isdigit() for identifier in configured_identifier_mappings
        )
        if is_mobile_lookup and not has_configured_mobile_lookup:
            raise AppException(
                status_code=404,
                code="shop_mobile_lookup_not_configured",
                message=(
                    "This environment does not have shop mobile lookup configured yet. "
                    "Use a center identifier or add SHOP_IDENTIFIER_MAPPINGS in backend/.env."
                ),
            )
        raise AppException(
            status_code=404,
            code="shop_not_found",
            message="Shop identifier not recognized.",
        )

    return ShopPublicRead(
        code=shop.code,
        display_name=shop.display_name,
        location_label=shop.location_label,
        center_type=shop.center_type,
    )
