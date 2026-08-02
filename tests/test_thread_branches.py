from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from app.repository import thread as repository


class ThreadBranchRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_branch_stores_only_summary_metadata(self):
        inserted = []

        def select(table, query, access_token):
            if table == "threads":
                return [
                    {
                        "id": "parent-thread",
                        "title": "원본",
                        "owner_id": "owner-1",
                        "is_workspace": False,
                    }
                ]
            if "select=content" in query:
                return []
            if "index=gte.0" in query:
                return [
                    {
                        "index": 0,
                        "role": "user",
                        "content": "질문",
                        "created_at": "2026-01-01T00:00:00+00:00",
                    },
                    {
                        "index": 1,
                        "role": "assistant",
                        "content": "이 답변은 스무 글자보다 길어서 잘려야 합니다.",
                        "created_at": "2026-01-01T00:00:01+00:00",
                    },
                ]
            if "select=index" in query:
                return []
            return []

        def insert(table, rows, access_token):
            inserted.append((table, rows))
            return {}

        with (
            patch.object(repository.sb, "rest_select", side_effect=select),
            patch.object(repository.sb, "rest_insert", side_effect=insert),
            patch.object(repository, "uuid4", return_value="child-thread"),
            patch.object(
                repository.llm_client,
                "generate",
                new=AsyncMock(return_value="핵심 맥락을 요약했습니다."),
            ),
        ):
            result = await repository.create_thread_branch(
                owner_id="owner-1",
                parent_thread_id="parent-thread",
                access_token="token",
                requested_model="gemini-2.5-flash",
            )

        self.assertEqual(result["thread_id"], "child-thread")
        self.assertEqual(result["title"], "원본")
        self.assertEqual(result["parent_thread_id"], "parent-thread")
        self.assertLessEqual(len(result["context_preview"]), 20)

        child_message_insert = [
            rows
            for table, rows in inserted
            if table == "messages"
            and any(row.get("thread_id") == "child-thread" for row in rows)
        ][0]
        marker = child_message_insert[0]
        self.assertEqual(marker["index"], repository.BRANCH_META_INDEX)
        self.assertEqual(marker["role"], "assistant")
        metadata = repository._decode_branch_metadata(marker["content"])
        self.assertEqual(metadata["parent_thread_id"], "parent-thread")
        self.assertEqual(metadata["model"], "gemini-2.5-flash")
        self.assertEqual(metadata["context_preview"], result["context_preview"])
        self.assertEqual(len(child_message_insert), 1)

    async def test_create_branch_rejects_non_owner(self):
        with patch.object(
            repository.sb,
            "rest_select",
            return_value=[{"id": "parent-thread", "title": "원본", "owner_id": "someone-else"}],
        ):
            with self.assertRaises(repository.BranchForbiddenError):
                await repository.create_thread_branch(
                    owner_id="owner-1",
                    parent_thread_id="parent-thread",
                    access_token="token",
                    requested_model="gemini-2.5-flash",
                )

    async def test_create_branch_accepts_current_model_for_legacy_thread(self):
        inserted = []
        legacy_metadata = repository._encode_branch_metadata(
            {
                "version": 1,
                "parent_thread_id": None,
                "root_thread_id": "parent-thread",
                "model": "gemini-2.5-flash",
            }
        )

        def select(table, query, access_token):
            if table == "threads":
                return [
                    {
                        "id": "parent-thread",
                        "title": "원본",
                        "owner_id": "owner-1",
                        "is_workspace": False,
                    }
                ]
            if "select=content" in query:
                return [{"content": legacy_metadata}]
            if "index=gte.0" in query:
                return [
                    {
                        "index": 0,
                        "role": "user",
                        "content": "질문",
                        "created_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            return []

        def insert(table, rows, access_token):
            inserted.append((table, rows))
            return {}

        generate = AsyncMock(return_value="핵심 맥락")
        with (
            patch.object(repository.sb, "rest_select", side_effect=select),
            patch.object(repository.sb, "rest_insert", side_effect=insert),
            patch.object(repository, "uuid4", return_value="child-thread"),
            patch.object(repository.llm_client, "generate", new=generate),
        ):
            result = await repository.create_thread_branch(
                owner_id="owner-1",
                parent_thread_id="parent-thread",
                access_token="token",
                requested_model="gemini-3.6-flash",
            )

        self.assertEqual(result["thread_id"], "child-thread")
        self.assertEqual(generate.await_args.kwargs["model"], "gemini-3.6-flash")
        child_message_rows = [
            rows
            for table, rows in inserted
            if table == "messages"
            and any(row.get("thread_id") == "child-thread" for row in rows)
        ][0]
        child_metadata = repository._decode_branch_metadata(
            child_message_rows[0]["content"]
        )
        self.assertEqual(child_metadata["model"], "gemini-3.6-flash")

    async def test_create_branch_keeps_child_non_workspace_and_inherits_access(self):
        inserted = []

        def select(table, query, access_token):
            if table == "threads":
                return [
                    {
                        "id": "workspace-parent",
                        "title": "공유 대화",
                        "owner_id": "owner-1",
                        "is_workspace": True,
                    }
                ]
            if table == "thread_members":
                return [
                    {"user_id": "owner-1", "role": "owner"},
                    {"user_id": "member-1", "role": "member"},
                ]
            if "select=content" in query:
                return []
            if "index=gte.0" in query:
                return [
                    {
                        "index": 0,
                        "role": "user",
                        "content": "공유 질문",
                        "created_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            return []

        def insert(table, rows, access_token):
            inserted.append((table, rows))
            return {}

        with (
            patch.object(repository.sb, "rest_select", side_effect=select),
            patch.object(repository.sb, "rest_insert", side_effect=insert),
            patch.object(repository, "uuid4", return_value="workspace-child"),
            patch.object(
                repository.llm_client,
                "generate",
                new=AsyncMock(return_value="공유 맥락 요약"),
            ),
        ):
            result = await repository.create_thread_branch(
                owner_id="owner-1",
                parent_thread_id="workspace-parent",
                access_token="token",
                requested_model="gemini-2.5-flash",
            )

        child_thread = [
            rows[0]
            for table, rows in inserted
            if table == "threads" and rows[0]["id"] == "workspace-child"
        ][0]
        copied_members = [
            rows for table, rows in inserted if table == "thread_members"
        ][0]
        self.assertEqual(result["title"], "공유 대화")
        self.assertFalse(child_thread["is_workspace"])
        self.assertEqual(
            {row["user_id"] for row in copied_members},
            {"owner-1", "member-1"},
        )
        self.assertTrue(
            all(row["thread_id"] == "workspace-child" for row in copied_members)
        )

    async def test_create_branch_rejects_non_gemini_model(self):
        def select(table, query, access_token):
            if table == "threads":
                return [{"id": "parent-thread", "title": "원본", "owner_id": "owner-1"}]
            return []

        with (
            patch.object(repository.sb, "rest_select", side_effect=select),
            patch.object(repository.sb, "rest_insert") as insert,
        ):
            with self.assertRaises(repository.BranchModelError):
                await repository.create_thread_branch(
                    owner_id="owner-1",
                    parent_thread_id="parent-thread",
                    access_token="token",
                    requested_model="gemma3:270m",
                )
            insert.assert_not_called()

    def test_update_thread_title_requires_owner_and_trims_title(self):
        with (
            patch.object(
                repository.sb,
                "rest_select",
                return_value=[{"id": "thread-id"}],
            ),
            patch.object(repository.sb, "rest_update") as update,
        ):
            title = repository.update_thread_title(
                owner_id="owner-1",
                thread_id="thread-id",
                title="  새 이름  ",
                access_token="token",
            )

        self.assertEqual(title, "새 이름")
        update.assert_called_once()
        self.assertEqual(update.call_args.args[2], {"title": "새 이름"})

    def test_update_thread_title_masks_non_owner_as_missing(self):
        with (
            patch.object(repository.sb, "rest_select", return_value=[]),
            patch.object(repository.sb, "rest_update") as update,
        ):
            title = repository.update_thread_title(
                owner_id="owner-1",
                thread_id="thread-id",
                title="새 이름",
                access_token="token",
            )

        self.assertIsNone(title)
        update.assert_not_called()

    def test_branch_tree_returns_only_lineages_and_nests_children(self):
        root_meta = repository._encode_branch_metadata(
            {
                "version": 1,
                "parent_thread_id": None,
                "root_thread_id": "root",
                "model": "gemini-2.5-flash",
            }
        )
        child_meta = repository._encode_branch_metadata(
            {
                "version": 1,
                "parent_thread_id": "root",
                "root_thread_id": "root",
                "context_preview": "preview",
                "model": "gemini-2.5-flash",
            }
        )
        grandchild_meta = repository._encode_branch_metadata(
            {
                "version": 1,
                "parent_thread_id": "child",
                "root_thread_id": "root",
                "context_preview": "next",
                "model": "gemini-2.5-flash",
            }
        )

        thread_rows = [
            {
                "id": "standalone",
                "title": "독립",
                "created_at": "0",
                "owner_id": "owner-1",
            },
            {
                "id": "root",
                "title": "원본",
                "created_at": "1",
                "owner_id": "owner-1",
            },
            {
                "id": "child",
                "title": "원본",
                "created_at": "2",
                "owner_id": "owner-1",
            },
            {
                "id": "grandchild",
                "title": "원본",
                "created_at": "3",
                "owner_id": "owner-1",
            },
        ]
        marker_rows = [
            {"thread_id": "root", "content": root_meta},
            {"thread_id": "child", "content": child_meta},
            {"thread_id": "grandchild", "content": grandchild_meta},
        ]

        def select(table, query, access_token):
            if table == "thread_members":
                return []
            if table == "threads":
                return thread_rows
            if table == "messages":
                return marker_rows
            return []

        with (
            patch.object(repository.sb, "rest_select", side_effect=select),
            patch.object(repository, "_ensure_tutorial_branch"),
        ):
            roots = repository.list_branch_trees("owner-1", "token")

        self.assertEqual([node["thread_id"] for node in roots], ["root"])
        self.assertEqual(roots[0]["children"][0]["thread_id"], "child")
        self.assertEqual(
            roots[0]["children"][0]["children"][0]["thread_id"],
            "grandchild",
        )

    def test_workspace_member_sees_complete_tree_but_only_root_is_workspace(self):
        root_meta = repository._encode_branch_metadata(
            {
                "version": 1,
                "parent_thread_id": None,
                "root_thread_id": "root",
                "model": "gemini-2.5-flash",
            }
        )
        child_meta = repository._encode_branch_metadata(
            {
                "version": 1,
                "parent_thread_id": "root",
                "root_thread_id": "root",
                "model": "gemini-2.5-flash",
            }
        )

        def select(table, query, access_token):
            if table == "thread_members":
                return [
                    {"thread_id": "root", "role": "member"},
                    {"thread_id": "child", "role": "member"},
                ]
            if table == "threads" and "owner_id=eq.member-1" in query:
                return []
            if table == "threads":
                return [
                    {
                        "id": "root",
                        "title": "공유 루트",
                        "created_at": "1",
                        "owner_id": "owner-1",
                        "is_workspace": True,
                    },
                    {
                        "id": "child",
                        "title": "공유 루트",
                        "created_at": "2",
                        "owner_id": "owner-1",
                        # Legacy data can still be true; the API must mask it.
                        "is_workspace": True,
                    },
                ]
            if table == "messages":
                return [
                    {"thread_id": "root", "content": root_meta},
                    {"thread_id": "child", "content": child_meta},
                ]
            return []

        with (
            patch.object(repository.sb, "rest_select", side_effect=select),
            patch.object(repository, "_ensure_tutorial_branch"),
        ):
            roots = repository.list_branch_trees("member-1", "token")

        self.assertEqual([root["id"] for root in roots], ["root"])
        self.assertTrue(roots[0]["is_workspace"])
        self.assertEqual(roots[0]["workspace_role"], "member")
        self.assertFalse(roots[0]["can_manage_workspace"])
        self.assertEqual([node["id"] for node in roots[0]["children"]], ["child"])
        self.assertFalse(roots[0]["children"][0]["is_workspace"])
        self.assertIsNone(roots[0]["children"][0]["workspace_role"])

    def test_message_context_query_excludes_hidden_marker(self):
        with patch.object(repository.sb, "rest_select", return_value=[]) as select:
            repository.list_recent_messages("thread-id", 10, "token")
        self.assertIn("index=gte.0", select.call_args.args[1])

    def test_delete_root_removes_entire_branch_lineage(self):
        root_metadata = {
            "parent_thread_id": None,
            "root_thread_id": "root",
        }
        metadata_by_id = {
            "root": root_metadata,
            "child": {
                "parent_thread_id": "root",
                "root_thread_id": "root",
            },
            "grandchild": {
                "parent_thread_id": "child",
                "root_thread_id": "root",
            },
        }

        with (
            patch.object(
                repository.sb,
                "rest_select",
                return_value=[
                    {
                        "id": "root",
                        "owner_id": "owner-1",
                        "is_workspace": False,
                    }
                ],
            ),
            patch.object(
                repository,
                "_get_thread_metadata",
                return_value=root_metadata,
            ),
            patch.object(
                repository,
                "_all_branch_metadata",
                return_value=metadata_by_id,
            ),
            patch.object(
                repository,
                "_hard_delete_thread",
                return_value=1,
            ) as hard_delete,
        ):
            deleted = repository.delete_thread_by_id(
                "owner-1",
                "root",
                "token",
            )

        self.assertEqual(deleted, 3)
        self.assertEqual(
            {call.args[0] for call in hard_delete.call_args_list},
            {"root", "child", "grandchild"},
        )

    def test_delete_non_leaf_keeps_a_tombstone_node(self):
        metadata = {
            "parent_thread_id": "root",
            "root_thread_id": "root",
        }
        with (
            patch.object(
                repository.sb,
                "rest_select",
                return_value=[
                    {
                        "id": "middle",
                        "owner_id": "owner-1",
                        "is_workspace": False,
                    }
                ],
            ),
            patch.object(
                repository,
                "_get_thread_metadata",
                return_value=metadata,
            ),
            patch.object(
                repository,
                "_all_branch_metadata",
                return_value={
                    "middle": metadata,
                    "leaf": {
                        "parent_thread_id": "middle",
                        "root_thread_id": "root",
                    },
                },
            ),
            patch.object(repository, "_persist_thread_metadata") as persist,
            patch.object(repository.sb, "rest_delete", return_value=1) as delete,
            patch.object(repository, "_hard_delete_thread") as hard_delete,
        ):
            deleted = repository.delete_thread_by_id(
                "owner-1",
                "middle",
                "token",
            )

        self.assertEqual(deleted, 1)
        self.assertTrue(persist.call_args.args[1]["is_deleted"])
        self.assertIn(
            f"index=lt.{repository.BRANCH_META_INDEX}",
            delete.call_args.args[1],
        )
        hard_delete.assert_not_called()

    def test_delete_leaf_removes_the_physical_thread(self):
        metadata = {
            "parent_thread_id": "root",
            "root_thread_id": "root",
        }
        with (
            patch.object(
                repository.sb,
                "rest_select",
                return_value=[
                    {
                        "id": "leaf",
                        "owner_id": "owner-1",
                        "is_workspace": False,
                    }
                ],
            ),
            patch.object(
                repository,
                "_get_thread_metadata",
                return_value=metadata,
            ),
            patch.object(
                repository,
                "_all_branch_metadata",
                return_value={"leaf": metadata},
            ),
            patch.object(
                repository,
                "_hard_delete_thread",
                return_value=1,
            ) as hard_delete,
        ):
            deleted = repository.delete_thread_by_id(
                "owner-1",
                "leaf",
                "token",
            )

        self.assertEqual(deleted, 1)
        hard_delete.assert_called_once_with("leaf", "token")


if __name__ == "__main__":
    unittest.main()
