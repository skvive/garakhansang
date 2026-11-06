from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/'app/src/main/java/site/lexid/garakhansang/order'


def test_shared_strict_mime_used_in_both_api_transports():
    for name in ('MobileApiClient.java','OAuthTokenHttp.java'):
        assert 'HttpResponseGuards.isStrictJson(' in (JAVA/name).read_text()
    assert (JAVA/'HttpResponseGuards.java').is_file()


def test_oauth_code_control_characters_rejected():
    assert 'Character.isISOControl(code.charAt(i))' in (JAVA/'OAuthPkce.java').read_text()
    assert 'Character.isISOControl(callback.authorizationCode.charAt(i))' in (JAVA/'OAuthCodeExchange.java').read_text()


def test_signature_scheme_has_independent_gate():
    script=ROOT/'tools/verify_debug_apk.py'
    spec=importlib.util.spec_from_file_location('apk_p1h',script)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    signed="Verifies\nVerified using v1 scheme (JAR signing): true\nVerified using v2 scheme (APK Signature Scheme v2): true\nSigner #1 certificate SHA-256 digest: 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef\n"
    assert m.parse_signature(signed)['signed']
