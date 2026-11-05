#!/usr/bin/env python3
"""P1c static gates for v1.7. APK/emulator and real Neon E2E are separately required."""
from collections import Counter
from pathlib import Path
from PIL import Image
import json,re,subprocess,sys,tempfile

ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'app/src/main/java/site/lexid/garakhansang/order/MainActivity.java').read_text()
CLIENT=(ROOT/'app/src/main/java/site/lexid/garakhansang/order/MobileApiClient.java').read_text()
SERVER=(ROOT/'integrations/v5/mobile_api_p1.py').read_text()
CONF=json.loads((ROOT/'app/src/main/assets/mobile_api_config.json').read_text())
MAN=(ROOT/'app/src/main/AndroidManifest.xml').read_text()
BUILD=(ROOT/'app/build.gradle.kts').read_text()
CAT=json.loads((ROOT/'catalog/menus_47.json').read_text())
entries=CAT['items'];checks={}
def check(name,condition):checks[name]='PASS' if condition else 'FAIL'
def arr_strings(name):
    m=re.search(r'private final String\[\] '+name+r'\s*=\s*\{(.*?)\};',SRC,re.S)
    if not m:return []
    return [json.loads(x) for x in re.findall(r'"(?:\\.|[^"\\])*"',m[1])]
def arr_ints(name):
    m=re.search(r'private final int\[\] '+name+r'\s*=\s*\{(.*?)\};',SRC,re.S)
    return [int(x) for x in re.findall(r'\d+',m[1])] if m else []

names=arr_strings('names');cats=arr_strings('catalogCategories');prices=arr_ints('prices')
check('catalog_rows_47',len(entries)==len(names)==len(cats)==len(prices)==47)
check('catalog_names_prices_unchanged',all((i['name'],i['category'],i['price_krw'])==(n,c,p) for i,n,c,p in zip(entries,names,cats,prices)))
check('catalog_ids_unique',len({i['id'] for i in entries})==47)
check('catalog_categories_12',len(set(cats))==12)
check('all_products_not_orderable',all(i.get('is_orderable') is False and i.get('catalog_visibility')=='needs_merchandising_approval' for i in entries))
check('all_images_concept',all(i.get('image_is_ai_concept') is True for i in entries))
valid=0
for item in entries:
    try:
        with Image.open(ROOT/'app/src/main/assets'/item['image']) as im:im.verify()
        valid+=1
    except (OSError,ValueError):pass
