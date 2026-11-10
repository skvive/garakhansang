"""RODI POS local functional prototype. No live card charges are performed by this app.
The Toss FRONT bridge is isolated in terminal/ for future official SDK validation.
Inspired by the Garak Hansang order/accounting schema separation; no production data imported.
"""
import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import urllib.parse
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = Path(os.getenv('RODI_DB', str(ROOT / 'runtime' / 'rodi.sqlite3')))
WEB = ROOT / 'web'
MODE = os.getenv('RODI_MODE', 'demo')
STAFF_KEY = os.getenv('RODI_STAFF_KEY', 'local-demo-staff')
TERMINAL_KEY = os.getenv('RODI_TERMINAL_KEY', '')
ALLOWED_STATES = {'queued': 'preparing', 'preparing': 'ready', 'ready': 'collected'}
MENU = [
    {'id':'americano','name':'썬즈 아메리카노','en':'SunZ Americano','category':'coffee','price':4500,'emoji':'☕','description':'고소한 로스팅 원두 · HOT / ICED'},
    {'id':'latte','name':'바니베어 라떼','en':'BunnyBear Latte','category':'coffee','price':5500,'emoji':'🥛','description':'부드러운 우유와 진한 에스프레소'},
    {'id':'caramel','name':'허니 캐럿 라떼','en':'Honey Carrot Latte','category':'signature','price':6500,'emoji':'🥕','description':'달콤한 허니 캐럿 시그니처'},
    {'id':'mocha','name':'록스 모카','en':'Rocks Mocha','category':'coffee','price':5800,'emoji':'🍫','description':'다크 초콜릿과 에스프레소'},
    {'id':'pie','name':'시드니 미트파이','en':'Sydney Meat Pie','category':'bakery','price':7900,'emoji':'🥧','description':'겉은 바삭하고 속은 든든하게'},
    {'id':'carrotcake','name':'바니 캐럿 케이크','en':'Bunny Carrot Cake','category':'bakery','price':6800,'emoji':'🍰','description':'촉촉한 당근 케이크'},
    {'id':'cookie','name':'선즈 버터 쿠키','en':'SunZ Butter Cookie','category':'bakery','price':3500,'emoji':'🍪','description':'버터 풍미 가득한 홈메이드 스타일'},
    {'id':'tea','name':'록스 시트러스 티','en':'Rocks Citrus Tea','category':'signature','price':5300,'emoji':'🍋','description':'상큼한 시트러스 블렌드'},
]
MENU_BY_ID = {p['id']:p for p in MENU}
LOCK = threading.RLock()

