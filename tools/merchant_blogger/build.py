#!/usr/bin/env python3
"""Build portable Blogger post, theme, CSV and manifest from merchant JSON. No Google account writes."""
import argparse,csv,html,json,re
from pathlib import Path
from collections import defaultdict
from urllib.parse import quote
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
FRONT=ROOT/'storefront'
MERCHANTS=('ilwol-susan','yonggi-susan')
def escape(x):return html.escape(str(x),quote=True)
def image_link(path,origin):
    if not path or '://' in path or path.startswith(('/', '\\','..')):raise ValueError('Unsupported image path '+str(path))
    return origin.rstrip('/')+'/'+path
def normalized(source):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',source.get('id','')):raise ValueError('Invalid merchant id')
    loc=source['location'];phone=source.get('phone') or source.get('contact',{}).get('display') or ''
    menus=[]
    for m in source['menus']:
        assert isinstance(m['price'],int) and m['price']>=0 and m.get('id') and m.get('name')
        menus.append(dict(id=m['id'],category=m['category'],name=m['name'],price=m['price'],
                          description=m.get('description',''),image=m.get('image') or m.get('representativeImage'),
                          screenshot=m.get('sourceScreenshot','')))
    if len(set(x['id'] for x in menus))!=len(menus):raise ValueError('Duplicate IDs')
    images=source.get('images',{})
    if source['id'] not in MERCHANTS and not images.get('storefront'):
        raise ValueError('New merchants require a verified storefront image path')
    return dict(id=source['id'],name=source['name'],phone=phone,address=loc.get('address') or source.get('address'),
                building=loc.get('building','가락몰 판매동'),floor=loc.get('floor','1F'),
                unit=loc.get('unit','확인 필요'),unit_unverified=loc.get('unitStatus')=='external_listing_not_field_verified',
                phone_unverified=not bool(source.get('phoneSource')),
                hero=images.get('signature') or images.get('storefront') or 'assets/merchant/ilwol-susan-storefront.webp',
                storefront=images.get('storefront') or 'assets/merchant/ilwol-susan-storefront.webp',
                categories=source.get('categoryOrder') or source.get('groupOrder') or [],menus=menus)
def build_post(m,origin):
    groups=defaultdict(list)
    for row in m['menus']:groups[row['category']].append(row)
    categories=list(dict.fromkeys(m['categories']+[x['category'] for x in m['menus']]))
    cards=[]
    for cat in categories:
        if cat not in groups:continue
        cards.append('<h2 style="color:#126651;margin:29px 0 10px">'+escape(cat)+'</h2>')
        for item in groups[cat]:
            image=image_link(item['image'] or m['hero'],origin)
            cards.append('<div style="border-bottom:1px solid #e0e9e4;padding:15px 0;display:flex;align-items:center;gap:12px">'
                         '<img style="width:92px;height:92px;object-fit:cover;border-radius:10px" src="'+escape(image)+'" alt="'+escape(item['name'])+' 메뉴 참고 이미지" />'
                         '<div style="flex:1;min-width:0"><b>'+escape(item['name'])+'</b>'
                         '<p style="font-size:12px;color:#627d74">'+escape(item['description'])+'</p>'
                         '<small style="font-size:11px;color:#889b92">메뉴 캡처 참고 이미지</small></div>'
                         '<strong style="white-space:nowrap;color:#087c55">'+f"{item['price']:,}"+'원</strong></div>')
    phone='<a href="tel:'+escape(m['phone'].replace('-',''))+'" style="color:#baf1d4">'+escape(m['phone'])+'</a>' if m['phone'] else '전화번호 확인 필요'
    place_note='외부 등록 기준 · 현장 호수 재확인 필요' if m['unit_unverified'] else '매장 위치 방문 전 재확인'
    contact_note='전화번호 외부 등록 정보 기준 · 재확인 필요' if m['phone_unverified'] else '현장 간판 사진상 전화번호 확인'
    return ('<!-- Blogger 글 편집기 HTML 보기용, 자동 게시되지 않음 -->'
      '<article lang="ko" style="max-width:900px;margin:auto;font-family:Malgun Gothic,sans-serif;line-height:1.8;color:#183c35">'
      '<small style="font-weight:800;color:#0e8361">GARAK MARKET · MERCHANT STORY</small>'
      '<h1 style="font-size:36px;line-height:1.25">'+escape(m['name'])+' 가락몰 메뉴판 · 제철 수산 안내</h1>'
      '<p>가락몰 '+escape(m['building'])+'의 '+escape(m['name'])+'을 소개합니다. 현장과 메뉴 사진을 바탕으로 정리했습니다.</p>'
      '<img src="'+escape(image_link(m['hero'],origin))+'" alt="'+escape(m['name'])+' 회 메뉴 참고 사진" style="display:block;width:100%;height:auto;border-radius:15px" />'
      '<p style="font-size:11px;color:#798c85">제공 화면의 참고 사진이며 실제 판매 메뉴 구성은 달라질 수 있습니다.</p>'
      '<div style="background:#0b3a30;color:white;border-radius:16px;padding:23px;margin:25px 0"><h2 style="color:white">찾아오시는 길</h2>'
      '<p>'+escape(m['address'])+' · '+escape(m['building'])+' '+escape(m['floor'])+' '+escape(m['unit'])+' ('+place_note+')</p>'
      '<p>'+phone+' <small>'+contact_note+'</small></p></div>'
      '<img src="'+escape(image_link(m['storefront'],origin))+'" alt="'+escape(m['name'])+' 현장 매장 사진" style="width:100%;height:auto;border-radius:12px" />'
      '<h2>'+escape(m['name'])+' 메뉴 '+str(len(m['menus']))+'가지</h2>'
      '<p style="background:#fff7e1;border:1px solid #e8d8af;border-radius:9px;padding:14px;font-size:13px">'
      '사진 당시 참고 가격입니다. 현재 판매가·영업·수급·리뷰혜택·할인 여부는 매장 확인이 필요합니다. 실제 주문·결제 기능은 제공하지 않습니다.</p>'
      +''.join(cards)+
      '<p style="margin:33px 0"><a href="'+escape(origin.rstrip('/')+'/'+m['id']+'.html')+'" style="display:inline-block;background:#087953;color:white;border-radius:9px;padding:12px 20px;font-weight:800">가락한상 상세 메뉴판 보기 ↗</a></p>'
      '<p style="font-size:11px;color:#748e80">매장의 게시 승인 및 사진 권리를 확인한 후 공개 발행하세요. Google의 공식 제휴 또는 검색 순위 보장 서비스가 아닙니다.</p></article>')
