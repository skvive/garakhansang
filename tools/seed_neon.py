"""Write Postgres DDL for MCP apply. Does not print secrets."""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from admin_core.database import SCHEMA
from admin_core.pgcompat import postgres_schema

out = ROOT / "runtime"
out.mkdir(exist_ok=True)
sql = postgres_schema(SCHEMA)
(out / "neon_schema.sql").write_text(sql, encoding="utf-8")
parts = [s.strip() for s in sql.split(";") if s.strip()]
print("schema_statements", len(parts))
