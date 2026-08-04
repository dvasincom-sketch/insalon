"""Синхронный шим над PostgreSQL с интерфейсом supabase-py v2.

Переключает доступ к данным с Supabase (PostgREST) на управляемый Postgres,
меняя только объект `supabase` (через DB_BACKEND в database.py), без правки
242 вызовов. Покрывает используемую в коде поверхность:
table/select/insert/update/upsert/delete + eq/neq/gt/gte/lt/lte/ilike/like/
is_/in_/or_ + order/limit/range/single/maybe_single/execute. RPC не используется.
"""
import os
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import ConnectionPool
from datetime import date as _date, datetime as _datetime, time as _time
from decimal import Decimal as _Decimal
from uuid import UUID as _UUID


def _dsn():
    dsn = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
    if dsn:
        return dsn
    return (f"host={os.getenv('PGHOST','localhost')} port={os.getenv('PGPORT','5432')} "
            f"dbname={os.getenv('PGDATABASE','postgres')} user={os.getenv('PGUSER','postgres')} "
            f"password={os.getenv('PGPASSWORD','')}")


_pool = None
def _get_pool():
    global _pool
    if _pool is None:
        _pool = ConnectionPool(_dsn(), min_size=1,
                               max_size=int(os.getenv("PG_POOL_MAX", "8")),
                               kwargs={"row_factory": dict_row}, open=True)
    return _pool


def _val(v):
    return Json(v) if isinstance(v, (dict, list)) else v


