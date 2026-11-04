"""Public, read-only app bootstrap contract for the isolated GHO V5 demo.

The release switches are intentionally FAIL-CLOSED, not environment flags.
A real-money rollout requires a separate reviewed implementation and QA.
"""
from __future__ import annotations

def build_mobile_bootstrap() -> dict:
    """Fresh, JSON-serializable, non-sensitive response for Android/PWA."""
    return {
        "api_version": "v5",
        "app_name": "가락한상오더",
        "environment": "isolated-development",
        "demo_mode": True,
        "features": {
            "catalog_preview_enabled": True,
            "local_cart_enabled": True,
            "real_checkout_enabled": False,
            "payments_enabled": False,
            "live_tracking_enabled": False,
            "delivery_zone_verification_enabled": False,
            "merchant_live_orders_enabled": False,
            "rider_dispatch_enabled": False,
        },
        "delivery_service_zones": [],
        "delivery_eta_minutes": None,
        "message": "현재 시연용 서비스입니다. 실제 주문·결제·배달은 지원하지 않습니다.",
    }
