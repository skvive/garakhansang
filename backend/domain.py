"""Garak Hansang Order: strictly local, simulated commerce engine.

This module does not accept real payments, store personal delivery addresses,
track real riders, or provide a production authentication boundary.
"""
import hashlib
import json
import secrets
import hmac
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name('catalog.json')

class DomainError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def uid(prefix):
    return prefix + '_' + uuid.uuid4().hex[:16]


def db_connect(path):
    db = sqlite3.connect(str(path), timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=10000')
    return db


def init_db(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = db_connect(path)
    db.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS markets(
       id TEXT PRIMARY KEY, name TEXT NOT NULL, base_fee INTEGER NOT NULL,
       additional_store_fee INTEGER NOT NULL, cold_fee INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS merchants(
       id TEXT PRIMARY KEY, market_id TEXT NOT NULL REFERENCES markets(id),
       name TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
       created_at TEXT NOT NULL, demo INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS products(
       id TEXT PRIMARY KEY, market_id TEXT NOT NULL REFERENCES markets(id),
       merchant_id TEXT NOT NULL REFERENCES merchants(id), name TEXT NOT NULL,
       price INTEGER NOT NULL CHECK(price>=0), stock INTEGER NOT NULL CHECK(stock>=0),
       cold INTEGER NOT NULL DEFAULT 0, processing INTEGER NOT NULL DEFAULT 0, demo INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS orders(
       id TEXT PRIMARY KEY, checkout_id TEXT NOT NULL, market_id TEXT NOT NULL REFERENCES markets(id),
       subtotal INTEGER NOT NULL, shipping INTEGER NOT NULL, discount INTEGER NOT NULL,
       total INTEGER NOT NULL, coupon_id TEXT,
       status TEXT NOT NULL CHECK(status IN ('awaiting_mock_payment','paid_mock','assembling','ready_for_dispatch','assigned','picked_up','delivered','cancelled')),
       created_at TEXT NOT NULL, updated_at TEXT NOT NULL, demo INTEGER NOT NULL DEFAULT 1);
    CREATE INDEX IF NOT EXISTS idx_order_market ON orders(market_id,created_at);
    CREATE TABLE IF NOT EXISTS order_lines(
       id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES orders(id),
       product_id TEXT NOT NULL REFERENCES products(id), merchant_id TEXT NOT NULL REFERENCES merchants(id),
       name_snapshot TEXT NOT NULL, qty INTEGER NOT NULL CHECK(qty BETWEEN 1 AND 99),
       unit_price INTEGER NOT NULL CHECK(unit_price>=0), processing TEXT NOT NULL DEFAULT '');
    CREATE TABLE IF NOT EXISTS merchant_fulfillment(
       order_id TEXT NOT NULL REFERENCES orders(id), merchant_id TEXT NOT NULL REFERENCES merchants(id),
       status TEXT NOT NULL CHECK(status IN ('pending','accepted','ready')),
       PRIMARY KEY(order_id,merchant_id));
    CREATE TABLE IF NOT EXISTS dispatch_jobs(
       id TEXT PRIMARY KEY, order_id TEXT NOT NULL UNIQUE REFERENCES orders(id),
       market_id TEXT NOT NULL REFERENCES markets(id), rider_alias TEXT,
       status TEXT NOT NULL CHECK(status IN ('waiting','assigned','picked_up','delivered')),
       updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS coupon_redemptions(
       coupon_id TEXT NOT NULL, checkout_id TEXT NOT NULL, order_id TEXT NOT NULL REFERENCES orders(id),
       PRIMARY KEY(coupon_id,checkout_id));
    CREATE TABLE IF NOT EXISTS checkout_access(
       checkout_id TEXT PRIMARY KEY, token_sha TEXT NOT NULL,
       created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS idempotency(
       key TEXT PRIMARY KEY, payload_sha TEXT NOT NULL, response_json TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS event_log(
       id INTEGER PRIMARY KEY AUTOINCREMENT, entity TEXT NOT NULL,
       entity_id TEXT NOT NULL, action TEXT NOT NULL, actor_role TEXT NOT NULL,
       created_at TEXT NOT NULL);
    ''')
    with CATALOG_PATH.open(encoding='utf-8') as f:
        catalog = json.load(f)
    db.execute('BEGIN IMMEDIATE')
    try:
        for m in catalog['markets']:
            db.execute('INSERT OR IGNORE INTO markets VALUES(?,?,?,?,?)',
                       (m['id'],m['name'],m['min'],m['add'],m['cold']))
        for p in catalog['items']:
            merchant_id = 'store_' + hashlib.sha256((p['m'] + '|' + p['store']).encode()).hexdigest()[:12]
            db.execute('INSERT OR IGNORE INTO merchants VALUES(?,?,?,?,?,1)',
                       (merchant_id,p['m'],p['store'],'approved',now()))
            db.execute('INSERT OR IGNORE INTO products VALUES(?,?,?,?,?,?,?,?,1)',
                       (p['id'],p['m'],merchant_id,p['name'],p['price'],30,
                        int(bool(p.get('cold'))),int(bool(p.get('process')))))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def rows(db, q, args=()):
    return [dict(x) for x in db.execute(q,args).fetchall()]


def record(db, entity, entity_id, action, role):
    db.execute('INSERT INTO event_log(entity,entity_id,action,actor_role,created_at) VALUES(?,?,?,?,?)',
               (entity,entity_id,action,role,now()))


def require_role(role, allowed):
    if role not in allowed:
        raise DomainError('데모 역할 권한이 없습니다',403)


def markets(db):
    return rows(db,'SELECT * FROM markets ORDER BY id')


def merchants(db, market_id=None):
    if market_id:
        return rows(db,'SELECT * FROM merchants WHERE market_id=? ORDER BY name',(market_id,))
    return rows(db,'SELECT * FROM merchants ORDER BY market_id,name')


def products(db, market_id=None):
    if market_id:
        return rows(db,'SELECT p.* FROM products p JOIN merchants m ON m.id=p.merchant_id WHERE p.market_id=? AND m.status=\'approved\' ORDER BY p.name',(market_id,))
    return rows(db,'SELECT p.* FROM products p JOIN merchants m ON m.id=p.merchant_id WHERE m.status=\'approved\' ORDER BY p.market_id,p.name')


def apply_merchant(db, payload, role):
    require_role(role, {'merchant','admin'})
    market_id = str(payload.get('market_id','')).strip()
    name = str(payload.get('name','')).strip()
    if not db.execute('SELECT id FROM markets WHERE id=?',(market_id,)).fetchone():
        raise DomainError('존재하지 않는 시장입니다')
    if not (2 <= len(name) <= 70):
        raise DomainError('상호명 2~70자 필요')
    mid=uid('store')
    with db:
        db.execute('INSERT INTO merchants VALUES(?,?,?,?,?,1)',(mid,market_id,name,'pending',now()))
        record(db,'merchant',mid,'applied',role)
    return dict(db.execute('SELECT * FROM merchants WHERE id=?',(mid,)).fetchone())


def approve_merchant(db, merchant_id, role):
    require_role(role, {'admin'})
    with db:
        row=db.execute('SELECT * FROM merchants WHERE id=?',(merchant_id,)).fetchone()
        if not row: raise DomainError('상인 신청을 찾을 수 없습니다',404)
        if row['status']!='pending': raise DomainError('대기 상태만 승인 가능',409)
        db.execute("UPDATE merchants SET status='approved' WHERE id=?",(merchant_id,))
        record(db,'merchant',merchant_id,'approved',role)
    return {'merchant_id':merchant_id,'status':'approved'}


def update_stock(db,merchant_id,product_id,stock,role):
    require_role(role, {'merchant','admin'})
    if type(stock) is not int or not 0<=stock<=100000: raise DomainError('재고 0~100000 정수만 허용')
    with db:
        p=db.execute('SELECT * FROM products WHERE id=? AND merchant_id=?',(product_id,merchant_id)).fetchone()
        if not p: raise DomainError('해당 상점의 상품이 아닙니다',403)
        db.execute('UPDATE products SET stock=? WHERE id=?',(stock,product_id))
        record(db,'product',product_id,'stock_updated',role)
    return {'id':product_id,'stock':stock}


def _normalized_lines(db, line_payload):
    if not isinstance(line_payload,list) or not 1<=len(line_payload)<=80:
        raise DomainError('장바구니 1~80개 상품 필요')
    combined={}
    for entry in line_payload:
        if not isinstance(entry,dict):raise DomainError('상품 항목 형식 오류')
        product_id=str(entry.get('id',''))
        processing=str(entry.get('proc',''))
        qty=entry.get('qty')
        if type(qty) is not int or qty<1 or qty>99:raise DomainError('상품 수량 오류')
        if processing not in ('','sliced'):raise DomainError('지원하지 않는 손질 옵션')
        key=(product_id,processing)
        combined[key]=combined.get(key,0)+qty
        if combined[key]>99:raise DomainError('상품별 최대 99개')
    result=[]
    for (product_id,processing),qty in combined.items():
        p=db.execute("SELECT p.*,m.status as merchant_status FROM products p JOIN merchants m ON m.id=p.merchant_id WHERE p.id=?",(product_id,)).fetchone()
        if not p or p['merchant_status']!='approved':raise DomainError('판매 불가 상품: '+product_id,409)
        if processing=='sliced' and not p['processing']:raise DomainError('손질이 불가능한 상품입니다',409)
        result.append({'p':dict(p),'proc':processing,'qty':qty,'unit_price':p['price']+(3000 if processing=='sliced' else 0)})
    return result


def _cost(db, market_id, lines):
    m=db.execute('SELECT * FROM markets WHERE id=?',(market_id,)).fetchone()
    if not m:raise DomainError('시장 정보 없음')
    stores={x['p']['merchant_id'] for x in lines}
    return m['base_fee'] + (len(stores)-1)*m['additional_store_fee'] + (m['cold_fee'] if any(x['p']['cold'] for x in lines) else 0)


def _coupon(groups, coupon_id, had_any_orders):
    if coupon_id not in ('','welcome','marketday','fish','bundle'):
        raise DomainError('지원하지 않는 쿠폰')
    if not coupon_id:return None,0
    for mid, ls in groups.items():
        subtotal=sum(x['unit_price']*x['qty'] for x in ls)
        if coupon_id=='welcome' and not had_any_orders and subtotal>=30000:
            return mid,min(5000,subtotal)
        if coupon_id=='marketday' and mid=='garak' and subtotal>=20000:
            return mid,min(3500,subtotal//10)
        if coupon_id=='fish' and mid=='noryang' and subtotal>=30000:
            return mid,3000
        if coupon_id=='bundle' and subtotal>=30000 and len({x['p']['merchant_id'] for x in ls})>=2:
            return mid,2500
    return None,0


def create_orders(db, payload, idem_key, role='customer'):
    require_role(role, {'customer','admin'})
    if not (8<=len(idem_key)<=128):raise DomainError('Idempotency-Key 8~128자 필요')
    if not isinstance(payload,dict):raise DomainError('요청 형식 오류')
    coupon_id=str(payload.get('coupon_id',''))
    normalized=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    phash=hashlib.sha256(normalized.encode()).hexdigest()
    db.execute('BEGIN IMMEDIATE')
    try:
        past=db.execute('SELECT * FROM idempotency WHERE key=?',(idem_key,)).fetchone()
        if past:
            if past['payload_sha']!=phash:raise DomainError('같은 키에 다른 주문 내용 사용',409)
            db.commit();return json.loads(past['response_json'])
        lines=_normalized_lines(db,payload.get('lines'))
        stock_required={}
        for x in lines:
            pid=x['p']['id'];stock_required[pid]=stock_required.get(pid,0)+x['qty']
        for pid,qty in stock_required.items():
            p=db.execute('SELECT stock FROM products WHERE id=?',(pid,)).fetchone()
            if not p or p['stock']<qty:raise DomainError('상품 재고가 부족합니다: '+pid,409)
        grouped={}
        for x in lines: grouped.setdefault(x['p']['market_id'],[]).append(x)
        # A coupon is strictly scoped to one market; never discounts cross-market totals.
        had_any_orders=bool(db.execute('SELECT 1 FROM orders LIMIT 1').fetchone())
        target,discount=_coupon(grouped,coupon_id,had_any_orders)
        checkout_id=uid('checkout')
        customer_action_token=secrets.token_urlsafe(32)
        db.execute('INSERT INTO checkout_access VALUES(?,?,?)',(checkout_id,hashlib.sha256(customer_action_token.encode()).hexdigest(),now()))
        order_ids=[]
        for mid,group in grouped.items():
            oid=uid('order');order_ids.append(oid)
            subtotal=sum(x['unit_price']*x['qty'] for x in group)
            shipping=_cost(db,mid,group)
            discount_this_market= min(discount,shipping) if coupon_id=='bundle' and mid==target else discount if mid==target else 0
            status='awaiting_mock_payment'
            db.execute('INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       (oid,checkout_id,mid,subtotal,shipping,discount_this_market,
                        subtotal+shipping-discount_this_market,coupon_id if mid==target else None,status,now(),now(),1))
            for x in group:
                db.execute('INSERT INTO order_lines VALUES(?,?,?,?,?,?,?,?)',
                           (uid('line'),oid,x['p']['id'],x['p']['merchant_id'],x['p']['name'],x['qty'],x['unit_price'],x['proc']))
            for store in {x['p']['merchant_id'] for x in group}:
                db.execute('INSERT INTO merchant_fulfillment VALUES(?,?,?)',(oid,store,'pending'))
            record(db,'order',oid,'created_mock',role)
        for pid,qty in stock_required.items():
            db.execute('UPDATE products SET stock=stock-? WHERE id=?',(qty,pid))
        if target and discount:
            claimed_oid=next(o for o in order_ids if db.execute('SELECT market_id FROM orders WHERE id=?',(o,)).fetchone()['market_id']==target)
            db.execute('INSERT INTO coupon_redemptions VALUES(?,?,?)',(coupon_id,checkout_id,claimed_oid))
        response={'demo':True,'checkout_id':checkout_id,'customer_action_token':customer_action_token,'orders':[dict(db.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()) for oid in order_ids]}
        db.execute('INSERT INTO idempotency VALUES(?,?,?)',(idem_key,phash,json.dumps(response,ensure_ascii=False)))
        db.commit();return response
    except Exception:
        db.rollback();raise


def get_orders(db, market_id=None):
    query='SELECT * FROM orders'+(' WHERE market_id=?' if market_id else '')+' ORDER BY created_at DESC,id DESC'
    out=rows(db,query,(market_id,) if market_id else ())
    for order in out:
        order['lines']=rows(db,'SELECT * FROM order_lines WHERE order_id=?',(order['id'],))
        order['fulfillment']=rows(db,'SELECT f.*,m.name FROM merchant_fulfillment f JOIN merchants m ON m.id=f.merchant_id WHERE f.order_id=?',(order['id'],))
        order['dispatch']=rows(db,'SELECT * FROM dispatch_jobs WHERE order_id=?',(order['id'],))
    return out


def verify_checkout_access(db, oid, role, bearer_token=''):
    if role == 'admin':
        return
    if role != 'customer' or not bearer_token:
        raise DomainError('주문 접근 토큰이 필요합니다', 403)
    row=db.execute('''SELECT a.token_sha FROM checkout_access a JOIN orders o
      ON a.checkout_id=o.checkout_id WHERE o.id=?''',(oid,)).fetchone()
    if not row or not hmac.compare_digest(row['token_sha'],hashlib.sha256(bearer_token.encode()).hexdigest()):
        raise DomainError('주문 소유 검증에 실패했습니다',403)


def mock_pay(db,oid,role,customer_action_token=''):
    require_role(role, {'customer','admin'})
    verify_checkout_access(db,oid,role,customer_action_token)
    with db:
        o=db.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
        if not o:raise DomainError('주문 없음',404)
        if o['status']!='awaiting_mock_payment':raise DomainError('모의 결제 대기 주문만 처리 가능',409)
        db.execute("UPDATE orders SET status='paid_mock',updated_at=? WHERE id=?",(now(),oid))
        record(db,'order',oid,'paid_mock',role)
    return {'id':oid,'status':'paid_mock','demo':True}


def merchant_status(db,oid,merchant_id,new_status,role):
    require_role(role,{'merchant','admin'})
    if new_status not in ('accepted','ready'):raise DomainError('허용하지 않는 상태')
    with db:
        o=db.execute('SELECT status FROM orders WHERE id=?',(oid,)).fetchone()
        f=db.execute('SELECT * FROM merchant_fulfillment WHERE order_id=? AND merchant_id=?',(oid,merchant_id)).fetchone()
        if not o or not f:raise DomainError('상인에게 배정되지 않은 주문',403)
        if o['status'] not in ('paid_mock','assembling'):raise DomainError('모의 결제 완료 후 진행 가능합니다',409)
        transition={'pending':'accepted','accepted':'ready'}
        if transition.get(f['status'])!=new_status:raise DomainError('상인 상태 전환 순서 오류',409)
        db.execute('UPDATE merchant_fulfillment SET status=? WHERE order_id=? AND merchant_id=?',(new_status,oid,merchant_id))
        db.execute("UPDATE orders SET status='assembling',updated_at=? WHERE id=?",(now(),oid))
        record(db,'fulfillment',oid,merchant_id+':'+new_status,role)
    return {'order_id':oid,'merchant_id':merchant_id,'status':new_status}


def hub_collect(db,oid,role):
    require_role(role,{'hub','admin'})
    with db:
        o=db.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
        if not o:raise DomainError('주문 없음',404)
        fs=rows(db,'SELECT status FROM merchant_fulfillment WHERE order_id=?',(oid,))
        if o['status']!='assembling' or not fs or not all(x['status']=='ready' for x in fs):
            raise DomainError('모든 점포 집하 준비 완료 후에만 인수할 수 있습니다',409)
        db.execute("UPDATE orders SET status='ready_for_dispatch',updated_at=? WHERE id=?",(now(),oid))
        job=uid('dispatch')
        db.execute('INSERT INTO dispatch_jobs VALUES(?,?,?,?,?,?)',(job,oid,o['market_id'],None,'waiting',now()))
        record(db,'dispatch',job,'hub_collected',role)
    return {'order_id':oid,'job_id':job,'status':'ready_for_dispatch'}


def dispatch_update(db,job_id,action,rider_alias,role):
    require_role(role,{'rider','hub','admin'})
    if action not in ('assign','pick_up','deliver'):raise DomainError('잘못된 배차 작업')
    with db:
        j=db.execute('SELECT * FROM dispatch_jobs WHERE id=?',(job_id,)).fetchone()
        if not j:raise DomainError('배차 작업 없음',404)
        expected={'assign':'waiting','pick_up':'assigned','deliver':'picked_up'}[action]
        if j['status']!=expected:raise DomainError('배차 상태 전환 순서 오류',409)
        if action=='assign':
            if role not in ('hub','admin'):raise DomainError('집하센터만 기사 배정 가능',403)
            if not 2<=len(rider_alias)<=32:raise DomainError('시연 기사 표시명 2~32자 필요')
            status='assigned'
            db.execute('UPDATE dispatch_jobs SET rider_alias=?,status=?,updated_at=? WHERE id=?',(rider_alias,status,now(),job_id))
        else:
            if role not in ('rider','admin'):raise DomainError('기사 역할 필요',403)
            status='picked_up' if action=='pick_up' else 'delivered'
            db.execute('UPDATE dispatch_jobs SET status=?,updated_at=? WHERE id=?',(status,now(),job_id))
        db.execute('UPDATE orders SET status=?,updated_at=? WHERE id=?',(status,now(),j['order_id']))
        record(db,'dispatch',job_id,status,role)
    return {'job_id':job_id,'order_id':j['order_id'],'status':status,'demo':True}


def cancel_order(db,oid,role,customer_action_token=''):
    require_role(role,{'customer','admin'})
    verify_checkout_access(db,oid,role,customer_action_token)
    with db:
        o=db.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
        if not o:raise DomainError('주문 없음',404)
        if o['status'] not in ('awaiting_mock_payment','paid_mock','assembling'):
            raise DomainError('집하·배차 진행 주문은 시연 취소 불가',409)
        for line in rows(db,'SELECT * FROM order_lines WHERE order_id=?',(oid,)):
            db.execute('UPDATE products SET stock=stock+? WHERE id=?',(line['qty'],line['product_id']))
        db.execute("UPDATE orders SET status='cancelled',updated_at=? WHERE id=?",(now(),oid))
        record(db,'order',oid,'cancelled_mock',role)
    return {'order_id':oid,'status':'cancelled','demo':True}


def dashboard(db):
    return {
     'merchants_pending':db.execute("SELECT count(*) FROM merchants WHERE status='pending'").fetchone()[0],
     'total_mock_orders':db.execute('SELECT count(*) FROM orders').fetchone()[0],
     'orders_by_status':rows(db,'SELECT status,count(*) as count FROM orders GROUP BY status ORDER BY status'),
     'dispatch_jobs':rows(db,'SELECT d.*,m.name as market_name FROM dispatch_jobs d JOIN markets m ON m.id=d.market_id ORDER BY d.updated_at DESC'),
     'audit_tail':rows(db,'SELECT * FROM event_log ORDER BY id DESC LIMIT 30')
    }
