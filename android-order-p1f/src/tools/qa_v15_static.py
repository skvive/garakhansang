#!/usr/bin/env python3
"""P1 static gates for v1.5. APK/emulator and real Neon E2E are separately required."""
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
check('v15_version', 'versionCode = 15' in BUILD and '1.5.0-p1-preview' in BUILD)
check('internet_permission_only', 'android.permission.INTERNET' in MAN and 'android.permission.ACCESS_FINE_LOCATION' not in MAN and 'android.permission.ACCESS_COARSE_LOCATION' not in MAN)
check('cleartext_off', 'android:usesCleartextTraffic="false"' in MAN)
check('backup_off', 'android:allowBackup="false"' in MAN)
check('api_disabled_by_default',CONF.get('enabled') is False and CONF.get('base_url')=='' and CONF.get('allowed_hosts')==[])
check('https_host_allowlist',all(x in CLIENT for x in ['"https".equalsIgnoreCase(parsed.getScheme())','getRawUserInfo()','getRawQuery()','getRawFragment()','allowed_hosts']))
check('fixed_get_only', 'setRequestMethod("GET")' in CLIENT and 'setRequestMethod("POST")' not in CLIENT and 'setInstanceFollowRedirects(false)' in CLIENT)
check('no_network_on_launch','mobileApi = new MobileApiClient(this);' in SRC and 'private void apiRequest' in SRC and 'mobileApi.bootstrap(callback)' in SRC and 'mobileApi.bootstrap(' not in SRC.split('private void apiRequest')[0])
check('postal_code_local_only', 'postal.getText().toString()' in SRC and 'InputFilter.LengthFilter(5)' in SRC and 'putString("postal' not in SRC)
check('no_persistent_tokens_or_secrets', 'Authorization' not in CLIENT and 'Bearer ' not in CLIENT and 'client_secret' not in CLIENT)
check('api_endpoint_contract',all('/api/v1/mobile/'+x in CLIENT for x in ['bootstrap','markets','merchants','products','serviceability','auth/status']))
check('api_backed_by_v5_repository', 'from backend import repository_v5 as repo' in SERVER and 'repo.open_catalog_db()' in SERVER)
check('server_delivery_false','"serviceable": False' in SERVER and '"fee_krw": None' in SERVER)
check('server_checkout_false', '"checkout_enabled": False' in SERVER and '"payment_enabled": False' in SERVER and '"delivery_dispatch_enabled": False' in SERVER)
check('no_real_order_api','@router.post' not in SERVER and 'HttpURLConnection' not in SRC and '주문·결제 기능 준비 중' in SRC)
check('new_ui_screens', all('case "'+x+'"' in SRC for x in ['address','api','checkout','orders']))
check('app_keeps_original_brand',all((ROOT/'app/src/main/assets'/x).exists() for x in ['garakhansang_official_logo.webp','order_brand_512.webp']))
check('api_read_only_db_role', 'gho.merchants m' not in SERVER and 'repo.catalog(db, market_id)' in SERVER)

with tempfile.TemporaryDirectory(prefix='garak-javac-') as tmp:
    srcs=[str(x) for x in (ROOT/'app/src/main/java').rglob('*.java')]
    compiled=subprocess.run(['javac','-d',tmp,str(ROOT/'tools/JavaSyntaxGate.java')],capture_output=True,text=True)
    parsed=subprocess.run(['java','-cp',tmp,'JavaSyntaxGate']+srcs,capture_output=True,text=True) if compiled.returncode==0 else compiled
    check('java17_parser',compiled.returncode==0 and parsed.returncode==0)

out={'project':'Garak Hansang Order Android v1.5 P1 preview','scope':'offline source + Python contract QA, not APK or Neon E2E','menus':len(entries),'verified_images':valid,'checks':checks,'passed':sum(v=='PASS' for v in checks.values()),'total':len(checks),'limitations':['Android SDK/Gradle unavailable: APK not built','Neon live database untouched: no remote E2E','HTTPS host disabled by default; no production API calls','Google login, delivery zones and payments unconfigured and disabled']}
(ROOT/'docs/QA_V1_5_P1.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(f"Static QA: {out['passed']}/{out['total']} passed. Java 17 syntax, images: {valid}/47")
for k,v in checks.items():print(v,k)
sys.exit(0 if out['passed']==out['total'] else 1)
