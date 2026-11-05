#!/usr/bin/env python3
"""Native Android smoke via adb: install, launch, navigate by UI text, capture evidence.

Requires running emulator and real debug APK; no mock success path.
No login, payment or real orders are triggered.
"""
import argparse
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

PACKAGE='site.lexid.garakhansang.order'
ACTIVITY=PACKAGE+'/.MainActivity'


def center_of_bounds(bounds):
    m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',bounds)
    if not m:raise ValueError('No usable Android UI bounds')
    x1,y1,x2,y2=map(int,m.groups())
    if x2<=x1 or y2<=y1:raise ValueError('Invalid Android UI bounds')
    return (x1+x2)//2,(y1+y2)//2


def locate_text(xml_data:str, text:str):
    root=ET.fromstring(xml_data)
    for n in root.iter('node'):
        if n.get('text','')==text and n.get('bounds'):
            return center_of_bounds(n.attrib['bounds'])
    raise ValueError('UI control missing: '+text)


def adb(*args, output=False):
    r=subprocess.run(['adb',*args],capture_output=True,check=True)
    return r.stdout.decode('utf-8',errors='replace') if output else None


def xml_dump():
    adb('shell','uiautomator','dump','/sdcard/window.xml')
    return adb('shell','cat','/sdcard/window.xml',output=True)


def snapshot(name:str,destination:Path):
    output=destination/f'{name}.png'
    with output.open('wb') as f:
        p=subprocess.run(['adb','exec-out','screencap','-p'],stdout=f,check=True)
    if output.stat().st_size<3000:
        raise RuntimeError('Empty Android screenshot')


def run(apk:Path,destination:Path):
    if not apk.is_file():raise FileNotFoundError(apk)
    destination.mkdir(parents=True,exist_ok=True)
    adb('install','-r',str(apk))
    adb('shell','am','force-stop',PACKAGE)
    adb('shell','am','start','-W','-n',ACTIVITY)
    time.sleep(3)
    if not adb('shell','pidof',PACKAGE,output=True).strip():
        raise RuntimeError('APK process did not remain alive after launch')
    xml=xml_dump()
    if '가락한상' not in xml:
        raise RuntimeError('Garak Hansang branded activity was not rendered')
    (destination/'home.xml').write_text(xml)
    snapshot('home',destination)
    for label,filename,expected in [
        ('메뉴','products','메뉴'),
        ('장바구니','cart','장바구니'),
        ('주문내역','orders','주문내역'),
        ('마이','my','마이')]:
        xy=locate_text(xml,label)
        adb('shell','input','tap',str(xy[0]),str(xy[1]))
        time.sleep(1)
        xml=xml_dump()
        if expected not in xml:raise RuntimeError('Navigation not rendered: '+label)
        (destination/(filename+'.xml')).write_text(xml)
        snapshot(filename,destination)
    print('Native Android smoke: installed, launched and navigated 4 tabs; screenshots saved.')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--apk',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    run(a.apk,a.out)

if __name__=='__main__':main()
