"""Garak Hansang Order V5 — disabled-by-default Neon demo API.
No real payments, shipping addresses, real riders, or external production service.
"""
from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field
from contextlib import contextmanager
from datetime import datetime
import os
import uuid
from .auth_v5 import verify_oidc, AuthenticationError
from . import repository_v5 as repo
from .mobile_app_contract import build_mobile_bootstrap

app=FastAPI(title='Garak Hansang Order V5 (DEVELOPMENT DEMO)',docs_url=None,redoc_url=None,openapi_url=None)
security=HTTPBearer(auto_error=False)

class CartLine(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id: str=Field(min_length=1,max_length=90)
    qty: int=Field(ge=1,le=99)
    proc: str=''
class Checkout(BaseModel):
    model_config=ConfigDict(extra='forbid')
    lines: list[CartLine]=Field(min_length=1,max_length=80)
class Progress(BaseModel):
    model_config=ConfigDict(extra='forbid')
    state: str

def get_subject(credentials:HTTPAuthorizationCredentials|None=Depends(security)):
    if credentials is None or credentials.scheme.lower()!='bearer':
        raise HTTPException(401,'Bearer authentication required',headers={'WWW-Authenticate':'Bearer'})
    try:return verify_oidc(credentials.credentials).sub
    except AuthenticationError as exc:raise HTTPException(401,str(exc)) from exc

def get_db():
    try:
        with repo.open_db() as db:yield db
    except repo.StorageUnavailable as exc:raise HTTPException(503,str(exc)) from exc

def _do(fn):
    try:return fn()
    except repo.Forbidden as e:raise HTTPException(403,str(e)) from e
    except repo.NotFound as e:raise HTTPException(404,str(e)) from e
    except repo.Conflict as e:raise HTTPException(409,str(e)) from e
    except ValueError as e:raise HTTPException(400,str(e)) from e
    except Exception as e:
        try:
            import psycopg
            if isinstance(e,psycopg.errors.UniqueViolation):raise HTTPException(409,'Duplicate idempotency key') from e
            if isinstance(e,psycopg.errors.InvalidParameterValue):raise HTTPException(400,'Invalid cart or checkout request') from e
            if isinstance(e,psycopg.errors.InsufficientPrivilege):raise HTTPException(403,'Insufficient database privileges') from e
            if isinstance(e,psycopg.errors.CheckViolation):raise HTTPException(409,'Inventory or state conflict') from e
            if isinstance(e,psycopg.errors.RaiseException):raise HTTPException(409,'Order validation failed') from e
        except ImportError:pass
        raise

def get_catalog_db():
    try:
        with repo.open_catalog_db() as db: yield db
    except repo.StorageUnavailable as exc: raise HTTPException(503,str(exc)) from exc

@app.middleware('http')
async def security_headers(request:Request,call_next):
    # No wildcard CORS; token authorization required for all mutations.
    response=await call_next(request)
    response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
                             'Referrer-Policy':'no-referrer','X-Frame-Options':'DENY'})
    return response

@app.get('/order/api/v5/mobile/bootstrap')
def mobile_bootstrap():
    """Non-sensitive feature flags: always disabled for real commerce in V5."""
    return build_mobile_bootstrap()

@app.get('/order/api/v5/health')
def health():
    return {'api':'v5','demo':True,'real_payments':False,
            'neon_enabled':bool(os.getenv('GHO_NEON_DSN') and os.getenv('GHO_V5_MODE')=='isolated-dev'),
            'oidc_configured':bool(os.getenv('GHO_NEON_AUTH_BASE_URL') and os.getenv('GHO_OIDC_ISSUER') and os.getenv('GHO_OIDC_AUDIENCE') and os.getenv('GHO_OIDC_JWKS_URL'))}

@app.get('/order/api/v5/catalog')
def catalog(market_id:str|None=None,db=Depends(get_catalog_db)):
    return _do(lambda:repo.catalog(db,market_id))

@app.post('/order/api/v5/checkouts',status_code=201)
def checkout(payload:Checkout,idempotency_key:str=Header(alias='Idempotency-Key'),subject:str=Depends(get_subject),db=Depends(get_db)):
    return _do(lambda:repo.create_checkout(db,subject,idempotency_key,[x.model_dump() for x in payload.lines]))

@app.get('/order/api/v5/orders')
def orders(subject:str=Depends(get_subject),db=Depends(get_db)):
    return _do(lambda:repo.customer_orders(db,subject))

@app.post('/order/api/v5/orders/{order_id}/demo-authorize')
def authorize(order_id:str,subject:str=Depends(get_subject),db=Depends(get_db)):
    return _do(lambda:repo.demo_authorize(db,subject,order_id))

@app.post('/order/api/v5/orders/{order_id}/cancel')
def cancel(order_id:str,subject:str=Depends(get_subject),db=Depends(get_db)):
    return _do(lambda:repo.cancel_checkout_order(db,subject,order_id))

@app.get('/order/api/v5/merchants/{merchant_id}/orders')
def merchant_orders(merchant_id:str,subject:str=Depends(get_subject),db=Depends(get_db)):
    return _do(lambda:repo.merchant_orders(db,subject,merchant_id))

@app.post('/order/api/v5/merchants/{merchant_id}/orders/{order_id}/status')
def merchant_progress(merchant_id:str,order_id:str,payload:Progress,subject:str=Depends(get_subject),db=Depends(get_db)):
    return _do(lambda:repo.merchant_progress(db,subject,merchant_id,order_id,payload.state))

@app.post('/order/api/v5/markets/{market_id}/orders/{order_id}/hub-collect')
def collect(market_id:str,order_id:str,subject:str=Depends(get_subject),db=Depends(get_db)):
    return _do(lambda:repo.hub_collect(db,subject,market_id,order_id))

class Assignment(BaseModel):
    model_config=ConfigDict(extra='forbid')
    rider_subject: str=Field(min_length=4,max_length=255)

@app.post('/order/api/v5/dispatch/jobs/{job_id}/assign')
def assign(job_id:str,payload:Assignment,subject:str=Depends(get_subject),db=Depends(get_db)):
    return _do(lambda:repo.assign_rider(db,subject,job_id,payload.rider_subject))

@app.post('/order/api/v5/dispatch/jobs/{job_id}/{action}')
def ride(job_id:str,action:str,subject:str=Depends(get_subject),db=Depends(get_db)):
    return _do(lambda:repo.rider_progress(db,subject,job_id,action))
