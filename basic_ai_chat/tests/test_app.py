import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import state
from app import app
from routers import chat
from services import llm


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        state._providers_config = {
            "test": {
                "name": "Test provider",
                "base_url": "http://test",
                "models": [
                    {
                        "id": "test-model",
                        "name": "Test model",
                        "temperature": {"min": 0, "max": 2, "default": 0.7},
                        "max_tokens": {"min": 5, "max": 100, "default": 20},
                    }
                ],
            }
        }
        state._active_provider = "test"
        state._active_model = "test-model"
        state._active_model_config = state._providers_config["test"]["models"][0]
        state._raw_config = {"active_provider": "test", "active_model": "test-model"}

    def test_routes_are_registered_once(self):
        paths = app.openapi()["paths"]
        self.assertEqual(
            set(paths),
            {"/", "/api/chat", "/api/switch-model", "/api/providers", "/api/supported-values"},
        )
        self.assertNotIn("/switch-model", paths)

    def test_home_and_configuration_endpoints(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        response = self.client.get("/api/providers")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["active_model"], "test-model")
        self.assertEqual(self.client.get("/api/supported-values").status_code, 200)

    def test_switch_model_validation(self):
        response = self.client.post(
            "/api/switch-model", params={"provider": "missing", "model": "test-model"}
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            "/api/switch-model", params={"provider": "test", "model": "missing"}
        )
        self.assertEqual(response.status_code, 400)

    def test_chat_uses_single_controlled_service(self):
        controlled_result = {
            "raw": {"id": "response-id"},
            "request_payload": {"model": "test-model", "messages": []},
            "content": "controlled",
            "finish_reason": "stop",
            "applied_params": {"Длина": 20},
            "usage": {"total": 3},
        }
        history = [{"role": "user", "content": "old"}]
        constraints = {"max_tokens": 20}
        with patch.object(
            chat, "call_controlled", return_value=controlled_result
        ) as controlled_call, patch.object(chat, "render_markdown", side_effect=lambda text: text):
            response = self.client.post(
                "/api/chat",
                json={
                    "message": "hello",
                    "conversation_history": history,
                    "constraints": constraints,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "raw": {"id": "response-id"},
                "raw_request": {"model": "test-model", "messages": []},
                "content": "controlled",
                "raw_content": "controlled",
                "finish_reason": None,
                "applied_params": {"Длина": 20},
                "usage": {"total": 3},
            },
        )
        self.assertNotIn("free_response", response.json())
        self.assertNotIn("controlled_response", response.json())
        controlled_call.assert_called_once_with(history, "hello", constraints)


class LlmServiceTests(unittest.TestCase):
    def make_response(self, content="answer"):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason="stop")],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
            model_dump=lambda: {"content": content},
        )

    def test_call_controlled_passes_constraints(self):
        client = MagicMock()
        client.chat.completions.create.return_value = self.make_response()
        constraints = {"max_tokens": 20, "temperature": 0.2}
        with patch.object(state, "_get_client", return_value=client), patch.object(
            state, "_get_model_name", return_value="test-model"
        ):
            result = llm.call_controlled([], "new", constraints)

        request = client.chat.completions.create.call_args.kwargs
        self.assertEqual(request["max_tokens"], 20)
        self.assertEqual(request["temperature"], 0.2)
        self.assertEqual(result["applied_params"], {"Длина": 20, "Температура": 0.2})

    def test_render_markdown(self):
        self.assertEqual(llm.render_markdown("# title"), "<h1>title</h1>")


if __name__ == "__main__":
    unittest.main()
