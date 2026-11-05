import importlib.util
from pathlib import Path
import pytest

source=Path(__file__).resolve().parents[1]/'tools/verify_debug_apk.py'
spec=importlib.util.spec_from_file_location('verify_p1e_apk',source)
apk=importlib.util.module_from_spec(spec)
spec.loader.exec_module(apk)

BADGING="""package: name='site.lexid.garakhansang.order' versionCode='19' versionName='1.9.0-p1e-ci-gate'
sdkVersion:'26'
targetSdkVersion:'36'
"""
SIGN="""Verifies
Verified using v1 scheme (JAR signing): false
Verified using v2 scheme (APK Signature Scheme v2): true
Signer #1 certificate SHA-256 digest: 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
"""

def test_realistic_aapt_data():
    d=apk.parse_badging(BADGING)
    assert d['package_name']=='site.lexid.garakhansang.order'
    assert d['version_code']==19
    assert d['target_sdk']==36

def test_realistic_signer_info():
    d=apk.parse_signature(SIGN)
    assert d['signed'] and d['cert_sha256_fingerprint'].count(':')==31

@pytest.mark.parametrize('text',[
    '',BADGING.replace('site.lexid.garakhansang.order','site.lexid.other'),
    BADGING.replace("versionCode='19'","versionCode='18'"),
    BADGING.replace('1.9.0-','1.8.0-'),
    BADGING.replace("sdkVersion:'26'","sdkVersion:'21'"),
    BADGING.replace("targetSdkVersion:'36'","targetSdkVersion:'35'"),
    BADGING.replace("targetSdkVersion:'36'",''),
])
def test_bad_apk_metadata_is_rejected(text):
    with pytest.raises(ValueError):apk.parse_badging(text)

@pytest.mark.parametrize('text',[
    '', SIGN.replace('Verifies','DOES NOT VERIFY'),
    SIGN.replace('certificate SHA-256 digest','certificate SHA-1 digest'),
    SIGN.replace('1234567890abcdef'*4,'F'*63),
    SIGN+'Signer #2 certificate SHA-256 digest: '+('0'*64)+'\n',
])
def test_unverified_signer_is_rejected(text):
    with pytest.raises(ValueError):apk.parse_signature(text)

def test_missing_apk_not_accepted(tmp_path):
    with pytest.raises(ValueError):apk.inspect(tmp_path/'missing.apk','aapt','apksigner')
