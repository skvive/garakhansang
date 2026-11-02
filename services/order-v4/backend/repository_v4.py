"""Neon transaction adapter (PostgreSQL). Isolated development, never live payments.
Requires psycopg 3 at deployment. Does not accept SQL identifiers from callers.
Every restricted operation uses server-side membership lookups inside the DB.
"""
import os
import json
import uuid
from contextlib import contextmanager
from urllib.parse import urlsplit

class StorageUnavailable(Exception):
    pass

class Forbidden(Exception):
    pass

class Conflict(Exception):
    pass

class NotFound(Exception):
    pass

@contextmanager
def open_db():
    if os.environ.get('GHO_V4_MODE')!='isolated-dev':
        raise StorageUnavailable('V4 writes require isolated-dev mode')
    dsn=os.getenv('GHO_NEON_DSN','')
    if not dsn:
        raise StorageUnavailable('GHO_NEON_DSN is not configured')
    # Neon-host guard prevents accidentally attaching a local/other production DSN.
    parsed=urlsplit(dsn)
    if parsed.scheme not in ('postgres','postgresql') or not (parsed.hostname or '').endswith('.neon.tech'):
        raise StorageUnavailable('Only a Neon PostgreSQL endpoint is allowed')
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise StorageUnavailable('Install requirements-v4.txt (psycopg3 driver)') from exc
    with psycopg.connect(dsn,autocommit=False,row_factory=dict_row,connect_timeout=5,
                         options='-c statement_timeout=5000 -c idle_in_transaction_session_timeout=10000') as db:
        yield db

def _parse_uuid(value):
    try:return uuid.UUID(str(value))
    except (ValueError,AttributeError,TypeError) as exc:raise ValueError('Invalid UUID') from exc

def _grant(db,subject,role,*,market_id=None,merchant_id=None):
    with db.cursor() as cur:
        cur.execute('''SELECT 1 FROM gho.actor_grants WHERE auth_subject=%s AND role=%s AND enabled=true
               AND (%s::text IS NULL OR market_id=%s::text)
               AND (%s::uuid IS NULL OR merchant_id=%s::uuid) LIMIT 1''',
             (subject,role,market_id,market_id,merchant_id,merchant_id))
        return cur.fetchone() is not None

def _merchant_access(db,subject,merchant_id):
    mid=_parse_uuid(merchant_id)
    with db.cursor() as cur:
        cur.execute('''SELECT 1 FROM gho.merchant_members WHERE auth_subject=%s AND merchant_id=%s
            AND member_role IN ('owner','staff') LIMIT 1''',(subject,mid))
        if cur.fetchone():return mid
    if _grant(db,subject,'admin'):return mid
    raise Forbidden('This merchant is not linked to your account')

def catalog(db,market_id=None):
    with db.cursor() as cur:
        cur.execute('''SELECT p.catalog_ref AS id,p.market_id,p.name,p.price_krw AS price,p.stock,
                     p.temp_class,p.supports_slicing,m.business_name AS merchant_name
                     FROM gho.products p JOIN gho.merchants m ON m.id=p.merchant_id
                     WHERE p.is_demo=true AND p.status='active' AND m.approval_status='approved'
                     AND (%s::text IS NULL OR p.market_id=%s::text) ORDER BY p.market_id,p.name LIMIT 200''',
                    (market_id,market_id))
        return cur.fetchall()

def create_checkout(db,subject,idempotency_key,lines):
    if not isinstance(idempotency_key,str) or not 8<=len(idempotency_key)<=128:
        raise ValueError('Idempotency-Key must be 8-128 characters')
    if not isinstance(lines,list) or not 1<=len(lines)<=80:
        raise ValueError('Cart must contain 1-80 items')
    with db.transaction():
        with db.cursor() as cur:
            cur.execute('SELECT gho.create_demo_checkout(%s,%s,%s::jsonb) AS result',
                (subject,idempotency_key,json.dumps(lines,ensure_ascii=False)))
            out=cur.fetchone()['result']
    return out

