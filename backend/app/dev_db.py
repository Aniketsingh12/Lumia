"""
In-memory database for local dev when Supabase is not configured.
Activated automatically when SUPABASE_URL is blank or a placeholder.

Pre-seeded accounts:
  admin@botforge.dev  / admin123
  demo@botforge.app   / demo123
  test@test.com       / test123
"""

import uuid
from passlib.hash import bcrypt

# ── Seed data ──────────────────────────────────────────────────────────────
_ORG_ID = "00000000-0000-0000-0000-000000000001"
_USERS: list[dict] = []

def _seed():
    accounts = [
        ("admin@botforge.dev",   "admin123", "Admin User"),
        ("demo@botforge.app",    "demo123",  "Demo User"),
        ("test@test.com",        "test123",  "Test User"),
    ]
    for email, password, name in accounts:
        _USERS.append({
            "id": str(uuid.uuid4()),
            "email": email,
            "full_name": name,
            "password_hash": bcrypt.hash(password),
            "org_id": _ORG_ID,
            "role": "owner",
        })

_seed()

_ORGS: list[dict] = [{"id": _ORG_ID, "name": "Dev Org", "plan": "free", "owner_id": _USERS[0]["id"]}]

# ── QuerySet shim — mimics Supabase client chaining ───────────────────────
class _Result:
    def __init__(self, data): self.data = data

class _Query:
    def __init__(self, rows):
        self._backing = rows          # the real table list — mutate for insert/delete
        self._rows = list(rows)       # snapshot — safe to filter/slice for reads
        self._filters: list[tuple] = []
        self._update_data: dict | None = None
        self._delete = False
        self._insert_data: dict | None = None
        self._cols: list[str] | None = None
        self._limit: int | None = None

    def select(self, cols="*", count=None):
        # `count` is accepted for API compat but not implemented; callers that need
        # exact counts should use len(result.data) instead in dev mode.
        self._cols = None if cols == "*" else [c.strip() for c in cols.split(",")]
        return self

    def insert(self, data: dict):
        self._insert_data = data
        return self

    def update(self, data: dict):
        self._update_data = data
        return self

    def delete(self):
        self._delete = True
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def order(self, col: str, desc: bool = False):
        # Sort the current snapshot by `col`; desc=True for descending order.
        self._rows = sorted(
            self._rows,
            key=lambda r: (r.get(col) is None, r.get(col)),
            reverse=desc,
        )
        return self

    def limit(self, n):
        self._limit = n
        return self

    def execute(self) -> _Result:
        # INSERT — append to the real backing list so it persists
        if self._insert_data is not None:
            self._backing.append(self._insert_data)
            return _Result([dict(self._insert_data)])

        # Filter (read snapshot)
        rows = self._rows
        for col, val in self._filters:
            rows = [r for r in rows if r.get(col) == val]

        # UPDATE — mutate the shared row dicts in place
        if self._update_data is not None:
            for r in rows:
                r.update(self._update_data)
            return _Result([dict(r) for r in rows])

        # DELETE — remove from the real backing list
        if self._delete:
            for r in rows:
                if r in self._backing:
                    self._backing.remove(r)
            return _Result([])

        # SELECT — apply limit, then return copies so callers can't mutate the store
        if self._limit is not None:
            rows = rows[: self._limit]
        if self._cols:
            rows = [{c: r[c] for c in self._cols if c in r} for r in rows]
        else:
            rows = [dict(r) for r in rows]
        return _Result(rows)


class _Table:
    _tables: dict[str, list] = {
        "users": _USERS,
        "organizations": _ORGS,
        "bots": [],
        "conversations": [],
        "messages": [],
        "knowledge_bases": [],
        "documents": [],
    }

    def __init__(self, name: str):
        if name not in self._tables:
            self._tables[name] = []
        self._rows = self._tables[name]

    def select(self, cols="*"): return _Query(self._rows).select(cols)
    def insert(self, data): return _Query(self._rows).insert(data)
    def update(self, data): return _Query(self._rows).update(data)
    def delete(self): return _Query(self._rows).delete()


class DevDB:
    """Drop-in replacement for the Supabase client in dev mode."""
    def table(self, name: str) -> _Table:
        return _Table(name)


_dev_db = DevDB()

def get_dev_db() -> DevDB:
    return _dev_db
