"""Local beta persistence, synthetic test data only. No real payments or seller identities."""
from __future__ import annotations
import os, sqlite3, json, secrets, hashlib, datetime as dt
from pathlib import Path
from .pgcompat import use_postgres, backend_name, _connect_postgres

HERE=Path(__file__).resolve().parents[1]
DEFAULT_DB=HERE/'runtime'/'garak_beta.sqlite3'
SCHEMA=r'''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('superadmin','ops','content','finance','support')), active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(id_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),csrf TEXT NOT NULL,expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS merchants(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,kind TEXT NOT NULL CHECK(kind IN ('seafood','meat','produce','other')),contact TEXT NOT NULL DEFAULT '', commission_bps INTEGER NOT NULL DEFAULT 800 CHECK(commission_bps BETWEEN 0 AND 4000),verified INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','active','rejected','suspended')),created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,slug TEXT NOT NULL UNIQUE,name TEXT NOT NULL,category TEXT NOT NULL,merchant_id INTEGER REFERENCES merchants(id),price INTEGER NOT NULL CHECK(price>=0),stock INTEGER NOT NULL CHECK(stock>=0),status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','published','hidden')),image TEXT NOT NULL DEFAULT '',origin TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS inventory_moves(id INTEGER PRIMARY KEY,product_id INTEGER NOT NULL REFERENCES products(id),delta INTEGER NOT NULL,reason TEXT NOT NULL,reference TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,actor_id INTEGER REFERENCES users(id));
CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT NOT NULL DEFAULT '',consent INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,customer_id INTEGER REFERENCES customers(id),reference TEXT NOT NULL UNIQUE,status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','paid_test','processing','shipped','delivered','canceled')),payment_mode TEXT NOT NULL DEFAULT 'simulation',subtotal INTEGER NOT NULL CHECK(subtotal>=0),delivery_fee INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL REFERENCES orders(id),product_id INTEGER NOT NULL REFERENCES products(id),merchant_id INTEGER REFERENCES merchants(id),qty INTEGER NOT NULL CHECK(qty>0),unit_price INTEGER NOT NULL CHECK(unit_price>=0));
CREATE TABLE IF NOT EXISTS shipments(id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id),carrier TEXT NOT NULL DEFAULT '',tracking TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','ready','shipped','delivered')),updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS recipes(id INTEGER PRIMARY KEY,source_id TEXT NOT NULL UNIQUE,title TEXT NOT NULL,category TEXT NOT NULL,main_ingredient TEXT NOT NULL,product_slug TEXT NOT NULL DEFAULT '',image TEXT NOT NULL DEFAULT '',minutes INTEGER NOT NULL DEFAULT 20,content TEXT NOT NULL DEFAULT '{}',status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','published','hidden')),reviewed INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS creators(id INTEGER PRIMARY KEY,name TEXT NOT NULL,platform TEXT NOT NULL DEFAULT 'blogger',url TEXT NOT NULL DEFAULT '',verified INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','active','suspended')),created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY,category TEXT NOT NULL CHECK(category IN ('merchants','distributors','associations','collaboration','chef')),organization TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,creator_id INTEGER REFERENCES creators(id),merchant_id INTEGER REFERENCES merchants(id),is_ad INTEGER NOT NULL DEFAULT 0,verified INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected','archived')),created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS campaigns(id INTEGER PRIMARY KEY,name TEXT NOT NULL,placement TEXT NOT NULL DEFAULT 'homepage',budget INTEGER NOT NULL DEFAULT 0 CHECK(budget>=0),spent INTEGER NOT NULL DEFAULT 0 CHECK(spent>=0),status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','active','paused','completed')),sponsored INTEGER NOT NULL DEFAULT 1,start_date TEXT NOT NULL DEFAULT '',end_date TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ad_events(id INTEGER PRIMARY KEY,campaign_id INTEGER NOT NULL REFERENCES campaigns(id),event_type TEXT NOT NULL CHECK(event_type IN ('impression','click','conversion')),order_id INTEGER REFERENCES orders(id),created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS integrations(id INTEGER PRIMARY KEY,provider TEXT NOT NULL UNIQUE,enabled INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'not_configured',description TEXT NOT NULL DEFAULT '',last_sync TEXT,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY,subject TEXT NOT NULL,category TEXT NOT NULL DEFAULT 'order',customer_id INTEGER REFERENCES customers(id),status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','working','resolved')),assignee_id INTEGER REFERENCES users(id),created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settlements(id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL,merchant_id INTEGER NOT NULL REFERENCES merchants(id),gross INTEGER NOT NULL,fee INTEGER NOT NULL,payout INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','approved','paid')),created_at TEXT NOT NULL,UNIQUE(order_id,merchant_id),FOREIGN KEY(order_id) REFERENCES orders(id));
CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY,actor_id INTEGER REFERENCES users(id),action TEXT NOT NULL,target TEXT NOT NULL,target_id INTEGER,old_json TEXT,new_json TEXT,at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS page_events(id INTEGER PRIMARY KEY,event_name TEXT NOT NULL,path TEXT NOT NULL DEFAULT '',session_anonymous TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orderitems_product ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_product ON inventory_moves(product_id);
CREATE INDEX IF NOT EXISTS idx_audit_at ON audit_logs(at);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_recipes_status ON recipes(status);
'''

def now():return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
class ClosingConnection(sqlite3.Connection):
    """Commit or roll back at context exit, then close the connection (sqlite3's default does not)."""
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()

def connect(path=None):
    if use_postgres():
        return _connect_postgres()
    db=Path(path or os.environ.get('GARAK_ADMIN_DB',str(DEFAULT_DB)))
    db.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(str(db), timeout=10, isolation_level=None, factory=ClosingConnection)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON');con.execute('PRAGMA busy_timeout=10000');con.execute('PRAGMA journal_mode=WAL')
    return con