check('all_47_images_readable',valid==47)
check('v17_version', 'versionCode = 17' in BUILD and '1.7.0-p1c-auth-gate' in BUILD)
check('internet_permission_only', 'android.permission.INTERNET' in MAN and 'android.permission.ACCESS_FINE_LOCATION' not in MAN and 'android.permission.ACCESS_COARSE_LOCATION' not in MAN)
check('cleartext_off', 'android:usesCleartextTraffic="false"' in MAN)
check('backup_off', 'android:allowBackup="false"' in MAN)
check('api_disabled_by_default',CONF.get('enabled') is False and CONF.get('base_url')=='' and CONF.get('allowed_hosts')==[])
check('https_host_allowlist',all(x in CLIENT for x in ['"https".equalsIgnoreCase(parsed.getScheme())','getRawUserInfo()','getRawQuery()','getRawFragment()','allowed_hosts']))
check('fixed_get_only', 'setRequestMethod("GET")' in CLIENT and 'setRequestMethod("POST")' not in CLIENT and 'setInstanceFollowRedirects(false)' in CLIENT)
check('no_network_on_launch','mobileApi = new MobileApiClient(this);' in SRC and 'private void apiRequest' in SRC and 'mobileApi.bootstrap(callback)' in SRC and 'mobileApi.bootstrap(' not in SRC.split('private void apiRequest')[0])
check('postal_code_local_only', 'postal.getText().toString()' in SRC and 'InputFilter.LengthFilter(5)' in SRC and 'putString("postal' not in SRC)
check('no_persistent_tokens_or_secrets', 'client_secret' not in CLIENT and 'prefs.edit().putString' not in CLIENT and 'Authorization' not in SRC and 'Bearer ' not in SRC)
check('pkce_disabled_by_default',CONF.get('oauth_enabled') is False and 'oauth' not in MAN.lower())
check('jwt_verification_endpoint', 'verify_oidc(parts[1])' in SERVER and '@router.get("/auth/session")' in SERVER)
check('session_no_pii_response', '"authenticated": True' in SERVER and '"checkout_enabled": False' in SERVER and '"user_id"' not in SERVER and '"subject":' not in SERVER)
check('ephemeral_bearer_only', 'verifySession(String accessToken' in CLIENT and 'setRequestProperty("Authorization","Bearer "+ephemeralBearer)' in CLIENT)
check('login_unavailable_ui', 'case "auth_preview":' in SRC and 'Google 로그인 준비 상태 (P1C)' in SRC)
check('no_implicit_login', 'startActivity(new Intent(Intent.ACTION_VIEW' not in SRC and 'signInWithCredential' not in SRC)
PKCE=(ROOT/'app/src/main/java/site/lexid/garakhansang/order/OAuthPkce.java').read_text()
check('pkce_secure_defaults',all(x in PKCE for x in ['SecureRandom','SHA-256','code_challenge_method=S256','state=','AtomicBoolean','consumeCallback','https']))
check('pkce_no_secret_or_webview', 'client_secret' not in PKCE and 'WebView' not in SRC+CLIENT)
check('api_endpoint_contract',all('/api/v1/mobile/'+x in CLIENT for x in ['bootstrap','markets','merchants','products','serviceability','auth/status','auth/session']))
check('api_backed_by_v5_repository', 'from backend import repository_v5 as repo' in SERVER and 'repo.open_catalog_db()' in SERVER)
check('server_delivery_false','"serviceable": False' in SERVER and '"fee_krw": None' in SERVER)
check('server_checkout_false', '"checkout_enabled": False' in SERVER and '"payment_enabled": False' in SERVER and '"delivery_dispatch_enabled": False' in SERVER)
check('no_real_order_api','@router.post' not in SERVER and 'HttpURLConnection' not in SRC and '주문·결제 기능 준비 중' in SRC)
check('new_ui_screens', all('case "'+x+'"' in SRC for x in ['address','api','checkout','orders']))
check('app_keeps_original_brand',all((ROOT/'app/src/main/assets'/x).exists() for x in ['garakhansang_official_logo.webp','order_brand_512.webp']))
check('api_read_only_db_role', 'gho.merchants m' not in SERVER and 'repo.catalog(db, market_id)' in SERVER)
check('market_to_merchant_to_product_ui',all(x in SRC for x in ['case "remote_catalog":', 'loadRemoteMarkets(', 'loadRemoteMerchants(', 'loadRemoteProducts(', 'selectedRemoteMarketId']))
check('remote_no_cart_binding','cart[' not in SRC[SRC.index('private void remoteCatalogPage()'):SRC.index('private void infoCell(')])
check('remote_no_orderable_flag', 'item.optBoolean("orderable"' not in SRC)
check('request_race_guard','remoteRequestSerial' in SRC and SRC.count('requestId!=remoteRequestSerial')==3)
check('encoded_query_filters',all(x in CLIENT for x in ['URLEncoder.encode(text, "UTF-8")', 'validMarketId(marketId)', 'merchant_name=', 'market_id=']))
check('minimum_android_api_compat', 'isBlank()' not in SRC+CLIENT and 'URLEncoder.encode(text, StandardCharsets.UTF_8)' not in CLIENT)
check('server_filter_exact', 'row["merchant_name"] == merchant_name' in SERVER and '_checked_market(market_id)' in SERVER)
check('server_no_write_routes','@router.post' not in SERVER and '@router.put' not in SERVER and '@router.delete' not in SERVER)

with tempfile.TemporaryDirectory(prefix='garak-javac-') as tmp:
    srcs=[str(x) for x in (ROOT/'app/src/main/java').rglob('*.java')]
    compiled=subprocess.run(['javac','-d',tmp,str(ROOT/'tools/JavaSyntaxGate.java')],capture_output=True,text=True)
    parsed=subprocess.run(['java','-cp',tmp,'JavaSyntaxGate']+srcs,capture_output=True,text=True) if compiled.returncode==0 else compiled
    check('java17_parser',compiled.returncode==0 and parsed.returncode==0)

out={'project':'Garak Hansang Order Android v1.7 P1c authentication gate','scope':'offline source + Python contract QA, not APK or Neon E2E','menus':len(entries),'verified_images':valid,'checks':checks,'passed':sum(v=='PASS' for v in checks.values()),'total':len(checks),'limitations':['Android SDK/Gradle unavailable: APK not built','Neon live database untouched: no remote E2E','HTTPS host and OAuth disabled by default; no production API calls','Neon OAuth Provider disabled (main only), no public client/App Link verified; login disabled']}
(ROOT/'docs/QA_V1_7_P1C.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(f"Static QA: {out['passed']}/{out['total']} passed. Java 17 syntax, images: {valid}/47")
for k,v in checks.items():print(v,k)
sys.exit(0 if out['passed']==out['total'] else 1)
