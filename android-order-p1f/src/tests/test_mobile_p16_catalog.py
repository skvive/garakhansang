"""P1b market -> merchant -> product exploration contract, no Neon connection."""
from contextlib import contextmanager
from urllib.parse import quote
import test_mobile_p1 as v15

api, client = v15.api, v15.client

ROWS = [
    {"id":"p1", "market_id":"garak", "name":"광어회", "merchant_name":"광양수산", "price":41000},
    {"id":"p2", "market_id":"garak", "name":"참돔회", "merchant_name":"광양수산", "price":55000},
    {"id":"p3", "market_id":"garak", "name":"오이", "merchant_name":"가락 채소집", "price":1000},
    {"id":"p4", "market_id":"noryangjin", "name":"도미회", "merchant_name":"동해수산", "price":47000},
]

class Cursor:
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def execute(self,sql,values=None):
        self.last_query, self.last_values = sql,values
    def fetchall(self):
        return [{"id":"garak","name":"가락시장","region_code":"11","service_status":"pilot"}]

class DB:
    def cursor(self): return Cursor()

@contextmanager
def fake_db():
    yield DB()


def _configure(monkeypatch):
    monkeypatch.setattr(api.repo, "open_catalog_db", fake_db)
    monkeypatch.setattr(api.repo, "catalog", lambda db,mid: [x for x in ROWS if mid is None or x['market_id']==mid],raising=False)


def test_market_to_store_to_products_by_exact_unicode_name(monkeypatch):
    _configure(monkeypatch)
    markets=client.get('/api/v1/mobile/markets');assert markets.status_code==200
    assert markets.json()['data']['items'][0]['serviceable'] is False
    merchants=client.get('/api/v1/mobile/merchants?market_id=garak');assert merchants.status_code==200
    names={x['name'] for x in merchants.json()['data']['items']}
    assert names=={'광양수산','가락 채소집'}
    url='/api/v1/mobile/products?market_id=garak&merchant_name='+quote('광양수산')
    products=client.get(url);assert products.status_code==200
    items=products.json()['data']['items']
    assert {x['name'] for x in items}=={'광어회','참돔회'}
    assert all(x['orderable'] is False and x['image_is_ai_concept'] is True for x in items)
    assert products.json()['data']['checkout_enabled'] is False


def test_merchants_isolated_by_market(monkeypatch):
    _configure(monkeypatch)
    market=client.get('/api/v1/mobile/merchants?market_id=noryangjin')
    assert [x['name'] for x in market.json()['data']['items']]==['동해수산']
    cross=client.get('/api/v1/mobile/products',params={'market_id':'noryangjin','merchant_name':'광양수산'})
    assert cross.status_code==200 and cross.json()['data']['items']==[]
    empty=client.get('/api/v1/mobile/products',params={'market_id':'garak','merchant_name':'없는 업체'})
    assert empty.status_code==200 and empty.json()['data']['items']==[]


def test_reject_malformed_market_and_merchant_before_db(monkeypatch):
    def must_not_access_db(): raise AssertionError('DB should not be touched')
    monkeypatch.setattr(api.repo,'open_catalog_db',must_not_access_db)
    for bad in ('../../admin','garak/../secret','!','💳','garak\nfoo'):
        for resource in ('merchants','products'):
            response=client.get('/api/v1/mobile/'+resource,params={'market_id':bad})
            assert response.status_code==422,(resource,bad,response.text)
    for bad in (' ', '\n', 'a'*91):
        r=client.get('/api/v1/mobile/products',params={'merchant_name':bad})
        assert r.status_code==422, (bad,r.text)


def test_serviceability_stays_false_independent_of_catalog(monkeypatch):
    _configure(monkeypatch)
    r=client.get('/api/v1/mobile/serviceability',params={'postal_code':'05600'})
    assert r.status_code==200
    data=r.json()['data']; assert data['serviceable'] is False
    assert data['verified'] is False and data['fee_krw'] is None


def test_no_side_effects_or_unauthorized_endpoints():
    for path in ('/api/v1/mobile/merchants','/api/v1/mobile/products', '/api/v1/mobile/markets'):
        assert client.post(path).status_code==405
        assert client.put(path).status_code==405
    assert client.post('/api/v1/mobile/orders').status_code==404
    assert client.post('/api/v1/mobile/payments/prepare').status_code==404
