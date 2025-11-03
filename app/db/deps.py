from app.db.supabase import get_supabase_client

def get_sb():
    return get_supabase_client()