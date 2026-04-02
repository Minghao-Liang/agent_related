import copy
import unittest
from types import SimpleNamespace

from agent_loop import LoopResult, run_agent_loop


def text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def tool_use_block(
    tool_use_id: str,
    name: str,
    payload: dict,
) -> SimpleNamespace:
    return SimpleNamespace(
        type="tool_use",
        id=tool_use_id,
        name=name,
        input=payload,
    )


def response(stop_reason: str, *content: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(stop_reason=stop_reason, content=list(content))


class FakeMessagesAPI:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        return self._responses.pop(0)

    def stream(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        payload = self._responses.pop(0)
        return FakeStream(payload["chunks"], payload["response"])


class FakeStream:
    def __init__(
        self,
        chunks: list[str],
        final_response: SimpleNamespace,
    ) -> None:
        self.text_stream = list(chunks)
        self._final_response = final_response

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get_final_message(self) -> SimpleNamespace:
        return self._final_response


class FakeClient:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self.messages = FakeMessagesAPI(responses)


class AgentLoopTests(unittest.TestCase):
    def test_returns_when_model_stops_without_tool_use(self) -> None:
        client = FakeClient([response("end_turn", text_block("done"))])
        messages = [{"role": "user", "content": "say done"}]

        result = run_agent_loop(
            client=client,
            model="test-model",
            system_prompt="test system",
            messages=messages,
            tools=[],
            execute_tool=lambda _name, _payload: "unused",
        )

        self.assertIsInstance(result, LoopResult)
        self.assertEqual(result.final_text, "done")
        self.assertEqual(result.turns, 1)
        self.assertEqual(messages[-1]["role"], "assistant")
        self.assertEqual(len(client.messages.calls), 1)

    def test_executes_tool_results_and_continues_until_final_answer(self) -> None:
        client = FakeClient(
            [
                response(
                    "tool_use",
                    text_block("checking"),
                    tool_use_block("tool-1", "bash", {"command": "pwd"}),
                ),
                response("end_turn", text_block("all done")),
            ]
        )
        messages = [{"role": "user", "content": "where am i?"}]
        executed: list[tuple[str, dict]] = []

        def execute_tool(name: str, payload: dict) -> str:
            executed.append((name, payload))
            return "/tmp/project"

        result = run_agent_loop(
            client=client,
            model="test-model",
            system_prompt="test system",
            messages=messages,
            tools=[{"name": "bash"}],
            execute_tool=execute_tool,
            max_turns=3,
        )

        self.assertEqual(result.final_text, "all done")
        self.assertEqual(result.turns, 2)
        self.assertEqual(executed, [("bash", {"command": "pwd"})])
        self.assertEqual(messages[2]["role"], "user")
        self.assertEqual(
            messages[2]["content"],
            [
                {
                    "type": "tool_result",
                    "tool_use_id": "tool-1",
                    "content": "/tmp/project",
                }
            ],
        )
        self.assertEqual(len(client.messages.calls), 2)
        self.assertEqual(
            client.messages.calls[1]["messages"][2]["content"][0]["tool_use_id"],
            "tool-1",
        )

    def test_raises_when_max_turns_is_exceeded(self) -> None:
        client = FakeClient(
            [
                response(
                    "tool_use",
                    tool_use_block("tool-1", "bash", {"command": "pwd"}),
                ),
                response(
                    "tool_use",
                    tool_use_block("tool-2", "bash", {"command": "ls"}),
                ),
            ]
        )

        with self.assertRaisesRegex(RuntimeError, "max turns"):
            run_agent_loop(
                client=client,
                model="test-model",
                system_prompt="test system",
                messages=[{"role": "user", "content": "loop"}],
                tools=[{"name": "bash"}],
                execute_tool=lambda _name, _payload: "ok",
                max_turns=1,
            )

    def test_streams_text_and_emits_tool_events(self) -> None:
        client = FakeClient(
            [
                {
                    "chunks": ["check", "ing"],
                    "response": response(
                        "tool_use",
                        text_block("checking"),
                        tool_use_block("tool-1", "bash", {"command": "pwd"}),
                    ),
                },
                {
                    "chunks": ["all ", "done"],
                    "response": response("end_turn", text_block("all done")),
                },
            ]
        )
        rendered: list[str] = []
        events: list[tuple[str, str]] = []

        result = run_agent_loop(
            client=client,
            model="test-model",
            system_prompt="test system",
            messages=[{"role": "user", "content": "where am i?"}],
            tools=[{"name": "bash"}],
            execute_tool=lambda _name, _payload: "/tmp/project",
            use_stream=True,
            on_text_delta=rendered.append,
            on_tool_event=lambda tool, status: events.append((tool, status)),
        )

        self.assertEqual(result.final_text, "all done")
        self.assertEqual("".join(rendered), "checkingall done")
        self.assertEqual(events, [("bash", "start"), ("bash", "end")])


if __name__ == "__main__":
    unittest.main()