def build_theme(m,origin):
    src=(FRONT/'blogger/yonggi-susan-theme-draft.xml').read_text()
    src=src.replace('용기수산',escape(m['name']))
    src=src.replace('yonggi-susan.html',escape(m['id'])+'.html')
    src=src.replace('assets/merchant/yonggi-susan-storefront.webp',escape(m['storefront']))
    src=src.replace('24가지',str(len(m['menus']))+'가지')
    src=src.replace('010-3233-3695',escape(m['phone'] or '전화 확인 필요'))
    src=src.replace('01032333695',escape(m['phone'].replace('-','')))
    src=src.replace('C-28호는 외부등록 기준 확인 필요',escape(m['unit'])+' · 정확한 위치 방문 전 확인')
    if m['id']=='ilwol-susan':
        src=src.replace('활어회 · 모둠회 · 오마카세 · 계절 수산 정보','가락몰 수산 · 제철 회 · 메뉴 안내')
    ET.fromstring(src)
    return src
def build(merchant,out,origin,source_json=None):
    src=Path(source_json) if source_json else FRONT/'merchant'/ (merchant+'.json')
    m=normalized(json.loads(src.read_text(encoding='utf-8')))
    out.mkdir(parents=True,exist_ok=True)
    (out/'post.html').write_text(build_post(m,origin),encoding='utf-8')
    (out/'theme.xml').write_text(build_theme(m,origin),encoding='utf-8')
    with (out/'menus.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['메뉴명','카테고리','캡처 당시 참고가격(원)','출처 사진','상태'])
        for item in m['menus']:w.writerow([item['name'],item['category'],item['price'],item['screenshot'],'현재 가격 재확인 필요'])
    manifest=dict(merchant_id=m['id'],name=m['name'],menus=len(m['menus']),website=origin.rstrip('/')+'/'+m['id']+'.html',
                  unit_requires_verification=m['unit_unverified'],phone_requires_verification=m['phone_unverified'],
                  blogger_published=False,blogger_theme_applied=False,merchant_approval=False,images_rights_approved=False)
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'README.md').write_text('# '+m['name']+' Blogger 판매용 패키지\n\n'
        '1. 상인에게 메뉴 가격, 점포 호수, 전화번호, 사진 사용과 게시 동의를 받아 검수합니다.\n'
        '2. Blogger 운영자가 자기 소유 Google 계정에서 블로그를 개설합니다.\n'
        '3. Blogger 테마에서 기존 설정을 백업하고 theme.xml을 복원/HTML 편집합니다.\n'
        '4. 새 글에서 HTML 보기로 바꾸고 post.html 소스를 붙여넣습니다.\n'
        '5. 미리보기와 링크 확인 후 승인받아 게시하고 메뉴 변경시 수정합니다.\n'
        '6. 이미지 경로는 가락몰 사이트에 의존합니다. 장기 사용시 Blogger로 자체 업로드하세요.\n'
        '7. Google 검색 순위, 현재 판매가격, 배달·결제·제휴 여부를 보장하지 않습니다.\n\n'
        '이 도구는 파일만 생성하며 게시/테마 적용은 수행하지 않습니다.\n',encoding='utf-8')
    return manifest
def main():
    p=argparse.ArgumentParser();p.add_argument('--merchant',required=True)
    p.add_argument('--out');p.add_argument('--origin',default='https://garakmall.lexid.site')
    p.add_argument('--source-json',help='External merchant JSON file for a new seller')
    a=p.parse_args();out=Path(a.out) if a.out else ROOT/'dist/blogger'/a.merchant
    info=build(a.merchant,out,a.origin,source_json=a.source_json)
    if info['merchant_id']!=a.merchant: raise ValueError('Merchant ID mismatch with source JSON')
    print(json.dumps(info,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
