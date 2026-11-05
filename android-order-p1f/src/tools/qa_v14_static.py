#!/usr/bin/env python3
"""Source-level regression for Android offline demo. Does not replace APK/emulator testing."""
import json, re, pathlib, sys
from collections import Counter
from PIL import Image
ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=(ROOT/'app/src/main/java/site/lexid/garakhansang/order/MainActivity.java').read_text()
MAN=(ROOT/'app/src/main/AndroidManifest.xml').read_text()
GRADLE=(ROOT/'app/build.gradle.kts').read_text()
CAT=json.loads((ROOT/'catalog/menus_47.json').read_text())
items=CAT['items']
checks={}

def ok(name,cond):
    checks[name]={'status':'PASS' if cond else 'FAIL'}

def java_string_array(name):
    m=re.search(r'private final String\[\] '+name+r'\s*=\s*\{(.*?)\};',SRC,re.S)
    assert m, name
    return [json.loads(x) for x in re.findall(r'"(?:\\.|[^"\\])*"',m.group(1))]

def java_int_array(name):
    m=re.search(r'private final int\[\] '+name+r'\s*=\s*\{(.*?)\};',SRC,re.S)
    assert m, name
    return [int(x) for x in re.findall(r'\d+',m.group(1))]

names=java_string_array('names')
prices=java_int_array('prices')
cats=java_string_array('catalogCategories')
ok('47_menu_count',len(items)==47 and len(names)==len(prices)==len(cats)==47)
ok('12_distinct_categories',len(set(cats))==12)
ok('unique_ids',len({i['id'] for i in items})==47)
ok('java_catalog_identity',all(i['name']==n and i['price_krw']==p and i['category']==c for i,n,p,c in zip(items,names,prices,cats)))
ok('all_catalog_requires_approval',all(i['catalog_visibility']=='needs_merchandising_approval' and i['is_orderable'] is False and i['source_visibility_note']=='숨김' for i in items))
ok('every_image_is_ai_concept',all(i['image_is_ai_concept'] is True for i in items))
assetroot=ROOT/'app/src/main/assets'
valid_images=0
for item in items:
    f=assetroot/item['image']
    try:
        with Image.open(f) as im:im.verify()
        valid_images+=1
    except (FileNotFoundError,OSError,ValueError):pass
ok('47_image_assets_decode',valid_images==47)
ok('v14_version', 'versionCode = 14' in GRADLE and 'versionName = "1.4.0-demo"' in GRADLE)
ok('no_network_or_location_permission','android.permission.INTERNET' not in MAN and 'android.permission.ACCESS_' not in MAN)
ok('backup_disabled','android:allowBackup="false"' in MAN)
ok('android_native_not_webview','class MainActivity extends Activity' in SRC and 'WebView' not in SRC)
ok('screen_flows',all(('case "'+x+'"') in SRC for x in ['products','store','cart','checkout','orders','favorites','my']))
ok('demo_region_no_freeform_address',all(s in SRC for s in ['DEMO_AREAS','chooseDemoArea','demo_area_index']) and 'getLastKnownLocation' not in SRC)
ok('fulfillment_switch',all(s in SRC for s in ['chooseFulfillment','"배달"','"포장"']))
ok('checkout_rejects_real_order',all(s in SRC for s in ['주문·결제 기능 준비 중','주문 접수 불가','최종 결제금액", "제공 불가']) and 'HttpURLConnection' not in SRC and 'OkHttp' not in SRC)
ok('thumbnail_cache', 'LruCache<String,Bitmap>' in SRC and 'inSampleSize' in SRC)
summary={'project':'가락한상 오더 Android v1.4.0-demo','scope':'static source checks only','counts':{'menus':len(items),'image_assets_verified':valid_images,'categories':len(set(cats)),'checks':len(checks),'passed':sum(v['status']=='PASS' for v in checks.values())},'checks':checks,'limitations':['Android SDK and Gradle not available in this environment; no APK built','No emulator or real device runtime QA','No real location, authentication, PG, dispatch or external service integration']}
result=ROOT/'docs/QA_V1_4_SOURCE.json';result.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary['counts'],ensure_ascii=False))
for k,v in checks.items():print(v['status'],k)
sys.exit(0 if summary['counts']['passed']==len(checks) else 1)
