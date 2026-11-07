#!/usr/bin/env python3
"""Fail-closed native emulator smoke with XML/screenshot evidence before UI assertions."""
import argparse,json,re,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
P='site.lexid.garakhansang.order'
SCREENS=[('home','가락한상'),('products','상품 탐색'),('cart','장바구니가 비었습니다'),('orders','아직 주문한 내역이 없습니다'),('my','마이 가락한상')]
TABS=['홈','메뉴','장바구니','주문내역','마이']
def adb(*args,check=True):
 p=subprocess.run(['adb',*args],capture_output=True,timeout=60,check=False)
 out=p.stdout.decode('utf-8','replace')+'\n'+p.stderr.decode('utf-8','replace')
 if check and p.returncode:raise RuntimeError('adb '+str(args)+' '+out[-1000:])
 return p.returncode,out
def nodes(xml):
 return [(n.get('text',''),n.get('content-desc',''),n.get('bounds','')) for n in ET.fromstring(xml).iter('node')]
def middle(b):
 m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',b)
 if not m:return None
 x,y,X,Y=map(int,m.groups())
 return ((x+X)//2,(y+Y)//2) if X>x and Y>y else None
def screen(out,name,expected):
 observed=[]
 for attempt in range(8):
  time.sleep(1.5)
  _,pid=adb('shell','pidof',P,check=False)
  if not pid.strip():
   observed.append('app pid not found')
   continue
  ret,_=adb('shell','uiautomator','dump','/sdcard/window.xml',check=False)
  if ret:
   observed.append('uiautomator dump failed')
   continue
  _,xml=adb('shell','cat','/sdcard/window.xml')
  (out/(name+'.xml')).write_text(xml,encoding='utf-8')
  elements=nodes(xml)
  (out/(name+'-labels.json')).write_text(json.dumps([{'text':t,'description':d,'bounds':b} for t,d,b in elements if t or d],ensure_ascii=False,indent=2),encoding='utf-8')
  with (out/(name+'.png')).open('wb') as f:
   p=subprocess.run(['adb','exec-out','screencap','-p'],stdout=f,check=False)
  if p.returncode or (out/(name+'.png')).stat().st_size<5000:raise RuntimeError('screenshot not captured')
  if any(expected in t or expected in d for t,d,b in elements):return elements
  # Sometimes a just-booted emulator shows a system Pixel Launcher ANR over
  # the perfectly rendered foreground app. Dismiss ONLY that launcher dialog;
  # never suppress crashes or ANRs involving the app under test.
  if any("Pixel Launcher isn't responding" in t for t,d,b in elements):
   position=next((middle(b) for t,d,b in elements if t=="Close app" and middle(b)),None)
   if position:
    observed.append('unrelated Pixel Launcher ANR dismissed')
    adb('shell','input','tap',str(position[0]),str(position[1]))
    continue
  observed.append('missing '+expected+' from '+str(len(elements))+' elements')
 raise RuntimeError('Real screen missing on '+name+': '+str(observed[-4:]))
def run(apk,out):
 out.mkdir(parents=True,exist_ok=True)
 status={}
 try:
  if not apk.is_file() or apk.stat().st_size<50000:raise RuntimeError('APK missing')
  _,status['install']=adb('install','-r',str(apk))
  adb('shell','am','force-stop',P)
  _,status['launch']=adb('shell','am','start','-W','-n',P+'/.MainActivity')
  previous=None
  for i, (name,expected) in enumerate(SCREENS):
   if i:
    label=TABS[i]
    xy=next((middle(b) for t,d,b in previous if (t==label or d==label+' 탭') and middle(b)),None)
    if not xy:raise RuntimeError('Missing accessible navigation '+label)
    adb('shell','input','tap',str(xy[0]),str(xy[1]))
   previous=screen(out,name,expected)
   status[name]='PASS '+expected
  print('Real emulator: APK installed, activity launched, all 5 tabs and screenshots validated')
 finally:
  (out/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
  _,a=adb('shell','dumpsys','activity','activities',check=False)
  (out/'activity.txt').write_text(a[-80000:],encoding='utf-8')
  _,logs=adb('logcat','-d','-v','brief','-t','800',check=False)
  (out/'logcat.txt').write_text(logs[-180000:],encoding='utf-8')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--apk',type=Path,required=True)
 p.add_argument('--out',type=Path,required=True)
 a=p.parse_args()
 run(a.apk,a.out)
