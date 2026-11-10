"""RODI POS local development server. NOT a live payment gateway.

This module deliberately has no production payment mode: payment confirmation
requires a real Toss Front SDK integration, device provisioning and reconciliation.
"""
from __future__ import annotations
import argparse, datetime, hmac, json, os, re, secrets, sqlite3, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
CATALOG = [
    {'id':'flat-white','name':'Flat White','category':'Coffee','price':4800,'desc':'Silky double espresso with steamed milk','tag':'BEST'},
    {'id':'long-black','name':'Long Black','category':'Coffee','price':4200,'desc':'Rich espresso and hot water','tag':''},
    {'id':'iced-latte','name':'Iced Latte','category':'Coffee','price':5300,'desc':'Espresso poured over chilled milk','tag':'ICED'},
    {'id':'honey-carrot','name':'Honey Carrot Latte','category':'Signature','price':5900,'desc':'BunnyBear signature concept beverage','tag':'SIGNATURE'},
    {'id':'meat-pie','name':'Classic Aussie Pie','category':'Bakery','price':6800,'desc':'Golden puff pastry filled with savoury beef','tag':'POPULAR'},
    {'id':'carrot-cake','name':'Carrot Cake','category':'Bakery','price':6500,'desc':'Moist spiced carrot cake','tag':''},
]
# Above menu and prices are TEST FIXTURES, not approved commercial offers.
SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS orders (
 id TEXT PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE,
 payment_key TEXT NOT NULL UNIQUE, status TEXT NOT NULL DEFAULT 'PENDING_PAYMENT',
 total INTEGER NOT NULL, queue_no INTEGER,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 payment_result TEXT, payment_method TEXT
);
CREATE TABLE IF NOT EXISTS order_items (
 order_id TEXT NOT NULL REFERENCES orders(id), product_id TEXT NOT NULL,
 product_name TEXT NOT NULL, quantity INTEGER NOT NULL, unit_price INTEGER NOT NULL,
 drink_option TEXT NOT NULL DEFAULT 'DEFAULT', PRIMARY KEY(order_id,product_id,drink_option)
);
CREATE TABLE IF NOT EXISTS queue_counters(day TEXT PRIMARY KEY, next_no INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS print_jobs (
 id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES orders(id),
 status TEXT NOT NULL DEFAULT 'QUEUED', attempts INTEGER NOT NULL DEFAULT 0,
 last_error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT, kind TEXT NOT NULL,
 data TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status,created_at);
CREATE INDEX IF NOT EXISTS idx_print_jobs ON print_jobs(status,created_at);
'''
VALID_TRANSITIONS = {'PAID': {'MAKING'}, 'MAKING': {'READY'}, 'READY': {'COLLECTED'}, 'COLLECTED': set()}
DB_LOCK = threading.RLock()

class ManagedConnection(sqlite3.Connection):
    def __exit__(self, typ, value, traceback):
        try:
            return super().__exit__(typ, value, traceback)
        finally:
            self.close()

def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')

def db_conn(db_path):
    conn = sqlite3.connect(str(db_path), timeout=10, isolation_level=None, factory=ManagedConnection)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=10000')
    return conn

def init_db(path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with db_conn(path) as c:
        c.executescript(SCHEMA)

def audit(conn, order_id, kind, data=None):
    conn.execute('INSERT INTO audit(order_id,kind,data,created_at) VALUES (?,?,?,?)',
                 (order_id,kind,json.dumps(data or {},ensure_ascii=False),stamp()))

def order_view(c, order_id):
    r=c.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
    if not r: return None
    d=dict(r)
    d.pop('payment_result',None)
    d['items']=[dict(x) for x in c.execute('SELECT product_id,product_name,quantity,unit_price,drink_option FROM order_items WHERE order_id=?',(order_id,))]
    return d

def create_order(path, items, idem):
    if not isinstance(items,list) or not (1<=len(items)<=30):raise ValueError('상품은 1~30종 선택해 주세요.')
    if not isinstance(idem,str) or not re.fullmatch(r'[A-Za-z0-9_-]{12,100}',idem):raise ValueError('Idempotency-Key 형식 오류')
    products={p['id']:p for p in CATALOG}
    lines=[]; total=0; seen=set()
    for itm in items:
        if not isinstance(itm,dict):raise ValueError('잘못된 상품 형식')
        pid=itm.get('id'); qty=itm.get('qty')
        opt=itm.get('option','ICED' if products.get(pid,{}).get('category') in ('Coffee','Signature') else 'DEFAULT')
        if pid not in products or type(qty) is not int or not (1<=qty<=30) or (pid,opt) in seen:raise ValueError('상품 ID, 수량 또는 중복 오류')
        p=products[pid]
        choices=('HOT','ICED') if p['category'] in ('Coffee','Signature') else ('DEFAULT',)
        if opt not in choices: raise ValueError('이 상품에 지원되지 않는 옵션입니다.')
        seen.add((pid,opt));lines.append((pid,p['name'],qty,p['price'],opt));total+=p['price']*qty
    if total>2_000_000:raise ValueError('주문 금액 초과')
    with DB_LOCK,db_conn(path) as c:
        c.execute('BEGIN IMMEDIATE')
        old=c.execute('SELECT id FROM orders WHERE idempotency_key=?',(idem,)).fetchone()
        if old:
            view=order_view(c,old['id'])
            if sorted((x['product_id'],x['quantity'],x['drink_option']) for x in view['items']) != sorted((x[0],x[2],x[4]) for x in lines):
                c.execute('ROLLBACK');raise ValueError('동일한 요청키로 다른 주문을 보낼 수 없습니다.')
            c.execute('COMMIT');return view
        oid='rd_'+secrets.token_hex(8); pkey='rodi_'+secrets.token_hex(15); now=stamp()
        c.execute('INSERT INTO orders(id,idempotency_key,payment_key,total,created_at,updated_at) VALUES (?,?,?,?,?,?)',
                  (oid,idem,pkey,total,now,now))
        c.executemany('INSERT INTO order_items(order_id,product_id,product_name,quantity,unit_price,drink_option) VALUES(?,?,?,?,?,?)',
                      [(oid,line[0],line[1],line[2],line[3],line[4]) for line in lines])
        audit(c,oid,'ORDER_CREATED',{'total':total})
        view=order_view(c,oid)
        c.execute('COMMIT');return view

def settle_demo(path, order_id):
    """Simulation only. Never exposed outside loopback in server."""
    return confirm_payment(path,order_id,{'type':'SUCCESS','response':{'paymentMethod':'CARD','approvalNumber':'DEMO-ONLY'}},demo=True)

def confirm_payment(path,order_id,result, demo=False):
    if not isinstance(result,dict) or result.get('type') not in ('SUCCESS','TIMEOUT','CANCELED','FAILED'):
        raise ValueError('결제 응답 형식 오류')
    with DB_LOCK,db_conn(path) as c:
        c.execute('BEGIN IMMEDIATE')
        existing=c.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
        if not existing:raise LookupError('주문을 찾을 수 없습니다.')
        if existing['status'] != 'PENDING_PAYMENT':
            view=order_view(c,order_id);c.execute('COMMIT');return view
        if result['type'] != 'SUCCESS':
            audit(c,order_id,'PAYMENT_UNSUCCESSFUL',{'type':result['type']});c.execute('COMMIT')
            return order_view(c,order_id)
        response=result.get('response') or {}
        if not isinstance(response,dict) or response.get('paymentMethod') not in ('CARD','BARCODE'):
            raise ValueError('지원되지 않는 결제 수단')
        # A production implementation MUST reconcile paymentKey, merchant, terminal and
        # approved amount via authenticated Toss partner/device APIs before finalizing.
        if not demo and os.getenv('RODI_ALLOW_BRIDGE_CONFIRM')!='1':
            raise PermissionError('실결제 승인 저장은 검증된 단말기 통합 전까지 차단됩니다.')
        now=stamp(); day=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')
        r=c.execute('SELECT next_no FROM queue_counters WHERE day=?',(day,)).fetchone()
        no=r['next_no'] if r else 1
        if r:c.execute('UPDATE queue_counters SET next_no=next_no+1 WHERE day=?',(day,))
        else:c.execute('INSERT INTO queue_counters(day,next_no) VALUES(?,?)',(day,2))
        c.execute("UPDATE orders SET status='PAID',queue_no=?,payment_result=?,payment_method=?,updated_at=? WHERE id=?",
                  (no,json.dumps(result,ensure_ascii=False)[:12000],response['paymentMethod'],now,order_id))
        c.execute('INSERT INTO print_jobs(id,order_id,created_at,updated_at) VALUES(?,?,?,?)',('pj_'+secrets.token_hex(8),order_id,now,now))
        audit(c,order_id,'PAYMENT_SIMULATED' if demo else 'PAYMENT_REPORTED',{'queue_no':no})
        view=order_view(c,order_id);c.execute('COMMIT');return view

def status_order(path,order_id,target):
    with DB_LOCK,db_conn(path) as c:
        c.execute('BEGIN IMMEDIATE');v=order_view(c,order_id)
        if not v:raise LookupError('주문 없음')
        if target not in VALID_TRANSITIONS.get(v['status'],set()):raise ValueError('이 상태로 전환할 수 없습니다.')
        c.execute('UPDATE orders SET status=?,updated_at=? WHERE id=?',(target,stamp(),order_id))
        audit(c,order_id,'STATUS_CHANGED',{'from':v['status'],'to':target})
        v=order_view(c,order_id);c.execute('COMMIT');return v

def print_jobs(path):
    with db_conn(path) as c:
        rows=c.execute('SELECT p.id,p.status,p.attempts,o.id order_id,o.payment_key,o.queue_no,o.total,o.payment_method FROM print_jobs p JOIN orders o ON o.id=p.order_id WHERE p.status IN (\'QUEUED\',\'FAILED\') AND p.attempts<5 ORDER BY p.created_at LIMIT 10').fetchall()
        ret=[]
        for r in rows:
            a=dict(r);a['items']=[dict(x) for x in c.execute('SELECT product_name,quantity,unit_price,drink_option FROM order_items WHERE order_id=?',(r['order_id'],))];ret.append(a)
        return ret

def update_print(path,job_id,success,error=''):
    with DB_LOCK,db_conn(path) as c:
        c.execute('BEGIN IMMEDIATE')
        r=c.execute('SELECT order_id,status FROM print_jobs WHERE id=?',(job_id,)).fetchone()
        if not r:raise LookupError('출력 작업 없음')
        if r['status']=='PRINTED':c.execute('COMMIT');return
        c.execute('UPDATE print_jobs SET status=?, attempts=attempts+1, last_error=?, updated_at=? WHERE id=?',
                  ('PRINTED' if success else 'FAILED',str(error)[:200],stamp(),job_id))
        audit(c,r['order_id'],'RECEIPT_PRINTED' if success else 'RECEIPT_FAILED')
        c.execute('COMMIT')

class Handler(BaseHTTPRequestHandler):
    server_version='RODI-POS-Demo/0.2'
    def log_message(self,fmt,*args):
        # Do not log auth headers, body content or payment data.
        print('%s %s' % (stamp(),fmt%args))
    def headers_base(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
    def send_json(self, obj, code=200):
        data=json.dumps(obj,ensure_ascii=False).encode('utf-8')
        self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.headers_base();self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def body(self):
        if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':raise ValueError('JSON only')
        size=int(self.headers.get('Content-Length',0))
        if not (2<=size<=32_000):raise ValueError('JSON body invalid size')
        value=json.loads(self.rfile.read(size))
        if not isinstance(value,dict):raise ValueError('JSON object required')
        return value
    def auth(self,kind):
        key=self.server.staff_key if kind=='staff' else self.server.bridge_key
        got=self.headers.get('Authorization','').removeprefix('Bearer ').strip()
        if not key or not hmac.compare_digest(got,key):
            self.send_json({'error':'인증이 필요합니다.'},401);return False
        return True
    def do_GET(self):
        path=urllib.parse.urlsplit(self.path).path
        try:
            if path=='/api/health':return self.send_json({'ok':True,'mode':'SIMULATION_ONLY','currency':'KRW','toss_approved':False})
            if path=='/api/catalog':return self.send_json({'items':CATALOG,'currency':'KRW','demo':True})
            if path.startswith('/api/orders/') and re.fullmatch(r'/api/orders/rd_[0-9a-f]{16}',path):
                with db_conn(self.server.db_path) as c:v=order_view(c,path.rsplit('/',1)[1])
                return self.send_json(v) if v else self.send_json({'error':'주문 없음'},404)
            if path=='/api/staff/orders':
                if not self.auth('staff'):return
                with db_conn(self.server.db_path) as c:
                    ids=[r['id'] for r in c.execute("SELECT id FROM orders WHERE status IN ('PAID','MAKING','READY','COLLECTED') ORDER BY created_at DESC LIMIT 80")]
                    return self.send_json({'orders':[order_view(c,i) for i in ids]})
            if path=='/api/bridge/pending':
                if not self.auth('bridge'):return
                with db_conn(self.server.db_path) as c:
                    rows=[dict(x) for x in c.execute("SELECT id,payment_key,total,created_at FROM orders WHERE status='PENDING_PAYMENT' ORDER BY created_at LIMIT 10")]
                return self.send_json({'orders':rows})
            if path=='/api/bridge/print-jobs':
                if not self.auth('bridge'):return
                return self.send_json({'jobs':print_jobs(self.server.db_path)})
            if path in ('/','/index.html','/staff.html','/receipt','/receipt.html','/assets.css','/kiosk.js','/staff.js','/receipt.js'):
                file={'/':'index.html','/receipt':'receipt.html'}.get(path,path.lstrip('/'))
                data=(ROOT/'web'/file).read_bytes()
                mimetype='text/html; charset=utf-8' if file.endswith('.html') else ('text/css; charset=utf-8' if file.endswith('.css') else 'text/javascript; charset=utf-8')
                self.send_response(200);self.headers_base();self.send_header('Content-Type',mimetype);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            self.send_json({'error':'없음'},404)
        except Exception as e:self.send_json({'error':'내부 오류'},500)
    def do_POST(self):
        path=urllib.parse.urlsplit(self.path).path
        try:
            if path=='/api/orders':
                result=create_order(self.server.db_path,self.body().get('items'),self.headers.get('Idempotency-Key',''))
                return self.send_json(result,201)
            match=re.fullmatch(r'/api/demo/orders/(rd_[0-9a-f]{16})/pay',path)
            if match:
                if not self.server.demo or self.client_address[0] not in ('127.0.0.1','::1'):
                    return self.send_json({'error':'로컬 시뮬레이션에서만 사용 가능'},403)
                self.body();return self.send_json(settle_demo(self.server.db_path,match.group(1)))
            match=re.fullmatch(r'/api/staff/orders/(rd_[0-9a-f]{16})/status',path)
            if match:
                if not self.auth('staff'):return
                return self.send_json(status_order(self.server.db_path,match.group(1),self.body().get('status')))
            match=re.fullmatch(r'/api/staff/orders/(rd_[0-9a-f]{16})/reprint',path)
            if match:
                if not self.auth('staff'):return
                self.body()
                with DB_LOCK,db_conn(self.server.db_path) as c:
                    c.execute('BEGIN IMMEDIATE');v=order_view(c,match.group(1))
                    if not v or v['status']=='PENDING_PAYMENT':raise ValueError('결제된 주문만 영수증 재출력할 수 있습니다.')
                    now=stamp();c.execute('INSERT INTO print_jobs(id,order_id,created_at,updated_at) VALUES(?,?,?,?)',('pj_'+secrets.token_hex(8),match.group(1),now,now));c.execute('COMMIT')
                return self.send_json({'queued':True})
            if path=='/api/bridge/payment-result':
                if not self.auth('bridge'):return
                b=self.body();return self.send_json(confirm_payment(self.server.db_path,b.get('order_id'),b.get('result')))
            if path=='/api/bridge/print-result':
                if not self.auth('bridge'):return
                b=self.body();update_print(self.server.db_path,b.get('job_id'),b.get('success') is True,b.get('error',''))
                return self.send_json({'ok':True})
            self.send_json({'error':'없음'},404)
        except LookupError as e:self.send_json({'error':str(e)},404)
        except PermissionError as e:self.send_json({'error':str(e)},403)
        except (ValueError,sqlite3.IntegrityError,json.JSONDecodeError,TypeError) as e:self.send_json({'error':str(e)},400)
        except Exception:self.send_json({'error':'내부 오류'},500)

def serve(bind='127.0.0.1',port=8765,db_path=DATA/'rodipos.sqlite3',demo=True,staff_token=None,bridge_token=None):
    init_db(db_path)
    srv=ThreadingHTTPServer((bind,port),Handler)
    srv.db_path=db_path; srv.demo=demo
    srv.staff_key=staff_token or (secrets.token_urlsafe(24) if demo else os.getenv('RODI_STAFF_TOKEN',''))
    srv.bridge_key=bridge_token or os.getenv('RODI_BRIDGE_TOKEN','')
    if bind not in ('127.0.0.1','::1','localhost') and demo:
        raise RuntimeError('데모 결제 서버는 외부 네트워크에 바인딩하지 않습니다.')
    return srv

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8765)
    ap.add_argument('--bind',default='127.0.0.1');ap.add_argument('--db',default=str(DATA/'rodipos.sqlite3'))
    args=ap.parse_args();s=serve(args.bind,args.port,args.db)
    print(f'RODI POS local demo http://{args.bind}:{s.server_port}/')
    print(f'Staff token (local only): {s.staff_key}')
    try:s.serve_forever()
    except KeyboardInterrupt:pass
    finally:s.server_close()
