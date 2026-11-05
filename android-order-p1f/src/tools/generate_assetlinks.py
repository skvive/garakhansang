#!/usr/bin/env python3
"""Generate deployment-ready Android Digital Asset Links from a REAL APK certificate fingerprint.

Does not publish, sign APKs, infer host ownership, or enable the manifest intent filter.
Requires caller to verify HTTPS domain ownership and cert fingerprint beforehand.
"""
import argparse
import json
import re
from pathlib import Path

PACKAGE = 'site.lexid.garakhansang.order'


def make_statement(package: str, fingerprint: str):
    if package != PACKAGE:
        raise ValueError('Package must exactly match signed Android applicationId')
    if not re.fullmatch(r'[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){31}', fingerprint):
        raise ValueError('SHA-256 certificate digest requires 32 colon-separated hexadecimal bytes')
    return [{
        'relation': ['delegate_permission/common.handle_all_urls'],
        'target': {
            'namespace': 'android_app',
            'package_name': package,
            'sha256_cert_fingerprints': [fingerprint.upper()],
        },
    }]


def main():
    parser=argparse.ArgumentParser(description='Android Verified App Links deployment statement generator')
    parser.add_argument('--package',default=PACKAGE)
    parser.add_argument('--fingerprint',required=True,help='actual apksigner SHA-256 signing certificate digest (AA:BB:...)')
    parser.add_argument('--out',required=True,help='output path ending assetlinks.json')
    args=parser.parse_args()
    output=Path(args.out)
    if output.name!='assetlinks.json':
        parser.error('Output basename must be exactly assetlinks.json')
    try:
        payload=make_statement(args.package,args.fingerprint)
    except ValueError as e:
        parser.error(str(e))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Created local statement only; NOT uploaded or verified on HTTPS:',output)

if __name__=='__main__':
    main()
