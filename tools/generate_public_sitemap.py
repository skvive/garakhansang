#!/usr/bin/env python3
"""Deterministic public-site sitemap. Only public canonical HTML pages."""
from pathlib import Path
import xml.etree.ElementTree as ET

SITE = "https://garakmall.lexid.site"
ROOT = Path(__file__).resolve().parents[1] / "storefront"
PUBLIC_ROOT = [
    "index.html", "stores.html", "prices.html", "market-map.html",
    "market-guide.html", "map.html", "events.html", "coupons.html",
    "merchant-center.html", "merchant-marketing.html", "wholesale.html", "blogger-service.html", "ilwol-susan.html",
    "yonggi-susan.html", "community/index.html", "community/merchants.html", "merchant/index.html",
    "recipes/index.html", "recipes/meat.html", "recipes/produce.html",
    "category/seafood.html", "category/meat.html", "category/produce.html",
    "category/sets.html", "category/extras.html",
]
PUBLIC_GLOBS = ["recipes/recipe-*.html", "product/*.html"]
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

def make():
    candidates = [ROOT / p for p in PUBLIC_ROOT]
    for pattern in PUBLIC_GLOBS:
        candidates.extend(sorted(ROOT.glob(pattern)))
    # Noindex sample/detail pages must not be submitted for indexing.
    def indexable(p: Path) -> bool:
        if not p.is_file():
            return False
        import re
        head = p.read_text(encoding="utf-8-sig", errors="replace")[:5000].lower()
        return not any("noindex" in tag and re.search(r'name\s*=\s*["\x27]robots["\x27]', tag)
                       for tag in re.findall(r"<meta\b[^>]*>", head))
    paths = sorted({p.relative_to(ROOT).as_posix() for p in candidates if indexable(p)})
    assert "index.html" in paths and len(paths) >= 150
    ET.register_namespace("", NS)
    urlset = ET.Element(f"{{{NS}}}urlset")
    for path in paths:
        url = ET.SubElement(urlset, f"{{{NS}}}url")
        loc = SITE + ("/" if path == "index.html" else "/" + path)
        ET.SubElement(url, f"{{{NS}}}loc").text = loc
    out = ROOT / "sitemap.xml"
    ET.indent(urlset, space="  ")
    out.write_bytes(ET.tostring(urlset, encoding="utf-8", xml_declaration=True))
    print(f"Generated {len(paths)} public URLs in {out}")

if __name__ == "__main__":
    make()
