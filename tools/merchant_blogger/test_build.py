#!/usr/bin/env python3
"""Offline assertions for the portable merchant Blogger pack generator."""
import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree
from build import build, normalized, image_link


class BloggerPackTests(unittest.TestCase):
    def test_both_merchants(self):
        for merchant, expected_count, expected_phone_unverified in (
            ("yonggi-susan", 24, False),
            ("ilwol-susan", 37, True),
        ):
            with self.subTest(merchant=merchant), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / merchant
                info = build(merchant, out, "https://garakmall.lexid.site")
                self.assertEqual(info["menus"], expected_count)
                self.assertEqual(info["merchant_id"], merchant)
                self.assertEqual(info["blogger_published"], False)
                self.assertEqual(info["blogger_theme_applied"], False)
                self.assertEqual(info["phone_requires_verification"], expected_phone_unverified)
                self.assertTrue((out / "post.html").is_file())
                self.assertTrue((out / "menus.csv").read_text(encoding="utf-8-sig").count("현재 가격 재확인 필요") == expected_count)
                self.assertEqual((out / "post.html").read_text().count("border-bottom:1px"), expected_count)
                ElementTree.parse(out / "theme.xml")
                self.assertIn(merchant, (out / "theme.xml").read_text())
                self.assertIn("Blogger", (out / "README.md").read_text())

    def test_source_schema_refusal(self):
        with self.assertRaises(ValueError):
            normalized({"id": "../../secrets", "location": {}, "menus": []})

    def test_asset_path_escape(self):
        for value in ("https://another-site/image.png", "/etc/passwd", "../private.jpg"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                image_link(value, "https://garakmall.lexid.site")

    def test_third_merchant_from_json(self):
        from build import ROOT
        data = json.loads((ROOT / "storefront/merchant/yonggi-susan.json").read_text())
        data["id"] = "new-merchant"
        data["name"] = "샘플 신규 상인"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "merchant.json"
            source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            out = Path(tmp) / "kit"
            result = build("new-merchant", out, "https://garakmall.lexid.site", source_json=source)
            self.assertEqual(result["merchant_id"], "new-merchant")
            self.assertEqual(result["menus"], 24)
            self.assertIn("샘플 신규 상인", (out / "post.html").read_text())
            self.assertIn("샘플 신규 상인", (out / "theme.xml").read_text())
            ElementTree.parse(out / "theme.xml")

    def test_merchant_location_uncertainty(self):
        from build import ROOT, normalized
        raw = json.loads((ROOT / "storefront/merchant/yonggi-susan.json").read_text())
        info = normalized(raw)
        self.assertTrue(info["unit_unverified"])
        self.assertFalse(info["phone_unverified"])
        self.assertEqual(info["unit"], "C-28")


if __name__ == "__main__":
    unittest.main(verbosity=2)
