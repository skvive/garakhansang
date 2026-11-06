#!/usr/bin/env python3
"""Fail-closed debug APK inspection, not Play release or domain-verification proof.

Requires real aapt and apksigner output from a built APK. Never guesses or
creates APKs, signing keys, Digital Asset Links, or OAuth configuration.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

PACKAGE = 'site.lexid.garakhansang.order'
MIN_SDK = '26'
TARGET_SDK = '36'


def parse_badging(output: str) -> dict:
    match=re.search(r"^package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'",output,re.M)
    min_sdk=re.search(r"^sdkVersion:'(\d+)'$",output,re.M)
    target=re.search(r"^targetSdkVersion:'(\d+)'$",output,re.M)
    if not match or not min_sdk or not target:
        raise ValueError('Missing real aapt package / sdk metadata')
    package, version, version_name = match.groups()
    if package != PACKAGE or min_sdk.group(1) != MIN_SDK or target.group(1) != TARGET_SDK:
        raise ValueError('Unexpected applicationId or Android SDK levels')
    if not version.isdecimal() or int(version)!=21 or not version_name.startswith('1.11.0-'):
        raise ValueError('Not the v1.11 P1H build')
    return {'package_name':package,'version_code':int(version),'version_name':version_name,
            'min_sdk':int(min_sdk.group(1)),'target_sdk':int(target.group(1))}


def parse_signature(output: str) -> dict:
    if not re.search(r'^Verifies\s*$',output,re.M):
        raise ValueError('APK signature has not been verified')
    # Android API 26+ requires a cryptographic APK signing scheme; an output
    # that only says "Verifies" but reports all modern schemes false is invalid.
    v2_or_newer = re.findall(r'^Verified using v(?:2|3|3\.1|4) scheme[^\n:]*:\s*(true|false)\s*$', output, re.M | re.I)
    if not any(value.lower() == 'true' for value in v2_or_newer):
        raise ValueError('APK does not have a verified v2-or-newer signing scheme')
    digests=re.findall(r'Signer #\d+ certificate SHA-256 digest:\s*([0-9a-fA-F]{64})',output)
    if len(digests)!=1:
        raise ValueError('APK must have exactly one verified signing certificate')
    fingerprint=':'.join(digests[0][i:i+2] for i in range(0,64,2)).upper()
    return {'cert_sha256_fingerprint':fingerprint,'signed':True}


def inspect(apk: Path, aapt: str, apksigner: str) -> dict:
    if not apk.is_file() or apk.stat().st_size<10000:
        raise ValueError('Real built APK is missing/too small')
    badging=subprocess.run([aapt,'dump','badging',str(apk)],capture_output=True,text=True,check=True)
    signature=subprocess.run([apksigner,'verify','--verbose','--print-certs',str(apk)],
                             capture_output=True,text=True,check=True)
    package_info=parse_badging(badging.stdout)
    signer_info=parse_signature(signature.stdout)
    h=hashlib.sha256()
    with apk.open('rb') as f:
        for block in iter(lambda:f.read(65536),b''):
            h.update(block)
    return {'apk_sha256':h.hexdigest(),**package_info,**signer_info,
            'e2e_google_login_verified':False,'verified_app_link':False,
            'publish_ready':False,
            'note':'Debug signing certificate alone does not prove HTTPS domain ownership or Google sign-in.'}


def main():
    p=argparse.ArgumentParser(description='Verify actual P1H signed Android debug APK')
    p.add_argument('--apk',required=True,type=Path)
    p.add_argument('--aapt',required=True)
    p.add_argument('--apksigner',required=True)
    p.add_argument('--receipt',required=True,type=Path)
    a=p.parse_args()
    try:
        receipt=inspect(a.apk,a.aapt,a.apksigner)
    except (ValueError,subprocess.CalledProcessError,OSError) as exc:
        p.error('APK verification failed: '+str(exc))
    a.receipt.parent.mkdir(parents=True,exist_ok=True)
    a.receipt.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print('Actual APK signature / package inspected. OAuth and verified App Links remain unverified.')

if __name__=='__main__':main()