def customer_orders(db,subject):
    with db.cursor() as cur:
        cur.execute('''SELECT id,checkout_id,market_id,goods_krw,shipping_krw,discount_krw,total_krw,state,
                    created_at FROM gho.orders WHERE customer_subject=%s ORDER BY created_at DESC LIMIT 50''',(subject,))
        return cur.fetchall()

def demo_authorize(db,subject,order_id):
    oid=_parse_uuid(order_id)
    with db.transaction():
        with db.cursor() as cur:
            cur.execute("""UPDATE gho.orders SET state='authorized',updated_at=now()
                WHERE id=%s AND customer_subject=%s AND state='created' RETURNING id,state""",(oid,subject))
            result=cur.fetchone()
            if not result:raise Conflict('Order not eligible for demo authorization')
            cur.execute('''INSERT INTO gho.audit_events(actor_subject,actor_role,entity_type,entity_id,action)
                     VALUES(%s,'customer','order',%s,'demo_authorized_no_money')''',(subject,str(oid)))
    return {'demo':True,'id':str(oid),'state':'authorized','real_payment':False}

def cancel_checkout_order(db,subject,order_id):
    oid=_parse_uuid(order_id)
    with db.transaction():
        with db.cursor() as cur:
            cur.execute('SELECT gho.cancel_demo_order(%s,%s::uuid) AS result',(subject,oid))
            return cur.fetchone()['result']

def merchant_orders(db,subject,merchant_id):
    mid=_merchant_access(db,subject,merchant_id)
    with db.cursor() as cur:
        cur.execute('''SELECT o.id,o.market_id,o.state,o.created_at,f.state AS merchant_state,
                (SELECT jsonb_agg(jsonb_build_object('product',l.name_snapshot,'qty',l.qty,'unit_price_krw',l.unit_price_krw))
                 FROM gho.order_lines l WHERE l.order_id=o.id AND l.merchant_id=%s) AS lines
                FROM gho.orders o JOIN gho.merchant_fulfillments f ON f.order_id=o.id
                WHERE f.merchant_id=%s ORDER BY o.created_at DESC LIMIT 100''',(mid,mid))
        return cur.fetchall()

def merchant_progress(db,subject,merchant_id,order_id,desired):
    if desired not in ('accepted','ready'):raise ValueError('Unsupported merchant status')
    oid=_parse_uuid(order_id)
    with db.transaction():
        mid=_merchant_access(db,subject,merchant_id)
        with db.cursor() as cur:
            cur.execute('''SELECT f.state AS fs,o.state AS os FROM gho.merchant_fulfillments f
                JOIN gho.orders o ON o.id=f.order_id WHERE f.order_id=%s AND f.merchant_id=%s FOR UPDATE OF f,o''',(oid,mid))
            row=cur.fetchone()
            if not row:raise Forbidden('Order not assigned to this merchant')
            if row['os'] not in ('authorized','picking'):
                raise Conflict('A demo-authorized order is required')
            if (row['fs'],desired) not in (('pending','accepted'),('accepted','ready')):
                raise Conflict('Merchant transition out of order')
            cur.execute('UPDATE gho.merchant_fulfillments SET state=%s,updated_at=now() WHERE order_id=%s AND merchant_id=%s',
                        (desired,oid,mid))
            cur.execute("UPDATE gho.orders SET state='picking',updated_at=now() WHERE id=%s AND state='authorized'",(oid,))
    return {'demo':True,'order_id':str(oid),'merchant_id':str(mid),'state':desired}

