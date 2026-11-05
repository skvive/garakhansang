#!/usr/bin/env python3
"""P1E offline invariant verification. Cannot certify a build or a live OAuth login."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
JAVA=ROOT/'app/src/main/java/site/lexid/garakhansang/order'
CAT=json.loads((ROOT/'catalog/menus_47.json').read_text(encoding='utf-8'))
MAIN=(JAVA/'MainActivity.java').read_text(encoding='utf-8')
CLIENT=(JAVA/'MobileApiClient.java').read_text(encoding='utf-8')
MAN=(ROOT/'app/src/main/AndroidManifest.xml').read_text(encoding='utf-8')
BUILD=(ROOT/'app/build.gradle.kts').read_text(encoding='utf-8')
CONF=json.loads((ROOT/'app/src/main/assets/mobile_api_config.json').read_text(encoding='utf-8'))
LOGIN=(JAVA/'OAuthLoginFlow.java').read_text(encoding='utf-8')
PKCE=(JAVA/'OAuthPkce.java').read_text(encoding='utf-8')
EXCHANGE=(JAVA/'OAuthCodeExchange.java').read_text(encoding='utf-8')
TOKEN=(JAVA/'OAuthTokenHttp.java').read_text(encoding='utf-8')
API=(ROOT/'integrations/v5/mobile_api_p1.py').read_text(encoding='utf-8')
WORKFLOW=(ROOT/'.github/workflows/order-android-ci.yml').read_text(encoding='utf-8')
CHECKS={}

def check(name,ok):CHECKS[name]='PASS' if ok else 'FAIL'
def parse_java_string_array(field):
    match=re.search(r'private final String\[\] '+field+r'\s*=\s*\{(.*?)\};',MAIN,re.S)
    return [json.loads(x) for x in re.findall(r'"(?:\\.|[^"\\])*"',match.group(1))] if match else []
def parse_java_int_array(field):
    match=re.search(r'private final int\[\] '+field+r'\s*=\s*\{(.*?)\};',MAIN,re.S)
    return [int(x) for x in re.findall(r'\d+',match.group(1))] if match else []

items=CAT['items'];names=parse_java_string_array('names');categories=parse_java_string_array('catalogCategories');prices=parse_java_int_array('prices')
check('47_products_match_java',len(items)==len(names)==len(prices)==len(categories)==47 and all((m['name'],m['category'],m['price_krw'])==(name,c,p) for m,name,c,p in zip(items,names,categories,prices)))
check('12_categories',len(set(categories))==12)
check('unique_product_ids',len(set(x['id'] for x in items))==47)
check('products_not_published',all(x.get('catalog_visibility')=='needs_merchandising_approval' and x.get('is_orderable') is False and x.get('image_is_ai_concept') is True for x in items))
valid_images=0
for item in items:
    try:
        with Image.open(ROOT/'app/src/main/assets'/item['image']) as image:
            image.verify()
        valid_images+=1
    except (OSError,ValueError,KeyError): pass
check('47_real_image_decodes',valid_images==47)
check('official_brand_assets',all((ROOT/'app/src/main/assets'/p).is_file() for p in ['garakhansang_official_logo.webp','order_brand_512.webp']))
check('v19_version', 'versionCode = 19' in BUILD and '1.9.0-p1e-ci-gate' in BUILD)
check('no_cleartext', 'android:usesCleartextTraffic="false"' in MAN)
check('no_external_backup','android:allowBackup="false"' in MAN)
check('internet_only', 'android.permission.INTERNET' in MAN and 'android.permission.ACCESS_FINE_LOCATION' not in MAN)
check('no_unverified_app_link','android.intent.action.VIEW' not in MAN and 'android:autoVerify' not in MAN)
check('api_disabled',CONF.get('enabled') is False and CONF.get('base_url')=='' and CONF.get('allowed_hosts')==[])
check('oauth_disabled',CONF.get('oauth_enabled') is False)
check('one_time_pkce','AtomicBoolean' in PKCE and 'SecureRandom' in PKCE and 'code_challenge_method=S256' in PKCE)
check('login_readiness_all_required',all(s in LOGIN for s in ['verifiedAppLink && registeredPublicClient && devAuthReady','!config.isReady()','OAuthPkce.begin','OAuthCodeExchange.prepare','cancel(); // always consume']))
check('login_no_persistence',all(s not in LOGIN for s in ['SharedPreferences','client_secret','WebView','KeyStore','Intent.ACTION_VIEW']))
check('oauth_callback_no_webview','WebView' not in MAIN+LOGIN+CLIENT)
check('token_post_only',all(s in TOKEN for s in ['HttpsURLConnection','setRequestMethod("POST")','setInstanceFollowRedirects(false)','setRequestProperty("Cache-Control","no-store")']))
check('token_no_secret','client_secret=' not in TOKEN+EXCHANGE and 'SharedPreferences' not in TOKEN+EXCHANGE)
check('no_login_ui_connection','OAuthLoginFlow' not in MAIN and 'OAuthTokenHttp' not in MAIN and 'startActivity(new Intent(Intent.ACTION_VIEW' not in MAIN)
check('api_get_only', 'setRequestMethod("GET")' in CLIENT and 'setRequestMethod("POST")' not in CLIENT)
check('api_verified_jwt', 'verify_oidc(parts[1])' in API and '@router.get("/auth/session")' in API)
check('no_checkout_server', all(s in API for s in ['"checkout_enabled": False','"payment_enabled": False','"delivery_dispatch_enabled": False']) and '@router.post' not in API)
check('no_real_order', '주문·결제 기능 준비 중' in MAIN)
check('debug_apk_verify_script',(ROOT/'tools/verify_debug_apk.py').is_file())
check('emulator_smoke_script',(ROOT/'tools/emulator_smoke.py').is_file())
check('ci_uses_real_apk_check','--apksigner' in WORKFLOW and 'verify_debug_apk.py' in WORKFLOW and ':app:assembleDebug' in WORKFLOW)
check('ci_emulator_not_ignored','continue-on-error: true' not in WORKFLOW and 'emulator_smoke.py' in WORKFLOW)
check('ci_test_p1e','OAuthLoginFlowSelfTest' in WORKFLOW and 'test_mobile_p19_apk_gate.py' in WORKFLOW)
check('not_storing_private_signing_keys',not any(p.suffix in ('.keystore','.jks','.p12','.pem') for p in ROOT.rglob('*') if p.is_file()))
check('source_documents_exist',all((ROOT/'docs'/x).is_file() for x in ['ANDROID_APP_LINK_P1D_KO.md','ANDROID_ORDER_PRODUCT_SPEC_V1_3_KO.md']))

with tempfile.TemporaryDirectory(prefix='gho-p1e-parse-') as tmp:
    compiler=subprocess.run(['javac','-d',tmp,str(ROOT/'tools/JavaSyntaxGate.java')],text=True,capture_output=True)
    parsed=subprocess.run(['java','-cp',tmp,'JavaSyntaxGate']+[str(p) for p in JAVA.glob('*.java')],text=True,capture_output=True) if compiler.returncode==0 else compiler
    check('java17_syntax_parser',parsed.returncode==0)

output={'version':'1.9.0-p1e-ci-gate','scope':'Static, offline Java parser and local catalog/media validation; NOT a real APK, Google login or verified App Link','checks':CHECKS,'total':len(CHECKS),'passed':sum(v=='PASS' for v in CHECKS.values()),'47_images_verified':valid_images,'apk_built':False,'neon_oauth_e2e':False,'google_login_enabled':False}
(ROOT/'docs/QA_V1_9_P1E.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
for name,result in CHECKS.items():print(result,name)
print('P1E static QA:',output['passed'],'/',output['total'])
sys.exit(0 if output['passed']==output['total'] else 1)
