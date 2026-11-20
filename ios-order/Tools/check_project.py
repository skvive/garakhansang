#!/usr/bin/env python3
"""Offline safety/assets/Xcode-project gate; does not claim Apple compilation."""
from pathlib import Path
import hashlib, json, plistlib, re, sys
root=Path(__file__).resolve().parent.parent
resources=root/'GarakHansangOrder'/'Assets.xcassets'
catalog=json.loads((root/'Shared'/'Resources'/'menu_catalog.json').read_text(encoding='utf8'))
assert len(catalog['items'])==47
assert len({i['category'] for i in catalog['items']})==12
assert len({i['id'] for i in catalog['items']})==47
assert catalog['not_for_live_sales'] is True
assert all(i['is_orderable'] is False and i['image_is_ai_concept'] is True for i in catalog['items'])
assert all(i['catalog_visibility']=='needs_merchandising_approval' for i in catalog['items'])
for item in catalog['items']:
    name=item['image'].removesuffix('.jpg')
    folder=resources/f'{name}.imageset'
    assert (folder/item['image']).is_file(),name
    assert len((folder/item['image']).read_bytes())>1000
    data=json.loads((folder/'Contents.json').read_text())
    assert data['images'][0]['filename']==item['image']
for name in ['OfficialLogo','FeatureFood']:
    assert (resources/f'{name}.imageset'/f'{name}.png').is_file()
assert (resources/'AppIcon.appiconset'/'AppIcon.png').is_file()
info=plistlib.loads((root/'GarakHansangOrder'/'Info.plist').read_bytes())
assert info['CFBundleDisplayName']=='가락한상 오더'
assert 'NSLocationWhenInUseUsageDescription' not in info
assert 'NSCameraUsageDescription' not in info
assert 'NSAppTransportSecurity' not in info
pbx=(root/'GarakHansangOrder.xcodeproj'/'project.pbxproj').read_text()
assert 'site.lexid.garakhansang.order.ios' in pbx
assert 'IPHONEOS_DEPLOYMENT_TARGET = 16.0' in pbx
assert 'SWIFT_VERSION = 5.0' in pbx
assert 'ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon' in pbx
swiftFiles=list((root/'GarakHansangOrder').rglob('*.swift'))
assert len(swiftFiles)==9
for file in swiftFiles:
    assert file.name in pbx, file
    txt=file.read_text()
    assert txt.count('{')==txt.count('}'), file
    assert not any(x in txt for x in ['URLSession.shared.dataTask','@AppStorage("userToken")','requestWhenInUseAuthorization','import WebKit']),file
app=(root/'GarakHansangOrder'/'Data'/'ShopViewModel.swift').read_text()
assert 'catalog = try CatalogStore.decodeAndValidate(contents)' in app
assert 'search = ""' in app
assert 'var cart = PreviewCart()' in app
assert 'actualOrder' not in app
assert 'CFBundleURLTypes' not in str(info)
print(json.dumps({'static_checks':'PASS','menu_images':47,'categories':12,'swift_ui_files':len(swiftFiles),'actual_sales':False,'login_active':False,'original_catalog_sha256':hashlib.sha256((root/'Shared'/'Resources'/'menu_catalog.json').read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
