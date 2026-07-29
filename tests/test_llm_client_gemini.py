from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services import llm_client


class GeminiClientTests(IsolatedAsyncioTestCase):
    async def test_generate_dispatches_gemini_messages(self):
        original_key = settings.GEMINI_API_KEY
        settings.GEMINI_API_KEY = "test-key"

        async_client = SimpleNamespace(
            models=SimpleNamespace(
                generate_content=AsyncMock(
                    return_value=SimpleNamespace(text="Gemini response"),
                )
            ),
            aclose=AsyncMock(),
        )
        client = SimpleNamespace(aio=async_client)

        try:
            with patch.object(llm_client.genai, "Client", return_value=client):
                result = await llm_client.generate(
                    "gemini-3.6-flash",
                    [
                        {"role": "system", "content": "Be concise."},
                        {"role": "user", "content": "Hello"},
                        {"role": "assistant", "content": "Hi"},
                        {"role": "user", "content": "Help me"},
                    ],
                )
        finally:
            settings.GEMINI_API_KEY = original_key

        self.assertEqual(result, "Gemini response")
        async_client.models.generate_content.assert_awaited_once()
        call = async_client.models.generate_content.await_args.kwargs
        self.assertEqual(call["model"], "gemini-3.6-flash")
        self.assertEqual([item.role for item in call["contents"]], ["user", "model", "user"])
        self.assertEqual(call["config"].system_instruction, "Be concise.")
        async_client.aclose.assert_awaited_once()

    async def test_generate_requires_server_api_key(self):
        original_key = settings.GEMINI_API_KEY
        settings.GEMINI_API_KEY = None
        try:
            with self.assertRaises(llm_client.LLMUpstreamError) as raised:
                await llm_client.generate(
                    "gemini-3.6-flash",
                    [{"role": "user", "content": "Hello"}],
                )
        finally:
            settings.GEMINI_API_KEY = original_key

        self.assertEqual(raised.exception.provider, "gemini")
        self.assertEqual(raised.exception.code, "GEMINI_NOT_CONFIGURED")

    async def test_legacy_2_5_model_uses_compatibility_model(self):
        original_key = settings.GEMINI_API_KEY
        settings.GEMINI_API_KEY = "test-key"

        async_client = SimpleNamespace(
            models=SimpleNamespace(
                generate_content=AsyncMock(
                    return_value=SimpleNamespace(text="Compatible response"),
                )
            ),
            aclose=AsyncMock(),
        )
        client = SimpleNamespace(aio=async_client)

        try:
            with patch.object(llm_client.genai, "Client", return_value=client):
                result = await llm_client.generate(
                    "gemini-2.5-flash",
                    [{"role": "user", "content": "Hello"}],
                )
        finally:
            settings.GEMINI_API_KEY = original_key

        self.assertEqual(result, "Compatible response")
        call = async_client.models.generate_content.await_args.kwargs
        self.assertEqual(call["model"], settings.GEMINI_2_5_COMPAT_MODEL)
