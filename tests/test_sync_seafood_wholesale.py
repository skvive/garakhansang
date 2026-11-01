import datetime as dt
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from sync_seafood_wholesale import parse_xml

TODAY = dt.date(2026, 11, 2)
SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<response><data>
<item><item_name>광어</item_name><kind_name>활어</kind_name><rank>상품</rank><unit>1kg</unit><day1>2026-10-31</day1><dpr1>12,500</dpr1><day2>2026-10-30</day2><dpr2>11,800</dpr2></item>
<item><item_name>참돔</item_name><unit>1kg</unit><day1>2026-10-31</day1><dpr1>-</dpr1></item>
</data></response>""".encode()

class TestKamis(unittest.TestCase):
    def test_parses_valid_price_and_source(self):
        result = parse_xml(SAMPLE, TODAY)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["priceWon"], 12500)
        self.assertEqual(result["items"][0]["unit"], "1kg")
        self.assertFalse(result["isGarakAuction"])
        self.assertFalse(result["isStorePrice"])

    def test_rejects_api_auth_error(self):
        with self.assertRaises(ValueError):
            parse_xml(b"<response><data><error_code>900</error_code></data></response>", TODAY)

    def test_rejects_old_data(self):
        with self.assertRaises(ValueError):
            parse_xml(SAMPLE, dt.date(2027, 1, 1))

    def test_rejects_missing_unit(self):
        invalid = b'<data><item><item_name>Fish</item_name><day1>2026-11-01</day1><dpr1>100</dpr1></item></data>'
        with self.assertRaises(ValueError):
            parse_xml(invalid, TODAY)

if __name__ == "__main__":
    unittest.main()
