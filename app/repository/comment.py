from supabase import Client

class CommentRepository:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    def create_comment(self, thread_id: str, user_id: str, message_index: int, content: str):
        res = self.supabase.table("comments").insert({
            "thread_id": thread_id,
            "user_id": user_id,
            "message_index": message_index,
            "content": content
        }).execute()

        return res.data[0] if res.data else None

    def get_comments(self, thread_id: str, message_index: int):
        res = (
            self.supabase.table("comments")
            .select("*")
            .eq("thread_id", thread_id)
            .eq("message_index", message_index)
            .order("created_at", desc=False)
            .execute()
        )

        return res.data

    def delete_comment(self, comment_id: str, user_id: str):
        res = (
            self.supabase.table("comments")
            .delete()
            .eq("id", comment_id)
            .eq("user_id", user_id)
            .execute()
        )

        return res.data