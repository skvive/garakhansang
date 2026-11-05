"""Offline tests of read-only P1 API: never connects to Neon."""
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

# The addon is intended to be copied into an existing V5 backend package.
# Offline tests provide only the repository boundary as a local stand-in.
backend = types.ModuleType('backend')
backend.__path__ = []
repo = types.ModuleType('backend.repository_v5')
class StorageUnavailable(Exception): pass
repo.StorageUnavailable = StorageUnavailable
def unavailable_db(): raise StorageUnavailable('DSN secret should not leak')
repo.open_catalog_db = unavailable_db
backend.repository_v5 = repo
auth_v5 = types.ModuleType('backend.auth_v5')
class AuthenticationError(Exception): pass
auth_v5.AuthenticationError=AuthenticationError
def require_real_config(token): raise AuthenticationError('No real JWT configured for local test')
auth_v5.verify_oidc=require_real_config
backend.auth_v5=auth_v5
with patch.dict(sys.modules, {'backend':backend, 'backend.repository_v5':repo, 'backend.auth_v5':auth_v5}):
    path=Path(__file__).resolve().parents[1]/'integrations/v5/mobile_api_p1.py'
    spec=importlib.util.spec_from_file_location('mobile_api_p1_test', path)
    api=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
app=FastAPI()
app.include_router(api.router)
client=TestClient(app)


def test_bootstrap_disables_all_real_operations():
    r=client.get('/api/v1/mobile/bootstrap'); assert r.status_code==200
    data=r.json()['data']
    assert data['checkout_enabled'] is False
    assert data['payment_enabled'] is False
    assert data['delivery_dispatch_enabled'] is False
    assert data['real_address_enabled'] is False
    assert data['auth_login_enabled'] is False
    assert data['service_area_verified'] is False
    assert r.json()['request_id']


def test_serviceability_never_claims_delivery():
    for code in ('05500','00000','99999'):
        result=client.get('/api/v1/mobile/serviceability',params={'postal_code':code})
        assert result.status_code==200
        assert result.json()['data']['serviceable'] is False
        assert result.json()['data']['fee_krw'] is None
    for code in ('010','123456','1234a','', '１２３４５'):
        assert client.get('/api/v1/mobile/serviceability',params={'postal_code':code}).status_code==422


def test_read_only_config_fail_closed():
    for route in ('markets','merchants','products'):
        response=client.get('/api/v1/mobile/'+route)
        assert response.status_code==503
        assert 'secret' not in response.text


def test_demo_catalog_never_orderable(monkeypatch):
    class Cursor:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def execute(self,sql,values=None):pass
        def fetchall(self):return [{'id':'shop-1','market_id':'garak','business_name':'샘플수산','name':'샘플수산','region_code':'11','service_status':'pilot'}]
    class DB:
        def cursor(self): return Cursor()
    from contextlib import contextmanager
    @contextmanager
    def fake_db():yield DB()
    monkeypatch.setattr(api.repo,"open_catalog_db",fake_db)
    monkeypatch.setattr(api.repo,"catalog",lambda db,market_id:[{'id':'sample-1','market_id':'garak','name':'샘플상품','merchant_name':'샘플수산','price':10000}],raising=False)
    for route in ('markets','merchants','products'):
        response=client.get('/api/v1/mobile/'+route)
        assert response.status_code==200
        items=response.json()['data']['items']; assert len(items)==1
        assert items[0].get('serviceable',False) is False
        assert items[0].get('orderable',False) is False
        assert response.json()['data']['demo'] is True


def test_no_mutation_routes():
    for route in ('bootstrap','markets','merchants','products','serviceability','auth/status'):
        assert client.post('/api/v1/mobile/'+route).status_code==405
