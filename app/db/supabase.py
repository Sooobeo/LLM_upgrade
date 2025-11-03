from app.db.connection import get_supabase as _get_supabase, ConfigError

def get_supabase_client():
    return _get_supabase()