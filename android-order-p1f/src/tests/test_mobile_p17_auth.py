"""Offline JWT authorization contract: mock cryptographic boundary, never mint real JWTs."""
import test_mobile_p1 as base

client, api = base.client, base.api


def test_anonymous_and_malformed_are_401():
    for headers in ({}, {'Authorization':'Basic abc'}, {'Authorization':'Bearer'},
                    {'Authorization':'Bearer aaa bbb'}, {'Authorization':'Bearer '},
                    {'Authorization':'Bearer '+('a'*12020)}):
        r=client.get('/api/v1/mobile/auth/session',headers=headers)
        assert r.status_code==401, (r.status_code,headers)
        assert r.headers['www-authenticate']=='Bearer'
        assert 'Bearer' not in r.text and 'token' not in r.text.lower()


def test_malformed_token_never_bypasses_v5_verifier(monkeypatch):
    touched=[]
    def fail_verify(jwt):
        touched.append(jwt)
        raise api.AuthenticationError('bad signature or issuer')
    monkeypatch.setattr(api,'verify_oidc',fail_verify)
    response=client.get('/api/v1/mobile/auth/session',headers={'Authorization':'Bearer wrong.jwt.payload'})
    assert response.status_code==401
    assert touched==['wrong.jwt.payload']
    assert 'signature' not in response.text


def test_verified_jwt_response_has_no_subject_pii(monkeypatch):
    calls=[]
    def simulate_verified(jwt):
        calls.append(jwt)
        return type('Subject',(),{'sub':'private-neon-user-id','role':'admin','email':'private@example.com'})()
    monkeypatch.setattr(api,'verify_oidc',simulate_verified)
    r=client.get('/api/v1/mobile/auth/session',headers={'Authorization':'Bearer sample.mock.jwt'})
    assert r.status_code==200
    body=r.json()
    assert body['data']['authenticated'] is True
    assert body['data']['checkout_enabled'] is False
    assert 'user' not in r.text and 'admin' not in r.text and 'example.com' not in r.text
    assert calls==['sample.mock.jwt']


def test_session_is_read_only_and_status_is_fail_closed():
    status=client.get('/api/v1/mobile/auth/status')
    assert status.status_code==200
    assert status.json()['data']['login_enabled'] is False
    assert status.json()['data']['oauth_public_client_configured'] is False
    for method in ('post','put','delete','patch'):
        assert getattr(client,method)('/api/v1/mobile/auth/session').status_code==405


def test_existing_read_only_routes_keep_order_disabled():
    r=client.get('/api/v1/mobile/bootstrap')
    data=r.json()['data']
    assert data['checkout_enabled'] is False and data['payment_enabled'] is False
    assert client.post('/api/v1/mobile/payments/prepare').status_code==404
