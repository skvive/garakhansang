"""Local-only API and static demo.  DO NOT expose this server to the public internet.

Only a local operator bearer secret can access admin routes; customer-specific
action tokens protect mock pay/cancel. NOT a production IdP or real payment processor.
"""
import argparse
import json
import os
import secrets
import hmac
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import domain

HERE=Path(__file__).resolve().parent
STATIC=HERE.parent / 'storefront'
PREFIX='/order/api/v1'

class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(STATIC),**kwargs)

    def log_message(self, fmt,*args):
        # No request bodies, personal data, cookies or secrets are logged.
        print('%s - %s' % (self.client_address[0],fmt%args))

    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Cache-Control','no-store')
        super().end_headers()

    @property
    def db_path(self):
        return self.server.db_path

    def reply(self,status,data):
        b=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def bearer(self):
        authorization=self.headers.get('Authorization','')
        return authorization[7:] if authorization.startswith('Bearer ') else ''

    def role(self):
        token=self.bearer()
        if token and hmac.compare_digest(token, self.server.admin_token):
            return 'admin'
        return 'customer'

    def guard_origin(self):
        origin=self.headers.get('Origin','')
        if not origin:
            return
        # Local development only. Reject POSTs from arbitrary external websites.
        allowed={f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}
        if origin not in allowed:
            raise domain.DomainError('다른 출처에서 요청할 수 없습니다',403)

    def body_json(self):
        ct=self.headers.get('Content-Type','').split(';')[0].strip()
        if ct!='application/json':raise domain.DomainError('application/json만 허용',415)
        try: size=int(self.headers.get('Content-Length','0'))
        except ValueError:raise domain.DomainError('Content-Length 오류')
        if size<1 or size>65536:raise domain.DomainError('JSON 본문 크기 1~65536 바이트')
        try:
            body=json.loads(self.rfile.read(size))
            if not isinstance(body,dict):raise ValueError('object required')
            return body
        except (UnicodeError,ValueError):raise domain.DomainError('JSON 객체 형식 오류')

    def perform(self,mode):
        path=urlsplit(self.path).path
        if not path.startswith(PREFIX):
            if mode=='GET':return super().do_GET()
            return self.reply(404,{'error':'endpoint_not_found'})
        route=path[len(PREFIX):].rstrip('/') or '/'
        query=parse_qs(urlsplit(self.path).query)
        db=domain.db_connect(self.db_path)
        try:
            if mode=='GET':
                if route=='/health':return self.reply(200,{'ok':True,'mode':'demo','payments':'mock_only','authentication':'not_for_production'})
                if route=='/markets':return self.reply(200,domain.markets(db))
                if route=='/merchants':return self.reply(200,domain.merchants(db,query.get('market_id',[None])[0]))
                if route=='/products':return self.reply(200,domain.products(db,query.get('market_id',[None])[0]))
                if route=='/orders':
                    domain.require_role(self.role(),{'admin','hub','merchant','rider'})
                    all_orders=domain.get_orders(db,query.get('market_id',[None])[0])
                    if self.role()=='merchant':
                        merchant_id=query.get('merchant_id',[''])[0]
                        if not merchant_id:raise domain.DomainError('merchant_id 필수',400)
                        all_orders=[x for x in all_orders if any(f['merchant_id']==merchant_id for f in x['fulfillment'])]
                    return self.reply(200,all_orders)
                if route=='/dashboard':
                    domain.require_role(self.role(),{'admin','hub'})
                    return self.reply(200,domain.dashboard(db))
                return self.reply(404,{'error':'unknown_api_route'})
            self.guard_origin()
            payload=self.body_json()
            if mode=='POST':
                if route=='/merchants/apply':return self.reply(201,domain.apply_merchant(db,payload,self.role()))
                if route=='/orders':return self.reply(201,domain.create_orders(db,payload,self.headers.get('Idempotency-Key',''),self.role()))
                m=re.fullmatch(r'/merchants/([^/]+)/approve',route)
                if m:return self.reply(200,domain.approve_merchant(db,m[1],self.role()))
                m=re.fullmatch(r'/merchants/([^/]+)/products/([^/]+)/stock',route)
                if m:return self.reply(200,domain.update_stock(db,m[1],m[2],payload.get('stock'),self.role()))
                m=re.fullmatch(r'/orders/([^/]+)/mock-pay',route)
                if m:return self.reply(200,domain.mock_pay(db,m[1],self.role(),self.bearer()))
                m=re.fullmatch(r'/orders/([^/]+)/cancel',route)
                if m:return self.reply(200,domain.cancel_order(db,m[1],self.role(),self.bearer()))
                m=re.fullmatch(r'/orders/([^/]+)/merchants/([^/]+)/status',route)
                if m:return self.reply(200,domain.merchant_status(db,m[1],m[2],payload.get('status'),self.role()))
                m=re.fullmatch(r'/orders/([^/]+)/hub-collect',route)
                if m:return self.reply(200,domain.hub_collect(db,m[1],self.role()))
                m=re.fullmatch(r'/dispatch/([^/]+)/(assign|pick-up|deliver)',route)
                if m:return self.reply(200,domain.dispatch_update(db,m[1],m[2].replace('-','_'),str(payload.get('rider_alias','')).strip(),self.role()))
                return self.reply(404,{'error':'unknown_api_route'})
            return self.reply(405,{'error':'method_not_allowed'})
        except domain.DomainError as e:
            return self.reply(e.status,{'error':str(e),'demo':True})
        except Exception as e:
            print('Internal error:', type(e).__name__)
            return self.reply(500,{'error':'내부 데모 서버 오류'})
        finally:
            db.close()

    def do_GET(self):self.perform('GET')
    def do_POST(self):self.perform('POST')


def main():
    parser=argparse.ArgumentParser(description='Garak Hansang Order LOOPBACK ONLY demo')
    parser.add_argument('--port',type=int,default=8768)
    parser.add_argument('--db',default=str(HERE/'demo.sqlite'))
    args=parser.parse_args()
    domain.init_db(args.db)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),AppHandler)
    server.db_path=args.db
    server.admin_token=os.environ.get('GHO_DEMO_ADMIN_TOKEN') or secrets.token_urlsafe(32)
    if len(server.admin_token)<24:raise SystemExit('GHO_DEMO_ADMIN_TOKEN 은 24자 이상 설정하세요')
    print(f'Garak Hansang Order LOCAL DEMO: http://127.0.0.1:{args.port}/order/')
    print(f'운영 콘솔: http://127.0.0.1:{args.port}/order/ops.html')
    print('LOCAL DEMO ADMIN TOKEN (do not share): '+server.admin_token,flush=True)
    print('REAL PAYMENTS DISABLED / BEARER TOKEN ONLY FOR LOCAL DEMO',flush=True)
    try:server.serve_forever()
    finally:server.server_close()

if __name__=='__main__':main()