def iso(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
def local_day(): return dt.datetime.now().strftime('%Y-%m-%d')
def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=10, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA busy_timeout=10000')
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('PRAGMA journal_mode=WAL')
    return c

def init_db():
    with LOCK:
        c=connect()
        c.executescript('''
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY, idem_key TEXT NOT NULL UNIQUE, cart_hash TEXT NOT NULL,
            payment_key TEXT NOT NULL UNIQUE, items_json TEXT NOT NULL,
            amount INTEGER NOT NULL CHECK(amount>0), currency TEXT NOT NULL DEFAULT 'KRW',
            mode TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'awaiting_payment',
            queue_date TEXT, queue_number INTEGER, approval_number TEXT,
            payment_method TEXT, payment_timestamp INTEGER, print_status TEXT NOT NULL DEFAULT 'pending',
            print_attempts INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
            paid_at TEXT, updated_at TEXT NOT NULL,
            UNIQUE(queue_date,queue_number)
        );
        CREATE TABLE IF NOT EXISTS queue_counters(day TEXT PRIMARY KEY, seq INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,order_id TEXT NOT NULL,kind TEXT NOT NULL,note TEXT NOT NULL DEFAULT '',at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_orders_paid ON orders(status,paid_at);
        ''')
        c.close()

def as_order(r):
    if not r: return None
    d=dict(r)
    d['items']=json.loads(d.pop('items_json'))
    for k in ['idem_key','cart_hash'] : d.pop(k,None)
    return d

def calculate_items(items):
    if not isinstance(items,list) or not (1<=len(items)<=30): raise ValueError('장바구니 품목 수 오류')
    out=[]; total=0
    for item in items:
        if not isinstance(item,dict): raise ValueError('장바구니 항목 오류')
        product=MENU_BY_ID.get(item.get('id'))
        qty=item.get('qty')
        if not product or type(qty)!=int or not (1<=qty<=20): raise ValueError('제품 또는 수량 오류')
        # Flavor/ice option currently non-priced, checked server-side.
        option=item.get('option','기본')
        if option not in ('기본','HOT','ICED'): raise ValueError('메뉴 옵션 오류')
        if product['category'] == 'bakery' and option!='기본': raise ValueError('베이커리 옵션 오류')
        out.append({'id':product['id'],'name':product['name'],'unit_price':product['price'], 'qty':qty,'option':option})
        total+=product['price']*qty
    if total>2_000_000: raise ValueError('결제 허용 금액 초과')
    return out,total

def create_checkout(items, key):
    if not isinstance(key,str) or not (16<=len(key)<=100) or not key.isascii(): raise ValueError('Idempotency-Key 필요')
    normalized,total=calculate_items(items)
    digest=hashlib.sha256(json.dumps(normalized,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    with LOCK:
        c=connect()
        try:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT * FROM orders WHERE idem_key=?',(key,)).fetchone()
            if old:
                if old['cart_hash']!=digest: raise ValueError('기존 요청키에 다른 장바구니가 사용됐습니다.')
                c.execute('COMMIT');return as_order(old)
            order_id=str(uuid.uuid4())
            payment_key='rodi_'+uuid.uuid4().hex
            now=iso()
            c.execute('''INSERT INTO orders(id,idem_key,cart_hash,payment_key,items_json,amount,mode,status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)''',(order_id,key,digest,payment_key,json.dumps(normalized,ensure_ascii=False),total,MODE,'awaiting_payment',now,now))
            c.execute('INSERT INTO events(order_id,kind,note,at) VALUES(?,?,?,?)',(order_id,'created','awaiting_payment',now))
            r=c.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
            c.execute('COMMIT'); return as_order(r)
        except Exception:
            c.execute('ROLLBACK'); raise
        finally:c.close()

def finalize_payment(order_id,payment_key,result,method,approval_number,timestamp):
    """Called ONLY by protected bridge endpoint (or demo-only endpoint).
    Live terminal results still require certified provider reconciliation before go-live.
    """
    if result not in ('SUCCESS','CANCELED','TIMEOUT','FAILED'): raise ValueError('잘못된 결제 결과')
    with LOCK:
        c=connect()
        try:
            c.execute('BEGIN IMMEDIATE')
            r=c.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
            if not r or r['payment_key']!=payment_key: raise ValueError('주문 또는 결제키 불일치')
            if r['status'] in ('queued','preparing','ready','collected'):
                if result!='SUCCESS': raise ValueError('이미 결제가 승인된 주문')
                c.execute('COMMIT');return as_order(r)
            if r['status']!='awaiting_payment': raise ValueError('주문 상태가 결제를 허용하지 않습니다.')
            if result!='SUCCESS':
                # Failure keeps the cart pending; a new terminal retry is an explicit customer action.
                c.execute('INSERT INTO events(order_id,kind,note,at) VALUES(?,?,?,?)',(order_id,'payment_failure',result,iso()))
                c.execute('COMMIT');return as_order(r)
            if method not in ('CARD','BARCODE','DEMO_CARD'): raise ValueError('지원하지 않는 결제 수단')
            if not isinstance(approval_number,str) or not approval_number or len(approval_number)>80: raise ValueError('승인번호가 없습니다.')
            if type(timestamp)!=int or timestamp<=0: raise ValueError('승인시각이 없습니다.')
            day=local_day()
            c.execute('INSERT INTO queue_counters(day,seq) VALUES(?,0) ON CONFLICT(day) DO NOTHING',(day,))
            c.execute('UPDATE queue_counters SET seq=seq+1 WHERE day=?',(day,))
            queue=c.execute('SELECT seq FROM queue_counters WHERE day=?',(day,)).fetchone()['seq']
            now=iso()
            c.execute('''UPDATE orders SET status='queued',queue_date=?,queue_number=?,approval_number=?,payment_method=?,payment_timestamp=?,paid_at=?,updated_at=? WHERE id=?''',
                (day,queue,approval_number,method,timestamp,now,now,order_id))
            c.execute('INSERT INTO events(order_id,kind,note,at) VALUES(?,?,?,?)',(order_id,'payment_approved',method,now))
            r=c.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
            c.execute('COMMIT');return as_order(r)
        except Exception:
            c.execute('ROLLBACK');raise
        finally:c.close()

def transition_order(order_id,next_status):
    with LOCK:
        c=connect()
        try:
            c.execute('BEGIN IMMEDIATE')
            r=c.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
            if not r:raise ValueError('주문이 없습니다.')
            if ALLOWED_STATES.get(r['status'])!=next_status:raise ValueError('허용되지 않는 주문 상태 전환')
            now=iso()
            c.execute('UPDATE orders SET status=?,updated_at=? WHERE id=?',(next_status,now,order_id))
            c.execute('INSERT INTO events(order_id,kind,note,at) VALUES(?,?,?,?)',(order_id,'status',next_status,now))
            r=c.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
            c.execute('COMMIT');return as_order(r)
        except Exception:
            c.execute('ROLLBACK');raise
        finally:c.close()

def cancel_pending(order_id, payment_key):
    """Demo customer abandon. Never call during an in-progress physical VAN approval."""
    if MODE != 'demo': raise ValueError('운영결제 취소는 단말기 승인 상태 확인이 필요합니다.')
    with LOCK:
        c=connect()
        try:
            c.execute('BEGIN IMMEDIATE')
            r=c.execute('SELECT status,payment_key FROM orders WHERE id=?',(order_id,)).fetchone()
            if not r or r['payment_key']!=payment_key:raise ValueError('주문 인증 실패')
            if r['status']=='cancelled':c.execute('COMMIT');return read_order(order_id)
            if r['status']!='awaiting_payment':raise ValueError('결제 완료 주문은 취소할 수 없습니다.')
            c.execute("UPDATE orders SET status='cancelled',updated_at=? WHERE id=?",(iso(),order_id))
            c.execute('INSERT INTO events(order_id,kind,note,at) VALUES(?,?,?,?)',(order_id,'cancelled','customer_abandoned',iso()))
            c.execute('COMMIT')
            return read_order(order_id)
        except Exception:
            c.execute('ROLLBACK'); raise
        finally:c.close()

def list_orders():
    c=connect()
    try:return [as_order(r) for r in c.execute("SELECT * FROM orders WHERE status IN ('queued','preparing','ready','collected') ORDER BY queue_date DESC,queue_number DESC LIMIT 150").fetchall()]
    finally:c.close()

def read_order(order_id):
    c=connect()
    try:return as_order(c.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone())
    finally:c.close()

def log_print(order_id, status):
    if status not in ('printed','failed'):raise ValueError('출력 상태 오류')
    with LOCK:
        c=connect()
        try:
            c.execute('BEGIN IMMEDIATE')
            r=c.execute('SELECT status FROM orders WHERE id=?',(order_id,)).fetchone()
            if not r or r['status'] not in ('queued','preparing','ready','collected'): raise ValueError('결제 완료 주문만 출력 가능')
            c.execute('UPDATE orders SET print_status=?,print_attempts=print_attempts+1 WHERE id=?',(status,order_id))
            c.execute('INSERT INTO events(order_id,kind,note,at) VALUES(?,?,?,?)',(order_id,'print',status,iso()))
            c.execute('COMMIT'); return read_order(order_id)
        except Exception:
            c.execute('ROLLBACK');raise
        finally:c.close()

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(WEB),**kwargs)
    def log_message(self,fmt,*args):pass
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        super().end_headers()
    def send_json(self,obj,status=200):
        body=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def fail(self,code,msg):self.send_json({'error':msg},code)
    def body(self):
        if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':raise ValueError('JSON Content-Type이 필요합니다.')
        n=int(self.headers.get('Content-Length','0'))
        if not (2<=n<=32000):raise ValueError('요청 본문 크기 오류')
        data=json.loads(self.rfile.read(n))
        if not isinstance(data,dict): raise ValueError('JSON 객체가 필요합니다.')
        return data
    def authorized(self,token):
        h=self.headers.get('Authorization','')
        return bool(token) and h.startswith('Bearer ') and hmac.compare_digest(h[7:],token)
    def origin_ok(self):
        origin=self.headers.get('Origin')
        return not origin or urllib.parse.urlparse(origin).netloc == self.headers.get('Host')
    def do_GET(self):
        path=urllib.parse.urlsplit(self.path).path
        if path=='/api/health':return self.send_json({'ok':True,'mode':MODE,'currency':'KRW','checkout':'demo_only' if MODE=='demo' else 'bridge_required'})
        if path=='/api/menu':return self.send_json({'items':MENU,'currency':'KRW','demo_prices':True})
        if path=='/api/staff/orders':
            if not self.authorized(STAFF_KEY):return self.fail(401,'직원 인증 필요')
            return self.send_json({'orders':list_orders()})
        if path.startswith('/api/orders/'):
            oid=path.removeprefix('/api/orders/')
            r=read_order(oid)
            if not r:return self.fail(404,'주문 없음')
            return self.send_json({'order':r})
        if path=='/api/terminal/pending':
            if MODE=='demo':return self.fail(403,'실물 단말 연동 비활성 · 개발 데모 전용')
            if not self.authorized(TERMINAL_KEY):return self.fail(401,'단말 인증 필요')
            c=connect()
            try:
                r=c.execute("SELECT * FROM orders WHERE status='awaiting_payment' ORDER BY created_at ASC LIMIT 1").fetchone()
                return self.send_json({'order':as_order(r)})
            finally:c.close()
        if path=='/staff':self.path='/staff.html'
        elif path=='/receipt':self.path='/receipt.html'
        elif path=='/':self.path='/index.html'
        return super().do_GET()
    def do_POST(self):
        path=urllib.parse.urlsplit(self.path).path
        if not self.origin_ok():return self.fail(403,'요청 출처 불일치')
        try:
            data=self.body()
            if path=='/api/checkout':
                order=create_checkout(data.get('items'),self.headers.get('Idempotency-Key',''))
                return self.send_json({'order':order},201)
            if path=='/api/demo/approve':
                if MODE!='demo':return self.fail(403,'운영 결제 사용 불가')
                oid=data.get('order_id','');r=read_order(oid)
                if not r:return self.fail(404,'주문 없음')
                result=finalize_payment(oid,r['payment_key'],'SUCCESS','DEMO_CARD','DEMO-'+secrets.token_hex(4),int(dt.datetime.now().timestamp()*1000))
                return self.send_json({'order':result,'simulated':True})
            if path=='/api/orders/cancel':
                return self.send_json({'order':cancel_pending(data.get('order_id',''),data.get('payment_key',''))})
            if path=='/api/staff/status':
                if not self.authorized(STAFF_KEY):return self.fail(401,'직원 인증 필요')
                return self.send_json({'order':transition_order(data.get('order_id',''),data.get('status',''))})
            if path=='/api/terminal/complete':
                if MODE=='demo':return self.fail(403,'실물 카드 승인 연동 비활성 · 데모 전용')
                if not self.authorized(TERMINAL_KEY):return self.fail(401,'단말 인증 필요')
                order=finalize_payment(data.get('order_id',''),data.get('payment_key',''),data.get('result',''),data.get('payment_method',''),data.get('approval_number',''),data.get('timestamp',0))
                return self.send_json({'order':order})
            if path=='/api/terminal/print-status':
                if MODE=='demo':return self.fail(403,'실물 프린터 연동 비활성 · 데모 전용')
                if not self.authorized(TERMINAL_KEY):return self.fail(401,'단말 인증 필요')
                return self.send_json({'order':log_print(data.get('order_id',''),data.get('status',''))})
            return self.fail(404,'API 경로 없음')
        except (ValueError,TypeError,KeyError,json.JSONDecodeError) as e:return self.fail(400,str(e))
        except Exception:return self.fail(500,'내부 오류')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    if MODE!='demo':
        raise SystemExit('Production payment mode is not certified. Live payments intentionally blocked until provider review.')
    init_db()
    print(f'RODI POS DEMO: http://{args.host}:{args.port} (staff: /staff)')
    ThreadingHTTPServer((args.host,args.port),Handler).serve_forever()
