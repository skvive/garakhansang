from pathlib import Path
import json, unittest, zipfile

ROOT = Path(__file__).resolve().parents[1]

class CatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'catalog/menus_47.json').read_text(encoding='utf-8'))
        cls.items = cls.data['items']

    def test_unique_catalog(self):
        self.assertEqual(len(self.items), 47)
        self.assertEqual(len({i['id'] for i in self.items}), 47)
        self.assertEqual(len({i['name'] for i in self.items}), 47)
        self.assertEqual(len({i['category'] for i in self.items}), 12)

    def test_item_attributes(self):
        for item in self.items:
            self.assertGreater(item['price_krw'], 0)
            self.assertEqual(item['catalog_visibility'], 'needs_merchandising_approval')
            self.assertTrue(item['image_is_ai_concept'])
            self.assertFalse(item['is_orderable'])
            self.assertTrue((ROOT / 'app/src/main/assets' / item['image']).is_file())
            self.assertTrue(item['description'] or item['name'])

    def test_java_ui_wired(self):
        text = (ROOT / 'app/src/main/java/site/lexid/garakhansang/order/MainActivity.java').read_text(encoding='utf-8')
        self.assertIn('cartTotal()', text)
        self.assertIn('menu_%02d.jpg', text)
        self.assertIn('주문내역', text)
        self.assertIn('실제 결제 불가', text)
        self.assertIn('getSharedPreferences(', text)

if __name__ == '__main__': unittest.main()