def _jsonify(v):
    """Привести типы psycopg к JSON-виду Supabase: даты->ISO-строки, Decimal->число, UUID->str."""
    if isinstance(v, (_datetime, _date, _time)):
        return v.isoformat()
    if isinstance(v, _Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    if isinstance(v, _UUID):
        return str(v)
    return v


_OPMAP = {"eq": "=", "neq": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=",
          "like": "LIKE", "ilike": "ILIKE"}

def _parse_or(expr):
    clauses, params = [], []
    for part in expr.split(","):
        seg = part.split(".", 2)
        if len(seg) < 2:
            continue
        col, op = seg[0], seg[1]
        val = seg[2] if len(seg) > 2 else ""
        if op == "is":
            low = val.lower()
            if low == "null": clauses.append(f'"{col}" IS NULL')
            elif low == "true": clauses.append(f'"{col}" IS TRUE')
            elif low == "false": clauses.append(f'"{col}" IS FALSE')
            else: clauses.append(f'"{col}" IS %s'); params.append(val)
        else:
            sqlop = _OPMAP.get(op)
            if not sqlop:
                raise ValueError(f"or_: неподдерживаемый оператор '{op}' в {expr!r}")
            clauses.append(f'"{col}" {sqlop} %s'); params.append(val)
    return " OR ".join(clauses), params


class _Result:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _Query:
    def __init__(self, table):
        self._t = table
        self._verb = "select"
        self._cols = "*"
        self._payload = None
        self._on_conflict = None
        self._filters = []
        self._order = []
        self._limit = None
        self._offset = None
        self._single = False

    def select(self, columns="*", count=None):
        self._verb, self._cols = "select", (columns or "*"); return self
    def insert(self, payload):
        self._verb, self._payload = "insert", payload; return self
    def upsert(self, payload, on_conflict=None):
        self._verb, self._payload, self._on_conflict = "upsert", payload, on_conflict; return self
    def update(self, payload):
        self._verb, self._payload = "update", payload; return self
    def delete(self):
        self._verb = "delete"; return self

    def _add(self, col, op, val):
        self._filters.append((f'"{col}" {op} %s', [val])); return self
    def eq(self, c, v): return self._add(c, "=", v)
    def neq(self, c, v): return self._add(c, "<>", v)
    def gt(self, c, v): return self._add(c, ">", v)
    def gte(self, c, v): return self._add(c, ">=", v)
    def lt(self, c, v): return self._add(c, "<", v)
    def lte(self, c, v): return self._add(c, "<=", v)
    def like(self, c, v): return self._add(c, "LIKE", v)
    def ilike(self, c, v): return self._add(c, "ILIKE", v)
    def is_(self, c, v):
        if v is None or (isinstance(v, str) and v.lower() == "null"):
            self._filters.append((f'"{c}" IS NULL', []))
        elif isinstance(v, bool) or (isinstance(v, str) and v.lower() in ("true", "false")):
            b = v if isinstance(v, bool) else (v.lower() == "true")
            self._filters.append((f'"{c}" IS {"TRUE" if b else "FALSE"}', []))
        else:
            self._filters.append((f'"{c}" IS %s', [v]))
        return self
    def in_(self, c, vals):
        vals = list(vals)
        if not vals:
            self._filters.append(("FALSE", [])); return self
        ph = ",".join(["%s"] * len(vals))
        self._filters.append((f'"{c}" IN ({ph})', vals)); return self
    def or_(self, expr):
        sql, params = _parse_or(expr)
        self._filters.append((f"({sql})", params)); return self

    def order(self, col, desc=False):
        self._order.append((col, bool(desc))); return self
    def limit(self, n):
        self._limit = int(n); return self
    def range(self, start, end):
        self._offset = int(start); self._limit = int(end) - int(start) + 1; return self
    def single(self):
        self._single = True; return self
    def maybe_single(self):
        self._single = True; return self

    def _where(self):
        if not self._filters:
            return "", []
        parts, params = [], []
        for sql, p in self._filters:
            parts.append(sql); params.extend(p)
        return " WHERE " + " AND ".join(parts), params

    def _build(self):
        t = f'"{self._t}"'
        if self._verb == "select":
            where, params = self._where()
            order = ""
            if self._order:
                order = " ORDER BY " + ", ".join(f'"{c}" {"DESC" if d else "ASC"}' for c, d in self._order)
            lim = f" LIMIT {self._limit}" if self._limit is not None else ""
            off = f" OFFSET {self._offset}" if self._offset else ""
            return f"SELECT {self._cols} FROM {t}{where}{order}{lim}{off}", params
        if self._verb in ("insert", "upsert"):
            rows = self._payload if isinstance(self._payload, list) else [self._payload]
            cols = list(rows[0].keys())
            colsql = ", ".join(f'"{c}"' for c in cols)
            ph_rows, params = [], []
            for r in rows:
                ph_rows.append("(" + ", ".join(["%s"] * len(cols)) + ")")
                params.extend(_val(r.get(c)) for c in cols)
            sql = f"INSERT INTO {t} ({colsql}) VALUES " + ", ".join(ph_rows)
            if self._verb == "upsert":
                conflict = self._on_conflict or "id"
                keys = [c.strip() for c in conflict.split(",")]
                cc = ", ".join(f'"{c}"' for c in keys)
                upd = ", ".join(f'"{c}"=EXCLUDED."{c}"' for c in cols if c not in keys)
                sql += (f" ON CONFLICT ({cc}) DO UPDATE SET {upd}" if upd
                        else f" ON CONFLICT ({cc}) DO NOTHING")
            return sql + " RETURNING *", params
        if self._verb == "update":
            setsql = ", ".join(f'"{c}"=%s' for c in self._payload.keys())
            params = [_val(v) for v in self._payload.values()]
            where, wp = self._where(); params += wp
            return f"UPDATE {t} SET {setsql}{where} RETURNING *", params
        if self._verb == "delete":
            where, params = self._where()
            return f"DELETE FROM {t}{where} RETURNING *", params
        raise ValueError(self._verb)

    def execute(self):
        sql, params = self._build()
        with _get_pool().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall() if cur.description else []
        rows = [{k: _jsonify(v) for k, v in r.items()} for r in rows]
        if self._single:
            return _Result(rows[0] if rows else None)
        return _Result(rows)


class PgClient:
    def table(self, name):
        return _Query(name)


supabase = PgClient()
