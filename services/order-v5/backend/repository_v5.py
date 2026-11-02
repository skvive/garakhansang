"""V5 catalog read-only DB, strict restricted account; V4 demo writes remain DEV-only."""
import os
from urllib.parse import urlsplit,parse_qs,unquote
from contextlib import contextmanager
from .repository_v4 import *
from .repository_v4 import StorageUnavailable
HOST='ep-gentle-wind-b5ir41pn.c-7.us-east-2.aws.neon.tech'
@contextmanager
def open_catalog_db():
    if os.getenv('GHO_V4_MODE')!='isolated-dev':
        raise StorageUnavailable('Isolated development required')
    dsn=os.getenv('GHO_CATALOG_READ_DSN','')
    p=urlsplit(dsn)
    if p.scheme not in ('postgres','postgresql') or p.hostname!=HOST or unquote(p.username or '')!='gho_catalog_runtime_v5':
        raise StorageUnavailable('Unapproved catalog DB account or branch')
    if parse_qs(p.query).get('sslmode',[''])[0]!='verify-full':
        raise StorageUnavailable('Verified TLS required')
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as e: raise StorageUnavailable('psycopg required') from e
    with psycopg.connect(dsn,row_factory=dict_row,connect_timeout=5,autocommit=False) as db:
        with db.transaction():
            with db.cursor() as cur:
                cur.execute('SET TRANSACTION READ ONLY')
                cur.execute("SELECT current_user AS name,rolbypassrls,rolcreaterole FROM pg_roles WHERE rolname=current_user")
                r=cur.fetchone()
                if not r or r['name']!='gho_catalog_runtime_v5' or r['rolbypassrls'] or r['rolcreaterole']:
                    raise StorageUnavailable('Unsafe database role')
            yield db
