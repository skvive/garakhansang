"""P2 GARAK LOCAL BETA checkout-intent ledger.

An intent is a non-payable, admin-authenticated simulation of a customer's cart.
It is NOT an order, invoice, reservation, payment initiation or delivery job.
Preserve the existing orders table and never mark an intent paid or dispatchable.
"""
from __future__ import annotations
import hashlib
import json
import re
import secrets

from .mobile_commerce import quote_cart

IDEMPOTENCY = re.compile(r"^[a-zA-Z0-9_-]{16,96}$")
REF = re.compile(r"^GH-DEMO-[0-9a-f]{20}$")


class IntentConflict(ValueError):
    pass


def _validate_key(key):
    if not isinstance(key, str) or not IDEMPOTENCY.fullmatch(key):
        raise ValueError("Idempotency-Key must be 16..96 alphanumeric/underscore/hyphen characters")
    return key


def _validated_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")
    if set(payload) - {"items", "delivery_type"}:
        raise ValueError("unexpected fields (PII, payment data and client totals are forbidden)")
    if "items" not in payload:
        raise ValueError("items are required")
    return {
        "items": payload["items"],
        "delivery_type": payload.get("delivery_type", "delivery"),
    }


def _digest(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _response(row):
    data = dict(row)
    return {
        "reference": data["reference"],
        "version": data["version"],
        "status": data["status"],
        "merchant_id": data["merchant_id"],
        "delivery_type": data["delivery_type"],
        "quote": json.loads(data["quote_json"]),
        "subtotal_krw": data["subtotal_krw"],
        "delivery_fee_krw": None,
        "payable_total_krw": None,
        "currency": "KRW",
        "payment_status": "not_initiated",
        "checkout_enabled": False,
        "stock_reserved": False,
        "merchant_notified": False,
        "dispatch_enabled": False,
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
    }


def create_or_replay(con, *, payload, actor_id, key, timestamp):
    """Caller must hold BEGIN IMMEDIATE and commit before responding HTTP 201."""
    _validate_key(key)
    if type(actor_id) is not int or actor_id < 1:
        raise ValueError("authenticated admin id required")
    request = _validated_payload(payload)
    digest = _digest(request)
    saved = con.execute(
        "SELECT * FROM checkout_intents WHERE actor_id=? AND idempotency_key=?",
        (actor_id, key),
    ).fetchone()
    if saved:
        if saved["request_digest"] != digest:
            raise IntentConflict("idempotency key already used for a different cart")
        return _response(saved), False

    quote = quote_cart(con, request)
    if quote.get("checkout_enabled") is not False or quote.get("payable_total_krw") is not None:
        raise ValueError("intent ledger only accepts non-payable sandbox quotes")
    if not quote.get("items") or type(quote.get("subtotal_krw")) is not int:
        raise ValueError("invalid sandbox quote")
    if quote.get("merchant_id") is None:
        raise ValueError("missing verified merchant")

    reference = "GH-DEMO-" + secrets.token_hex(10)
    snapshot = json.dumps(quote, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"))
    con.execute(
        """INSERT INTO checkout_intents
          (reference,actor_id,idempotency_key,request_digest,
           merchant_id,delivery_type,status,version,quote_json,
           subtotal_krw,created_at,updated_at)
         VALUES(?,?,?,?,?,?,'awaiting_delivery_policy',1,?,?,?,?)""",
        (reference, actor_id, key, digest, quote["merchant_id"],
         request["delivery_type"], snapshot, quote["subtotal_krw"],
         timestamp, timestamp),
    )
    result = con.execute(
        "SELECT * FROM checkout_intents WHERE reference=? AND actor_id=?",
        (reference, actor_id),
    ).fetchone()
    return _response(result), True


def read_intent(con, *, reference, actor_id=None):
    if not isinstance(reference, str) or not REF.fullmatch(reference):
        raise LookupError("unknown sandbox checkout intent")
    if actor_id is None:
        row = con.execute(
            "SELECT * FROM checkout_intents WHERE reference=?", (reference,)
        ).fetchone()
    else:
        row = con.execute(
            "SELECT * FROM checkout_intents WHERE reference=? AND actor_id=?",
            (reference, actor_id),
        ).fetchone()
    if row is None:
        raise LookupError("unknown sandbox checkout intent")
    return _response(row)


def list_intents(con, *, actor_id=None):
    if actor_id is None:
        rows = con.execute(
            "SELECT * FROM checkout_intents ORDER BY id DESC LIMIT 100"
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT * FROM checkout_intents WHERE actor_id=? ORDER BY id DESC LIMIT 100",
            (actor_id,),
        ).fetchall()
    return [_response(row) for row in rows]


def abandon_intent(con, *, reference, actor_id, expected_version, timestamp):
    """Only the creating admin can abandon an unpaid simulation."""
    if type(expected_version) is not int or expected_version < 1:
        raise ValueError("positive integer version required")
    current = read_intent(con, reference=reference, actor_id=actor_id)
    if current["version"] != expected_version:
        raise IntentConflict("stale intent version")
    if current["status"] != "awaiting_delivery_policy":
        raise IntentConflict("intent cannot be abandoned from current state")
    cursor = con.execute(
        """UPDATE checkout_intents
           SET status='abandoned',version=version+1,updated_at=?
           WHERE reference=? AND actor_id=? AND status='awaiting_delivery_policy'
             AND version=?""",
        (timestamp, reference, actor_id, expected_version),
    )
    if cursor.rowcount != 1:
        raise IntentConflict("concurrent modification")
    return read_intent(con, reference=reference, actor_id=actor_id)
