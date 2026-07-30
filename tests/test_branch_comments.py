from __future__ import annotations

import unittest
from unittest.mock import patch

from app.repository import comment as repository
from app.routes import comment as comment_routes


class BranchCommentRepositoryTests(unittest.TestCase):
    def test_inherited_member_can_access_non_workspace_branch_child(self):
        def select(table, query, access_token):
            if table == "threads":
                return [
                    {
                        "id": "child-1",
                        "owner_id": "owner-1",
                        "is_workspace": False,
                    }
                ]
            if table == "thread_members":
                return [{"thread_id": "child-1"}]
            return []

        with patch.object(repository.sb, "rest_select", side_effect=select):
            accessible = repository._accessible_thread_ids(
                "member-1",
                ["child-1"],
                "token",
            )

        self.assertEqual(accessible, ["child-1"])

    def test_branch_comment_payload_round_trip_preserves_unicode_and_position(self):
        encoded = repository._encode_branch_comment("  중요한 코멘트  ", 120.5, 44)
        decoded = repository._decode_branch_comment(
            {
                "id": "comment-1",
                "thread_id": "thread-1",
                "user_id": "owner-1",
                "content": encoded,
                "created_at": "2026-07-29T00:00:00+00:00",
            }
        )

        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["content"], "중요한 코멘트")
        self.assertEqual(decoded["position_x"], 120.5)
        self.assertEqual(decoded["position_y"], 44.0)

    def test_list_branch_comments_ignores_regular_or_invalid_comment_rows(self):
        branch_content = repository._encode_branch_comment("브랜치 메모", 10, 20)
        rows = [
            {
                "id": "comment-1",
                "thread_id": "thread-1",
                "user_id": "owner-1",
                "content": branch_content,
                "created_at": None,
            },
            {
                "id": "comment-2",
                "thread_id": "thread-1",
                "user_id": "owner-1",
                "content": "일반 메시지 코멘트",
                "created_at": None,
            },
        ]

        def select(table, query, access_token):
            if table == "threads":
                return [
                    {
                        "id": "thread-1",
                        "owner_id": "owner-1",
                        "is_workspace": False,
                    }
                ]
            if table == "comments":
                return rows
            return []

        with patch.object(repository.sb, "rest_select", side_effect=select) as jwt_select:
            result = repository.list_branch_comments(
                "owner-1",
                ["thread-1", "thread-1"],
                "token",
            )

        self.assertEqual([comment["id"] for comment in result], ["comment-1"])
        query = [
            call.args[1]
            for call in jwt_select.call_args_list
            if call.args[0] == "comments"
        ][0]
        self.assertIn(
            f"message_index=eq.{repository.BRANCH_COMMENT_MESSAGE_INDEX}",
            query,
        )
        self.assertEqual(query.count("thread-1"), 1)

    def test_create_branch_comment_uses_authenticated_rest_and_reserved_index(self):
        inserted = []

        def select(table, query, access_token):
            if table == "threads":
                return [
                    {
                        "id": "thread-1",
                        "owner_id": "owner-1",
                        "is_workspace": False,
                    }
                ]
            if table == "thread_members":
                return []
            return [
                {
                    "id": "comment-1",
                    "thread_id": "thread-1",
                    "user_id": "owner-1",
                    "content": repository._encode_branch_comment("저장", 30, 40),
                    "created_at": None,
                }
            ]

        def insert(table, rows, access_token):
            inserted.extend(rows)
            return {}

        with (
            patch.object(repository.sb, "rest_select", side_effect=select),
            patch.object(repository.sb, "rest_insert", side_effect=insert),
            patch.object(repository, "uuid4", return_value="comment-1"),
        ):
            result = repository.create_branch_comment(
                "owner-1",
                "thread-1",
                "저장",
                30,
                40,
                "token",
                author_id="insun",
            )

        self.assertEqual(result["id"], "comment-1")
        self.assertEqual(
            inserted[0]["message_index"],
            repository.BRANCH_COMMENT_MESSAGE_INDEX,
        )
        self.assertEqual(inserted[0]["user_id"], "owner-1")
        inserted_comment = repository._decode_branch_comment(
            {
                **inserted[0],
                "created_at": None,
            }
        )
        self.assertEqual(inserted_comment["author_id"], "insun")

    def test_comment_author_uses_email_id_without_domain(self):
        comments = [
            {"user_id": "owner-1", "author_id": "owner-1"},
            {"user_id": "member-1", "author_id": "member-1"},
        ]
        user = {"id": "owner-1", "email": "owner.name@example.com"}

        with patch.object(
            comment_routes,
            "get_users_by_ids",
            return_value={
                "member-1": {
                    "id": "member-1",
                    "email": "team.member@example.org",
                }
            },
        ):
            comment_routes._normalize_comment_authors(comments, user)

        self.assertEqual(comments[0]["author_id"], "owner.name")
        self.assertEqual(comments[1]["author_id"], "team.member")


if __name__ == "__main__":
    unittest.main()
