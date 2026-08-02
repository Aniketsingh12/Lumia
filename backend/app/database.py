"""
=============================================================================
BotForge — database.py (DATABASE CONNECTION & HELPERS)
=============================================================================

THIS FILE MANAGES THE CONNECTION TO SUPABASE (our PostgreSQL database).

WHAT IS SUPABASE?
  Supabase is an open-source Firebase alternative. It gives us:
  1. PostgreSQL database (stores users, bots, conversations, messages)
  2. Authentication (user signup/login)
  3. File Storage (uploaded PDFs, images)
  4. Realtime subscriptions (live updates)

  Instead of setting up our own PostgreSQL server, we use Supabase's hosted version.
  Think of it as "database-as-a-service."

HOW WE CONNECT:
  We use the Supabase Python SDK which provides a clean API:
    db.table("bots").select("*").eq("org_id", "abc").execute()
  This translates to SQL: SELECT * FROM bots WHERE org_id = 'abc'

SINGLETON PATTERN:
  We only create ONE Supabase client and reuse it everywhere.
  _supabase_client is None initially → first call creates it → stored globally.
  This avoids creating a new connection for every database query.

TWO TYPES OF CLIENTS:
  1. get_supabase() → Uses the "anon" key (respects Row-Level Security rules)
  2. get_supabase_admin() → Uses the "service_role" key (bypasses all security)
     Only use admin client for server-side operations where you need full access.

DEV MODE (NO SUPABASE):
  If SUPABASE_URL/SUPABASE_KEY are blank or still set to the placeholder values,
  get_supabase() and get_supabase_admin() return an in-memory shim (app/dev_db.py)
  instead of a real Supabase client. This lets the app run locally with zero
  external services — data lives in process memory and resets on restart.
  The switch is decided by _is_dev_mode().
=============================================================================
"""

from app.config import get_settings

_supabase_client = None


def _is_dev_mode() -> bool:
    """True when USE_DEV_DB=true or Supabase is not configured."""
    s = get_settings()
    if s.use_dev_db:
        return True
    placeholder = {"", "https://your-project.supabase.co"}
    return s.supabase_url in placeholder or s.supabase_key in {"", "your-anon-key"}


def get_supabase():
    """
    Return the database client. In dev mode (no Supabase configured) returns
    an in-memory shim so the app works without any external services.
    """
    if _is_dev_mode():
        from app.dev_db import get_dev_db
        return get_dev_db()

    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        settings = get_settings()
        _supabase_client = create_client(settings.supabase_url, settings.supabase_key)
    return _supabase_client


def get_supabase_admin():
    if _is_dev_mode():
        from app.dev_db import get_dev_db
        return get_dev_db()

    from supabase import create_client
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)


# ── HELPER FUNCTIONS ──
# These simplify common database operations so you don't have to write
# the full Supabase query chain every time.


async def db_insert(table: str, data: dict) -> dict:
    """
    Insert a single row into a table.

    Args:
        table: Table name (e.g., "bots", "messages")
        data: Dictionary of column values to insert

    Returns:
        The inserted row as a dictionary

    Example:
        user = await db_insert("users", {"email": "test@test.com", "name": "Test"})
    """
    response = get_supabase().table(table).insert(data).execute()
    return response.data[0] if response.data else {}


async def db_select(table: str, filters: dict | None = None, limit: int = 100) -> list[dict]:
    """
    Select rows from a table with optional filters.

    Args:
        table: Table name
        filters: Dict of {column: value} to filter by (all are AND conditions)
        limit: Maximum number of rows to return (default 100)

    Returns:
        List of matching rows as dictionaries

    Example:
        # Get all active bots for an org
        bots = await db_select("bots", {"org_id": "abc", "is_active": True})
    """
    query = get_supabase().table(table).select("*")
    if filters:
        for key, value in filters.items():
            query = query.eq(key, value)  # Add WHERE key = value for each filter
    response = query.limit(limit).execute()
    return response.data or []


async def db_update(table: str, id: str, data: dict) -> dict:
    """
    Update a single row by its ID.

    Args:
        table: Table name
        id: The UUID of the row to update
        data: Dictionary of columns to update

    Returns:
        The updated row as a dictionary
    """
    response = get_supabase().table(table).update(data).eq("id", id).execute()
    return response.data[0] if response.data else {}


async def db_delete(table: str, id: str) -> bool:
    """
    Delete a single row by its ID.

    Args:
        table: Table name
        id: The UUID of the row to delete

    Returns:
        True if deletion was executed (doesn't check if row existed)
    """
    get_supabase().table(table).delete().eq("id", id).execute()
    return True