def hub_collect(db,subject,market_id,order_id):
    oid=_parse_uuid(order_id)
    with db.transaction():
        if not (_grant(db,subject,'hub',market_id=market_id) or _grant(db,subject,'admin')):
            raise Forbidden('Not authorized for this market hub')
        with db.cursor() as cur:
            cur.execute('SELECT id,state FROM gho.orders WHERE id=%s AND market_id=%s FOR UPDATE',(oid,market_id))
            o=cur.fetchone()
            if not o:raise NotFound('Order does not belong to the market')
            if o['state']!='picking':raise Conflict('Order not in picking state')
            cur.execute('''SELECT count(*) AS all_count,count(*) FILTER (WHERE state='ready') AS ready_count
                        FROM gho.merchant_fulfillments WHERE order_id=%s''',(oid,))
            r=cur.fetchone()
            if not r['all_count'] or r['all_count']!=r['ready_count']:
                raise Conflict('All merchants must be ready')
            cur.execute('''UPDATE gho.orders SET state='hub_ready',updated_at=now() WHERE id=%s''',(oid,))
            cur.execute('''INSERT INTO gho.dispatch_jobs(order_id,market_id,state) VALUES(%s,%s,'waiting') RETURNING id''',
                      (oid,market_id))
            jid=cur.fetchone()['id']
    return {'demo':True,'order_id':str(oid),'job_id':str(jid),'state':'hub_ready'}

def assign_rider(db,subject,job_id,rider_subject):
    jid=_parse_uuid(job_id)
    if not isinstance(rider_subject,str) or not 4<=len(rider_subject)<=255:
        raise ValueError('Invalid rider subject')
    with db.transaction():
        with db.cursor() as cur:
            cur.execute('SELECT id,market_id,state,order_id FROM gho.dispatch_jobs WHERE id=%s FOR UPDATE',(jid,))
            job=cur.fetchone()
            if not job:raise NotFound('Dispatch job not found')
            if job['state']!='waiting':raise Conflict('Job already assigned')
            if not (_grant(db,subject,'hub',market_id=job['market_id']) or _grant(db,subject,'admin')):
                raise Forbidden('Not authorized for this market hub')
            if not _grant(db,rider_subject,'rider',market_id=job['market_id']):
                raise Forbidden('Rider is not enrolled in this market')
            cur.execute("UPDATE gho.dispatch_jobs SET rider_subject=%s,state='assigned',assigned_at=now() WHERE id=%s",(rider_subject,jid))
            cur.execute("UPDATE gho.orders SET state='assigned',updated_at=now() WHERE id=%s AND state='hub_ready'",(job['order_id'],))
            if cur.rowcount!=1:raise Conflict('Order not ready for assignment')
            cur.execute("INSERT INTO gho.audit_events(actor_subject,actor_role,entity_type,entity_id,action) VALUES(%s,'hub','dispatch',%s,'demo_assigned')",(subject,str(jid)))
    return {'demo':True,'job_id':str(jid),'state':'assigned','rider_subject':rider_subject}

def rider_progress(db,subject,job_id,action):
    if action not in ('pick-up','deliver'):raise ValueError('Invalid rider action')
    jid=_parse_uuid(job_id)
    expected='assigned' if action=='pick-up' else 'picked_up'
    target='picked_up' if action=='pick-up' else 'delivered'
    with db.transaction():
        with db.cursor() as cur:
            cur.execute('SELECT id,market_id,order_id,state,rider_subject FROM gho.dispatch_jobs WHERE id=%s FOR UPDATE',(jid,))
            job=cur.fetchone()
            if not job:raise NotFound('Dispatch job not found')
            if job['rider_subject']!=subject or not _grant(db,subject,'rider',market_id=job['market_id']):
                raise Forbidden('Not the assigned enrolled rider')
            if job['state']!=expected:raise Conflict('Invalid delivery state transition')
            cur.execute('''UPDATE gho.dispatch_jobs SET state=%s,completed_at=CASE WHEN %s='delivered' THEN now() ELSE completed_at END WHERE id=%s''',
                        (target,target,jid))
            cur.execute('UPDATE gho.orders SET state=%s,updated_at=now() WHERE id=%s AND state=%s',
                        (target,job['order_id'],expected))
            if cur.rowcount!=1:raise Conflict('Order state mismatch')
            cur.execute("INSERT INTO gho.audit_events(actor_subject,actor_role,entity_type,entity_id,action) VALUES(%s,'rider','dispatch',%s,%s)",
                        (subject,str(jid),'demo_'+target))
    return {'demo':True,'job_id':str(jid),'state':target}
