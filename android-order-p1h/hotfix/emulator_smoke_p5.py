#!/usr/bin/env python3
"""P5 Android *real UI* smoke: verified merchant tab, demo product detail and cart,
orders + delivery tracking, 5 bottom tabs. Never fakes a paid order.
Original P1J smoke is preserved; imports its checked adb/XML/screenshot helpers.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path
import emulator_smoke_p1j as original

P='site.lexid.garakhansang.order.lab'
original.P=P
SCREENS=[
 ('home','가락한상'),
 ('products','공식 입점 상품'),
 ('cart','장바구니'),
 ('orders','주문 조회'),
 ('my','마이 가락한상')
]
TABS=['홈','메뉴','장바구니','주문내역','마이']


def tap_label(output, target, *, scroll=True):
    observed=[]
    for attempt in range(9):
        ret,_=original.adb('shell','uiautomator','dump','/sdcard/window.xml',check=False)
        if ret:continue
        _,xml=original.adb('shell','cat','/sdcard/window.xml')
        nodes=original.nodes(xml)
        point=next((original.middle(bounds) for text,desc,bounds in nodes
                   if (target in text or target in desc) and original.middle(bounds)),None)
        if point:
            original.adb('shell','input','tap',str(point[0]),str(point[1]))
            return
        observed.append(target)
        if scroll:
            original.adb('shell','input','swipe','510','1710','510','700','330')
        time.sleep(1)
    raise RuntimeError('P5 native UI button not clickable: '+repr(target)+' (retried '+str(len(observed))+')')


def run(apk,out):
    out.mkdir(parents=True,exist_ok=True)
    state={}
    try:
        if not apk.is_file() or apk.stat().st_size<50000:
            raise RuntimeError('Native APK missing')
        _,state['install']=original.adb('install','-r',str(apk))
        original.adb('shell','am','force-stop',P)
        _,state['launch']=original.adb('shell','am','start','-W','-n',
                                      P+'/site.lexid.garakhansang.order.MainActivity')
        previous=None
        for index,(name,label) in enumerate(SCREENS):
            if index>0:
                nav=TABS[index]
                point=next((original.middle(bounds) for t,d,bounds in previous
                            if (t==nav or d==nav+' 탭') and original.middle(bounds)),None)
                if not point:raise RuntimeError('Bottom navigation missing '+nav)
                original.adb('shell','input','tap',str(point[0]),str(point[1]))
            previous=original.screen(out,name,label)
            state[name]='PASS: '+label
            if name=='products':
                # This is an approved-only live catalog, empty while all SKUs pending.
                # Access the original, clearly labelled demo menu *separately*
                # to assert item detail -> quantity -> preview cart still works.
                tap_label(out,'시연 메뉴 47종 둘러보기')
                original.screen(out,'demo_products','시연 메뉴 탐색')
                tap_label(out,'오늘의 한상 (1인)')
                detail=original.screen(out,'demo_detail','상품 상세')
                if not any('수량 선택' in t for t,d,b in detail):
                    raise RuntimeError('Demo item quantity stepper missing')
                tap_label(out,'장바구니 담기')
                original.screen(out,'demo_add_to_cart','선택 수량 1개')
                state['demo_detail_cart']='PASS: demo product detail, quantity and cart'
            if name=='orders':
                tap_label(out,'배송 조회')
                original.screen(out,'delivery_status','배송 조회')
                state['delivery']='PASS: private order/tracking screen without leaking real data'
        print('P5 PASS: actual Android verified menu, demo item, cart, orders, delivery, 5 tabs')
    finally:
        (out/'status-p5.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
        _,log=original.adb('logcat','-d','-v','brief','-t','800',check=False)
        (out/'logcat-p5.txt').write_text(log[-160000:],encoding='utf-8')


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--apk',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    run(a.apk,a.out)
