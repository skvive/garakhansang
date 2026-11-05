from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'app/src/main/java/site/lexid/garakhansang/order/MainActivity.java').read_text()
CLIENT=(ROOT/'app/src/main/java/site/lexid/garakhansang/order/MobileApiClient.java').read_text()
BUILD=(ROOT/'app/build.gradle.kts').read_text()
CAT=json.loads((ROOT/'catalog/menus_47.json').read_text())['items']

def test_version_and_safe_catalog():
    assert 'versionCode = 21' in BUILD
    assert len(CAT)==47 and all(x['is_orderable'] is False for x in CAT)

def test_accessibility_native_controls_and_touch_size():
    assert SRC.count('Button b=new Button(this)')==2
    assert SRC.count('b.setMinHeight(d(48))')==2
    assert 'productTop.addView(favorite,lp(-2,48))' in SRC
    assert 'details.addView(add,lp(-1,48))' in SRC
    assert 'root.addView(card,lp(-1,180))' in SRC
    assert 'segment.setContentDescription(item[1]+" 탭")' in SRC

def test_search_reset_and_bounded_input():
    assert 'if(!category.equals(kind))query=""' in SRC
    assert 'category=kind;query="";open("products")' in SRC
    assert 'CatalogFilters.matches(' in SRC
    assert 'InputFilter.LengthFilter(80)' in SRC

def test_error_state_and_request_race():
    assert '++remoteRequestSerial; ++addressRequestSerial; ++authRequestSerial; ++apiRequestSerial' in SRC
    for tag in ('address','auth','api','remote'):
        assert f'requestId!={tag}RequestSerial' in SRC
    assert 'isDestroyed()' in SRC

def test_sanitized_catalog_api_presentation():
    assert 'Character.isISOControl(c)' in SRC
    assert 'safeRemoteText(item.optString("name"' in SRC
    assert 'HttpResponseGuards.isStrictJson(contentType)' in CLIENT

def test_no_live_order_api_or_oauth_autostart():
    assert '주문·결제 기능 준비 중' in SRC
    assert 'OAuthTokenHttp' not in SRC
    assert 'setRequestMethod("GET")' in CLIENT