def password_hash(password,salt=None):
    salt=salt or secrets.token_bytes(16)
    raw=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,600_000)
    return 'pbkdf2_sha256$600000$'+salt.hex()+'$'+raw.hex()

def password_valid(password,hashval):
    try:
        algo, rounds, salt, expected=hashval.split('$')
        if algo!='pbkdf2_sha256':return False
        dig=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),int(rounds))
        return secrets.compare_digest(dig,bytes.fromhex(expected))
    except (ValueError,TypeError):return False

def init_db(path=None,seed=True, bootstrap=True):
    con=connect(path)
    con.executescript(SCHEMA)
    c=con.execute('SELECT COUNT(*) n FROM users').fetchone()['n']
    if c==0 and bootstrap:
        password=os.environ.get('GARAK_BOOTSTRAP_PASSWORD') or secrets.token_urlsafe(18)
        if len(password)<14:raise ValueError('Bootstrap password must contain at least 14 characters')
        con.execute('INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)',('admin',password_hash(password),'superadmin',now()))
        # Store ONLY for local interactive SQLite setup. Cloud uses GARAK_BOOTSTRAP_PASSWORD.
        if not use_postgres():
            credential=Path(path).parent/'FIRST_LOGIN_LOCAL_ONLY.txt' if path else Path(os.environ.get('GARAK_ADMIN_DB',str(DEFAULT_DB))).parent/'FIRST_LOGIN_LOCAL_ONLY.txt'
            credential.parent.mkdir(parents=True,exist_ok=True)
            credential.write_text('LOCAL BETA ONLY. Delete after first login.\nUsername: admin\nPassword: '+password+'\n',encoding='utf-8')
            try:credential.chmod(0o600)
            except OSError:pass
    if seed and con.execute('SELECT COUNT(*) n FROM products').fetchone()['n']==0:seed_beta(con)
    return con

def seed_beta(con):
    """Seed clearly-labelled synthetic beta fixtures, not production orders, merchant verification or revenue."""
    products=json.loads((HERE/'storefront'/'assets'/'products.json').read_text(encoding='utf-8'))
    recipes=json.loads((HERE/'storefront'/'assets'/'recipes.json').read_text(encoding='utf-8'))
    group={'seafood':'seafood','meat':'meat','produce':'produce','sets':'other','extras':'other'}
    for p in products:
        m=con.execute('SELECT id FROM merchants WHERE name=?',(p['merchant'],)).fetchone()
        if not m:
            cur=con.execute('INSERT INTO merchants(name,kind,contact,verified,status,created_at) VALUES(?,?,?,?,?,?)',(p['merchant'],group.get(p['category'],'other'),'[데모] 확인 필요',0,'pending',now()))
            mid=cur.lastrowid
        else:mid=m['id']
        con.execute('INSERT INTO products(slug,name,category,merchant_id,price,stock,status,image,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(p['slug'],p['name'],p['category'],mid,p['price'],20,'published',f"assets/images/{p['image']}.webp",now()))
    for i,r in enumerate(recipes):
        con.execute('INSERT INTO recipes(source_id,title,category,main_ingredient,product_slug,image,minutes,content,status,reviewed,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
        (r['id'],r['title'],r['category'],r['main'],r.get('sku',''),r.get('photo',''),r['time'],json.dumps({'ingredients':r.get('ingredients',[]),'steps':r.get('steps',[]),'photo_caption':r.get('photo_caption','')},ensure_ascii=False),'draft',0,now()))
    for provider,description in [
      ('Google Blogger','OAuth 2.0 승인 및 게시물 동기화 필요'),('YouTube','OAuth 및 영상 사용권 확인 필요'),('Coupang WING','사업자 API 키 및 상품매핑 필요'),('Coupang Eats','공식 입점/제휴 승인 필요'),('Baemin','공식 입점/제휴 승인 필요'),('Toss Payments','승인·서버 검증·Webhook 구성 필요'),('Neon PostgreSQL','운영 데이터 마이그레이션 미실행'),('Vercel','운영 배포 별도 검증 필요')]:
      con.execute('INSERT INTO integrations(provider,description,updated_at) VALUES(?,?,?)',(provider,description,now()))
    # A few synthetic records support measurable beta KPIs, never identified as real transactions.
    con.execute('INSERT INTO customers(name,email,created_at) VALUES(?,?,?)',('[데모] 고객 A','',now()))
    con.execute('INSERT INTO creators(name,platform,status,created_at) VALUES(?,?,?,?)',('[데모] 요리 연구가','blogger','pending',now()))
    con.execute("INSERT INTO posts(category,organization,title,body,is_ad,status,created_at) VALUES(?,?,?,?,?,?,?)",('merchants','[데모] 가락시장 점포','[데모] 제철 수산물 소개','실제 사업자 인증과 관리자 승인을 완료한 게시물만 공개됩니다.',1,'pending',now()))
    con.execute("INSERT INTO campaigns(name,placement,budget,status,created_at) VALUES(?,?,?,?,?)",('[데모] 제철 수산 기획전','homepage',150000,'draft',now()))
    con.execute("INSERT INTO tickets(subject,status,created_at) VALUES(?,?,?)",('[데모] 배송 문의','open',now()))
    con.execute("INSERT INTO page_events(event_name,path,created_at) VALUES(?,?,?)",('page_view','/',now()))
    con.execute("INSERT INTO page_events(event_name,path,created_at) VALUES(?,?,?)",('view_product','/product/bangeo-hoe.html',now()))
    return {'products':len(products),'recipes':len(recipes)}
