"""Immutable, versioned menu option sets for the GARAK local-beta catalog.

Never infer options or prices from a client. All drafts require explicit admin approval.
This module does not create orders, capture funds, or call delivery providers.
"""
from __future__ import annotations

import json
import re

ID = re.compile(r"^[a-z][a-z0-9_-]{0,47}$")


def _identifier(value, label):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError(f"invalid {label}")
    return value


def _label(value, field):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 100:
        raise ValueError(f"invalid {field}")
    if any(ord(ch) < 32 for ch in value):
        raise ValueError(f"invalid {field}")
    return value.strip()


def _int(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"invalid {label}")
    return value


def validate_groups(groups):
    """Canonicalize a bounded selection schema, reject unknown/duplicate values."""
    if not isinstance(groups, list) or len(groups) > 8:
        raise ValueError("option groups must be an array of up to 8")
    normalized = []
    seen_groups = set()
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("invalid option group")
        gid = _identifier(group.get("id"), "group id")
        if gid in seen_groups:
            raise ValueError("duplicate option group")
        seen_groups.add(gid)
        title = _label(group.get("title"), "group title")
        required = group.get("required", False)
        if type(required) is not bool:
            raise ValueError("required must be boolean")
        choices = group.get("choices")
        if not isinstance(choices, list) or not 1 <= len(choices) <= 20:
            raise ValueError("option group requires 1..20 choices")
        min_sel = _int(group.get("min_select", 1 if required else 0), 0, 20, "minimum selections")
        max_sel = _int(group.get("max_select", 1), 1, 20, "maximum selections")
        if min_sel > max_sel or max_sel > len(choices) or (required and min_sel == 0):
            raise ValueError("invalid option selection bounds")
        normalized_choices = []
        seen_choices = set()
        for choice in choices:
            if not isinstance(choice, dict):
                raise ValueError("invalid option choice")
            cid = _identifier(choice.get("id"), "choice id")
            if cid in seen_choices:
                raise ValueError("duplicate option choice")
            seen_choices.add(cid)
            normalized_choices.append({
                "id": cid,
                "label": _label(choice.get("label"), "choice label"),
                "additional_krw": _int(choice.get("additional_krw", 0), 0, 1000000, "option price"),
                "stock": _int(choice["stock"], 0, 1000000, "option stock")
                         if choice.get("stock") is not None else None,
            })
        normalized.append({
            "id": gid, "title": title, "required": required,
            "min_select": min_sel, "max_select": max_sel,
            "choices": normalized_choices,
        })
    return normalized


def _set(con, product_id, *, status="approved"):
    return con.execute(
        """SELECT id,version,status,groups_json,created_at,approved_at
           FROM product_option_sets WHERE product_id=? AND status=?
           ORDER BY version DESC LIMIT 1""", (product_id, status)
    ).fetchone()


def approved_options(con, product_id):
    row = _set(con, product_id)
    if row is None:
        return 0, []
    return row["version"], validate_groups(json.loads(row["groups_json"]))


def draft_options(con, product_id):
    row = _set(con, product_id, status="draft")
    if row is None:
        return None
    return {"version": row["version"], "status": row["status"],
            "groups": json.loads(row["groups_json"])}


def price_options(con, product_id, selections, qty):
    """Return (delta per unit, canonical selected choices, approved option version)."""
    _int(qty, 1, 99, "quantity")
    if not isinstance(selections, list) or len(selections) > 8:
        raise ValueError("invalid selected options")
    version, groups = approved_options(con, product_id)
    expected = {g["id"]: g for g in groups}
    provided = {}
    for entry in selections:
        if not isinstance(entry, dict):
            raise ValueError("invalid selected option")
        gid = _identifier(entry.get("group_id"), "group id")
        ids = entry.get("choice_ids")
        if gid in provided or gid not in expected or not isinstance(ids, list) or len(ids) > 20:
            raise ValueError("unknown or duplicate selection group")
        if any(not isinstance(x, str) or not ID.fullmatch(x) for x in ids) or len(ids) != len(set(ids)):
            raise ValueError("duplicate or malformed choice")
        provided[gid] = ids
    chosen = []
    delta = 0
    for group in groups:
        ids = provided.get(group["id"], [])
        if not group["min_select"] <= len(ids) <= group["max_select"]:
            raise ValueError("required option not selected or too many selections")
        choices = {c["id"]: c for c in group["choices"]}
        for cid in ids:
            choice = choices.get(cid)
            if choice is None:
                raise ValueError("unknown option choice")
            if choice["stock"] is not None and qty > choice["stock"]:
                raise ValueError("option stock insufficient")
            delta += choice["additional_krw"]
            chosen.append({
                "group_id": group["id"], "choice_id": cid,
                "label": choice["label"], "additional_krw": choice["additional_krw"]
            })
    return delta, chosen, version


def create_revision(con, product_slug, groups, actor_id, timestamp):
    """Append-only draft. No existing option or product record is deleted."""
    canonical = validate_groups(groups)
    product = con.execute("SELECT id FROM products WHERE slug=?", (product_slug,)).fetchone()
    if product is None:
        raise LookupError("unknown product")
    product_id = product["id"]
    version = con.execute(
        "SELECT COALESCE(MAX(version),0)+1 FROM product_option_sets WHERE product_id=?",
        (product_id,)
    ).fetchone()[0]
    con.execute(
        """INSERT INTO product_option_sets(product_id,version,status,groups_json,author_id,created_at)
           VALUES(?,?,'draft',?,?,?)""",
        (product_id, version, json.dumps(canonical, ensure_ascii=False, separators=(",", ":")),
         actor_id, timestamp)
    )
    return {"slug": product_slug, "version": version, "status": "draft", "groups": canonical}


def approve_revision(con, product_slug, version, timestamp):
    """Supersede prior approval; keep all previous revisions for audit."""
    _int(version, 1, 1000000, "version")
    product = con.execute(
        """SELECT p.id FROM products p JOIN merchants m ON m.id=p.merchant_id
           WHERE p.slug=? AND p.status='published' AND m.status='active'
                 AND m.verified=1""", (product_slug,)
    ).fetchone()
    if product is None:
        raise ValueError("product and merchant must be verified and published")
    pid = product["id"]
    row = con.execute(
        """SELECT status FROM product_option_sets
           WHERE product_id=? AND version=?""", (pid, version)
    ).fetchone()
    if row is None or row["status"] != "draft":
        raise ValueError("only an existing draft can be approved")
    con.execute(
        """UPDATE product_option_sets SET status='superseded'
           WHERE product_id=? AND status='approved'""", (pid,)
    )
    con.execute(
        """UPDATE product_option_sets SET status='approved',approved_at=?
           WHERE product_id=? AND version=? AND status='draft'""",
        (timestamp, pid, version)
    )
    return {"slug": product_slug, "version": version, "status": "approved"}
