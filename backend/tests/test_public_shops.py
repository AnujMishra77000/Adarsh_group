from __future__ import annotations

from collections import defaultdict, deque
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.v1.endpoints import public_shops
from app.core.config import settings
from app.main import app


def test_shop_resolver_returns_actionable_message_when_mobile_lookup_is_unconfigured() -> None:
    with (
        patch.object(settings, "shop_identifier_mappings", {}),
        patch.object(public_shops, "_attempts_by_client", defaultdict(deque)),
        TestClient(app) as client,
    ):
        response = client.post("/api/v1/public/shops/resolve", json={"identifier": "9876543210"})

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "shop_mobile_lookup_not_configured",
            "message": (
                "This environment does not have shop mobile lookup configured yet. "
                "Use a center identifier or add SHOP_IDENTIFIER_MAPPINGS in backend/.env."
            ),
        }
    }


def test_shop_resolver_accepts_center_codes_without_mobile_lookup_mapping() -> None:
    with (
        patch.object(settings, "shop_identifier_mappings", {}),
        patch.object(public_shops, "_attempts_by_client", defaultdict(deque)),
        TestClient(app) as client,
    ):
        response = client.post("/api/v1/public/shops/resolve", json={"identifier": "adarsh-eye-boutique"})

    assert response.status_code == 200
    assert response.json()["code"] == "adarsh-eye-boutique"
