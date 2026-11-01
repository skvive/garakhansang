#!/usr/bin/env python3
"""Daily KAMIS Seoul seafood WHOLESALE reference prices; never infer Garak auction prices."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parents[1] / "storefront/data/seoul-seafood-wholesale-latest.json"
API = "https://www.kamis.or.kr/service/price/xml.do"
SOURCE = "https://www.kamis.or.kr/customer/reference/openapi_list.do?action=detail&boardno=1"
KST = dt.timezone(dt.timedelta(hours=9))
MAX_AGE_DAYS = 14

def numeric(s):
    value = (s or "").replace(",", "").strip()
    if not re.fullmatch(r"\d+(?:\.\d+)?", value):
        return None
    price = float(value)
    return round(price) if 0 < price < 100000000 else None

def parse_date(value):
    raw = (value or "").strip()
    if re.fullmatch(r"\d{8}", raw):
        raw = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    try:
        return dt.date.fromisoformat(raw).isoformat()
    except ValueError:
        return None

def parse_xml(content, today):
    root = ET.fromstring(content)
    rows = root.findall(".//data/item") or root.findall("./item")
    if not rows:
        raise ValueError("KAMIS returned no rows or API error")
    result = []
    for item in rows:
        field = {child.tag: (child.text or "").strip() for child in item}
        price, previous = numeric(field.get("dpr1")), numeric(field.get("dpr2"))
        trade_date = parse_date(field.get("day1"))
        name = field.get("item_name", "").strip()
        unit = field.get("unit", "").strip()
        if not name or not unit or not price or not trade_date:
            continue
        age = (today - dt.date.fromisoformat(trade_date)).days
        if age < 0 or age > MAX_AGE_DAYS:
            continue
        result.append({
            "itemName": name[:80], "variety": field.get("kind_name", "")[:100],
            "grade": field.get("rank", "")[:60], "unit": unit[:40],
            "priceWon": price, "tradeDate": trade_date,
            "previousPriceWon": previous, "previousDate": parse_date(field.get("day2")),
            "source": "KAMIS", "region": "서울", "priceType": "wholesale_reference"
        })
    if not result:
        raise ValueError("No valid recent observations with date and units")
    return {
        "schemaVersion": 1, "status": "verified_wholesale_reference",
        "isGarakAuction": False, "isStorePrice": False,
        "provider": "한국농수산식품유통공사 KAMIS", "region": "서울",
        "category": "수산물", "priceType": "도매 참고가격",
        "sourceUrl": SOURCE, "fetchedAt": dt.datetime.now(KST).isoformat(timespec="seconds"),
        "latestTradeDate": max(row["tradeDate"] for row in result),
        "items": sorted(result, key=lambda x: (x["itemName"], x["variety"], x["grade"]))
    }

def fetch_live():
    key, user = os.getenv("KAMIS_CERT_KEY", "").strip(), os.getenv("KAMIS_CERT_ID", "").strip()
    if not key or not user:
        raise RuntimeError("KAMIS credentials not configured")
    query = urllib.parse.urlencode({
        "action": "dailyPriceByCategoryList", "p_cert_key": key, "p_cert_id": user,
        "p_returntype": "xml", "p_product_cls_code": "02",
        "p_item_category_code": "600", "p_country_code": "1101", "p_convert_kg_yn": "N"
    })
    req = urllib.request.Request(API + "?" + query, headers={"User-Agent": "GarakHansangOfficialPrices/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        content = response.read(4_000_001)
        if len(content) > 4_000_000:
            raise ValueError("API response exceeds size limit")
        return content

def main():
    data = parse_xml(fetch_live(), dt.datetime.now(KST).date())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(OUT)
    print("Validated KAMIS rows:", len(data["items"]), "trade date:", data["latestTradeDate"])

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Deliberately do not log secret-bearing request details.
        print("Daily fetch aborted; published data retained:", type(exc).__name__, file=sys.stderr)
        sys.exit(1)
