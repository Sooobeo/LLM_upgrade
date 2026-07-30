from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.routes import thread as thread_routes
from app.schemas.workspace import WorkspaceMembersIn


class WorkspaceRouteTests(unittest.TestCase):
    def test_child_thread_cannot_be_converted_to_workspace(self):
        with (
            patch.object(
                thread_routes.sb,
                "rest_select",
                return_value=[
                    {
                        "id": "child-thread",
                        "owner_id": "owner-1",
                        "is_workspace": False,
                    }
                ],
            ),
            patch.object(thread_routes, "is_branch_root", return_value=False),
        ):
            with self.assertRaises(HTTPException) as raised:
                thread_routes.convert_to_workspace(
                    thread_id="child-thread",
                    payload=WorkspaceMembersIn(emails=[]),
                    user={"id": "owner-1"},
                    access_token="token",
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail["code"],
            "WORKSPACE_ROOT_ONLY",
        )

    def test_new_root_member_access_is_inherited_by_existing_descendants(self):
        inserted = []

        def select(table, query, access_token):
            if table == "threads":
                return [
                    {
                        "id": "root-thread",
                        "owner_id": "owner-1",
                        "is_workspace": False,
                    }
                ]
            if table == "thread_members" and "select=user_id,role" in query:
                return [
                    {"user_id": "owner-1", "role": "owner"},
                    {"user_id": "member-1", "role": "member"},
                ]
            if table == "thread_members" and "select=thread_id,user_id" in query:
                return [
                    {"thread_id": "root-thread", "user_id": "owner-1"},
                    {"thread_id": "root-thread", "user_id": "member-1"},
                ]
            if table == "thread_members":
                return []
            return []

        def insert(table, rows, access_token):
            inserted.append((table, rows))
            return {}

        with (
            patch.object(thread_routes.sb, "rest_select", side_effect=select),
            patch.object(thread_routes.sb, "rest_insert", side_effect=insert),
            patch.object(thread_routes.sb, "rest_update"),
            patch.object(thread_routes, "is_branch_root", return_value=True),
            patch.object(
                thread_routes,
                "branch_lineage_thread_ids",
                return_value=["root-thread", "child-a", "child-b"],
            ),
            patch.object(
                thread_routes,
                "get_user_id_by_email",
                return_value="member-1",
            ),
        ):
            result = thread_routes.convert_to_workspace(
                thread_id="root-thread",
                payload=WorkspaceMembersIn(emails=["member@example.com"]),
                user={"id": "owner-1"},
                access_token="token",
            )

        inherited = [
            row
            for _, rows in inserted
            for row in rows
            if row["thread_id"] in {"child-a", "child-b"}
        ]
        self.assertTrue(result["is_workspace"])
        self.assertEqual(len(inherited), 4)
        self.assertEqual(
            {
                (row["thread_id"], row["user_id"], row["role"])
                for row in inherited
            },
            {
                ("child-a", "owner-1", "owner"),
                ("child-a", "member-1", "member"),
                ("child-b", "owner-1", "owner"),
                ("child-b", "member-1", "member"),
            },
        )


if __name__ == "__main__":
    unittest.main()
