"""Public storefront + admin release scan. Does not assert live production behavior."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
import json,subprocess,os
root=Path(__file__).resolve().parents[1]
site=root/'storefront'
class Tags(HTMLParser):
 def __init__(self):super().__init__();self.refs=[]
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  for k in ('src','href'):
   if attrs.get(k):self.refs.append((k,attrs[k]))
htmls=list(site.rglob('*.html'))
errors=[];missing_assets=[];bad_utf8=[];scripts=[]
for f in htmls:
 try:s=f.read_text('utf-8')
 except UnicodeDecodeError:bad_utf8.append(str(f.relative_to(site)));continue
 if '\ufffd' in s:bad_utf8.append(str(f.relative_to(site)))
 parser=Tags();parser.feed(s)
 for attr,ref in parser.refs:
  if not ref or ref.startswith(('#','mailto:','tel:','javascript:','data:','blob:')):continue
  u=urlsplit(ref)
  if u.scheme or u.netloc:continue
  pathname=unquote(u.path)
  if not pathname:continue
  if pathname.startswith('/'):
   candidate=site/pathname.lstrip('/')
   if pathname=='/':candidate=site/'index.html'
  else:candidate=f.parent/pathname
  candidate=candidate.resolve()
  if candidate.is_dir():candidate=candidate/'index.html'
  if not candidate.exists():
   if '/api/' in pathname:continue
   if '/product/' in pathname and not pathname.endswith('.html'):continue
   errors.append({'file':str(f.relative_to(site)),'missing':ref})
 if f.name!='index.html' or '/admin/' not in str(f):
  if 'commerce-bridge-v6.js' not in s:missing_assets.append(str(f.relative_to(site)))
imgs=list((site/'assets'/'images'/'recipes').glob('*.webp'))
images_invalid=[]
for img in imgs:
 data=img.read_bytes()
 if data[:4]!=b'RIFF' or data[8:12]!=b'WEBP':images_invalid.append(img.name)
for f in site.rglob('*.js'):
 p=subprocess.run(['node','--check',str(f)],capture_output=True,text=True)
 if p.returncode!=0:scripts.append({'file':str(f.relative_to(site)),'error':p.stderr[:300]})
prods=json.loads((site/'assets'/'products.json').read_text('utf-8'))
rec=json.loads((site/'assets'/'recipes.json').read_text('utf-8'))
result={'mode':'static-local-beta','html_files':len(htmls),'storefront_html_files':len(htmls)-1,'products':len(prods),'recipes':len(rec),'recipe_webp':len(imgs),'html_link_errors':errors[:100],'missing_bridge':missing_assets[:20],'invalid_images':images_invalid,'js_syntax_errors':scripts,'text_bad_utf8':bad_utf8,'passed':not(errors or missing_assets or images_invalid or scripts or bad_utf8) and len(prods)==44 and len(rec)==132 and len(imgs)==132}
(root/'docs'/'QA_STATIC_RELEASE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v if not isinstance(v,list) else len(v) for k,v in result.items()},ensure_ascii=False,indent=2))
if not result['passed']:raise SystemExit(1)
