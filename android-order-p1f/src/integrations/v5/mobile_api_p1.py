"""Garak Hansang Order P1 mobile READ-ONLY adapter for the existing V5 FastAPI app.

Install in the V5 package as backend/mobile_api_p1.py; include its `router`
under api_v5.app. All endpoints are fail-closed pilot previews. No live checkout.
Uses the EXISTING least-privileged V5 read-only database adapter.
"""
import re
import uuid
from contextlib import contextmanager

from fastapi import APIRouter, HTTPException, Query, Request, Header
from backend.auth_v5 import verify_oidc, AuthenticationError
from backend import repository_v5 as repo

router = APIRouter(prefix="/api/v1/mobile", tags=["mobile-read-p1"])


def envelope(request: Request, data):
    # A fresh opaque ID; no user identifiers or addresses in response metadata.
    return {"request_id": str(uuid.uuid4()), "data": data}


@contextmanager
def catalog_db():
    try:
        with repo.open_catalog_db() as db:
            yield db
    except repo.StorageUnavailable as exc:
        # Do not leak connection strings or database error internals.
        raise HTTPException(status_code=503, detail="개발용 읽기 전용 카탈로그가 연결되지 않았습니다.") from exc


@router.get("/bootstrap")
def bootstrap(request: Request):
    return envelope(request, {
        "brand": "가락한상 오더", "mode": "development_preview",
        "catalog_mode": "demo_only", "checkout_enabled": False,
        "payment_enabled": False, "delivery_dispatch_enabled": False,
        "auth_login_enabled": False, "real_address_enabled": False,
        "service_area_verified": False,
        "message": "운영 계약·주소·결제·배송 연결 전에는 주문할 수 없습니다.",
    })


@router.get("/auth/status")
def auth_status(request: Request):
    return envelope(request, {"login_enabled": False, "provider": "Neon Auth (integration pending)", "reason": "OAuth public client/App Link 미검증", "oauth_public_client_configured": False, "google_social_provider_verified_in_neon_console": False})


@router.get("/auth/session")
def auth_session(request: Request, authorization: str | None = Header(default=None)):
    """Verify only the existing V5 JWT; NEVER derive identity from client input.

    Disabled OAuth UI does not disable server verification of a pre-existing JWT.
    No subject, email, role, or raw token is included in the response.
    """
    if not authorization or len(authorization) > 12010:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.",
                            headers={"WWW-Authenticate": "Bearer"})
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise HTTPException(status_code=401, detail="유효하지 않은 인증 형식입니다.",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        # Existing V5 issuer+audience+EdDSA+JWKS validation, never bypass it.
        verify_oidc(parts[1])
    except (AuthenticationError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="인증을 확인할 수 없습니다.",
                            headers={"WWW-Authenticate": "Bearer"})
    return envelope(request, {"authenticated": True, "checkout_enabled": False,
                              "account_profile_available": False,
                              "message": "인증 토큰 검증 완료 · 실제 주문은 여전히 차단됩니다."})


@router.get("/serviceability")
def serviceability(request: Request, postal_code: str = Query(min_length=5, max_length=5)):
    if not re.fullmatch(r"[0-9]{5}", postal_code, flags=re.ASCII):
        raise HTTPException(status_code=422, detail="우편번호는 숫자 5자리여야 합니다.")
    # IMPORTANT: No real zone source has been approved. No inferred availability.
    return envelope(request, {"serviceable": False, "verified": False,
                              "status": "not_configured", "fee_krw": None,
                              "message": "실제 배송권역과 배송비가 아직 검증되지 않았습니다."})


@router.get("/markets")
def markets(request: Request):
    with catalog_db() as db:
        with db.cursor() as cur:
            cur.execute("""SELECT id, name, region_code, service_status
                        FROM gho.markets
                        WHERE service_status IN ('pilot','active')
                        ORDER BY name LIMIT 100""")
            rows = cur.fetchall()
    # A pilot market record is NOT proof of active delivery service.
    return envelope(request, {"items": [{"id": r["id"], "name": r["name"],
        "region_code": r["region_code"], "catalog_mode": "demo_only",
        "serviceable": False} for r in rows], "demo": True})


def _checked_market(market_id: str | None):
    if market_id is not None and not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", market_id, flags=re.ASCII):
        raise HTTPException(status_code=422, detail="시장 식별자가 올바르지 않습니다.")
    return market_id


@router.get("/merchants")
def merchants(request: Request, market_id: str | None = Query(default=None, max_length=60)):
    _checked_market(market_id)
    with catalog_db() as db:
        # V5 catalog role does not have SELECT on merchants.market_id. Reuse
        # the existing least-privileged catalog query instead of broadening grants.
        rows = repo.catalog(db, market_id)
    unique = sorted({(r["market_id"], r["merchant_name"]) for r in rows})
    return envelope(request, {"items": [{"id": None, "market_id": market,
        "name": name, "demo": True, "orderable": False,
        "serviceable": False, "merchant_id_available": False}
        for market, name in unique], "demo": True})


@router.get("/products")
def products(request: Request, market_id: str | None = Query(default=None, max_length=60),
             merchant_name: str | None = Query(default=None, min_length=1, max_length=90)):
    _checked_market(market_id)
    if merchant_name is not None and (not merchant_name.strip() or "\n" in merchant_name or "\r" in merchant_name):
        raise HTTPException(status_code=422, detail="매장 이름이 올바르지 않습니다.")
    with catalog_db() as db:
        rows = repo.catalog(db, market_id)
    if merchant_name is not None:
        # Exact match on existing limited catalog result; no new DB grants.
        rows = [row for row in rows if row["merchant_name"] == merchant_name]
    # Intentionally do not infer published/for-sale state from V5 demo rows.
    return envelope(request, {"items": [{"id": str(r["id"]), "market_id": r["market_id"],
        "name": r["name"], "merchant_name": r["merchant_name"],
        "price_krw": int(r["price"]), "image_is_ai_concept": True,
        "catalog_visibility": "demo_only", "orderable": False} for r in rows],
        "demo": True, "checkout_enabled": False})
