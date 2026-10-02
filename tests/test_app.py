import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app import app
from routers import chat
from services import history, llm
from state import state

TEST_CONFIG = {
    "active_provider": "test",
    "active_model": "test-model",
    "providers": {
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
    },
}


class ApiTests(unittest.TestCase):
    def setUp(self):
        history.clear_history()
        self.addCleanup(history.clear_history)

        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        tmp_path = Path(self._tmp_dir.name)
        config_path = tmp_path / "providers.json"
        config_path.write_text(json.dumps(TEST_CONFIG), encoding="utf-8")

        state.init(config_path)
        self.client = TestClient(app)

    def test_routes_are_registered_once(self):
        paths = app.openapi()["paths"]
        self.assertEqual(
            set(paths),
            {
                "/",
                "/api/chat",
                "/api/system-prompt",
                "/api/switch-model",
                "/api/providers",
                "/api/supported-values",
            },
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

    def test_system_prompt_appends_to_server_history(self):
        response = self.client.post(
            "/api/system-prompt", json={"content": "  Follow the rules.  "}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"content": "Follow the rules."})
        self.assertEqual(
            history.get_history(),
            [{"role": "system", "content": "Follow the rules."}],
        )

    def test_system_prompt_rejects_empty_content(self):
        response = self.client.post("/api/system-prompt", json={"content": " "})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(history.get_history(), [])

    def test_chat_streams_deltas_and_done(self):
        def fake_stream(history, message, constraints):
            yield {"type": "start"}
            yield {"type": "delta", "content": "cont"}
            yield {"type": "delta", "content": "rolled"}
            yield {
                "type": "done",
                "content": "controlled",
                "raw": {"id": "response-id"},
                "request_payload": {"model": "test-model", "messages": []},
                "finish_reason": "stop",
                "applied_params": {"Длина": 20},
                "usage": {"total": 3},
            }

        constraints = {"max_tokens": 20}
        with patch.object(chat, "stream_controlled", side_effect=fake_stream) as stream_call, patch.object(
            chat, "render_markdown", side_effect=lambda text: text
        ):
            response = self.client.post(
                "/api/chat",
                json={
                    "message": "hello",
                    "constraints": constraints,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        frames = [
            json.loads(chunk[len("data: ") :])
            for chunk in response.text.split("\n\n")
            if chunk.startswith("data: ")
        ]
        self.assertEqual([f["type"] for f in frames], ["start", "delta", "delta", "done"])
        self.assertEqual(frames[1]["content"], "cont")
        self.assertEqual(frames[2]["content"], "rolled")
        self.assertEqual(frames[3]["content"], "controlled")
        self.assertEqual(frames[3]["raw_request"], {"model": "test-model", "messages": []})
        self.assertIsNone(frames[3]["finish_reason"])
        self.assertEqual(frames[3]["applied_params"], {"Длина": 20})
        self.assertEqual(frames[3]["usage"], {"total": 3})
        stream_call.assert_called_once_with([], "hello", constraints)
        self.assertEqual(
            history.get_history(),
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "controlled"},
            ],
        )


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
        with patch.object(state, "get_client", return_value=client), patch.object(
            state, "get_active_model", return_value="test-model"
        ):
            result = llm.call_controlled([], "new", constraints)

        request = client.chat.completions.create.call_args.kwargs
        self.assertEqual(request["max_tokens"], 20)
        self.assertEqual(request["temperature"], 0.2)
        self.assertEqual(result["applied_params"], {"Длина": 20, "Температура": 0.2})

    def test_stream_controlled_accumulates(self):
        def make_chunk(content=None, finish_reason=None, usage=None):
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(delta=SimpleNamespace(content=content), finish_reason=finish_reason)
                ]
                if content is not None or finish_reason is not None
                else [],
                usage=usage,
            )

        chunks = [
            make_chunk("При"),
            make_chunk("вет"),
            make_chunk(
                content="",
                finish_reason="stop",
            ),
            make_chunk(
                content=None,
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
            ),
        ]
        client = MagicMock()
        client.chat.completions.create.return_value = iter(chunks)
        with patch.object(state, "get_client", return_value=client), patch.object(
            state, "get_active_model", return_value="test-model"
        ):
            frames = list(llm.stream_controlled([], "new", {}))

        request = client.chat.completions.create.call_args.kwargs
        self.assertTrue(request["stream"])
        self.assertEqual(request["stream_options"], {"include_usage": True})
        deltas = [f["content"] for f in frames if f["type"] == "delta"]
        self.assertEqual(deltas, ["При", "вет"])
        done = frames[-1]
        self.assertEqual(done["type"], "done")
        self.assertEqual(done["content"], "Привет")
        self.assertEqual(done["finish_reason"], "stop")
        self.assertEqual(done["usage"], {"prompt": 1, "completion": 2, "total": 3})
        self.assertEqual(len(done["raw"]), 2)

    def test_stream_controlled_reports_reasoning(self):
        def make_chunk(content=None, reasoning=None, finish_reason=None):
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(content=content, reasoning=reasoning),
                        finish_reason=finish_reason,
                    )
                ]
            )

        chunks = [
            make_chunk(content="", reasoning="Размышляю"),
            make_chunk(content="", reasoning=" о модели"),
            make_chunk(content="Ответ", finish_reason="stop"),
        ]
        client = MagicMock()
        client.chat.completions.create.return_value = iter(chunks)
        with patch.object(state, "get_client", return_value=client), patch.object(
            state, "get_active_model", return_value="test-model"
        ):
            frames = list(llm.stream_controlled([], "new", {}))

        self.assertEqual(frames[0], {"type": "start"})
        reasoning = [f["content"] for f in frames if f["type"] == "reasoning"]
        self.assertEqual(reasoning, ["Размышляю", " о модели"])
        deltas = [f["content"] for f in frames if f["type"] == "delta"]
        self.assertEqual(deltas, ["Ответ"])
        done = frames[-1]
        self.assertEqual(done["type"], "done")
        self.assertEqual(done["reasoning"], "Размышляю о модели")
        self.assertEqual(done["content"], "Ответ")
        self.assertEqual(len(done["raw"]), 3)

    def test_render_markdown(self):
        self.assertEqual(llm.render_markdown("# title"), "<h1>title</h1>")


class HistoryServiceTests(unittest.TestCase):
    def setUp(self):
        history.clear_history()

    def tearDown(self):
        history.clear_history()

    def test_history_appends_and_loads_messages(self):
        history.append_message("system", "instructions")
        history.append_turn("question", "answer")

        self.assertEqual(
            history.get_history(),
            [
                {"role": "system", "content": "instructions"},
                {"role": "user", "content": "question"},
                {"role": "assistant", "content": "answer"},
            ],
        )

    def test_get_history_returns_copy(self):
        history.append_message("user", "question")
        loaded = history.get_history()
        loaded.append({"role": "assistant", "content": "external"})

        self.assertEqual(len(history.get_history()), 1)

    def test_clear_history_removes_all_messages(self):
        history.append_message("user", "question")
        history.clear_history()

        self.assertEqual(history.get_history(), [])


if __name__ == "__main__":
    unittest.main()
