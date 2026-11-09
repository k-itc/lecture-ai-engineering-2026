"""エージェントの配線テスト。

TestModel は実際のLLMを呼ばない偽モデルで、登録されたツールを全部呼んでから
ダミーの回答を返す。APIキーも利用枠も使わずに、
「ツールが登録され、呼ばれ、結果がモデルに戻るか」を確かめられる。
"""

from pydantic_ai import DeferredToolRequests
import sys

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.test import TestModel

from app import agent as agent_module
from app.agent import agent

BASE_TOOLS = {"search_glossary", "get_lecture_summary"}


def _parts(result, kind):
    return [p for m in result.all_messages() for p in m.parts if isinstance(p, kind)]


def test_base_tools_are_registered_and_called():
    model = TestModel()
    with agent.override(model=model):
        result = agent.run_sync("LoRAとは？")

    offered = {t.name for t in model.last_model_request_parameters.function_tools}
    assert BASE_TOOLS <= offered  # 演習でツールを足しても壊れないよう「含む」で判定

    called = {p.tool_name for p in _parts(result, ToolCallPart)}
    assert BASE_TOOLS <= called
    # 承認が必要なツール（requires_approval=True）は、実行されずに承認待ちになるので戻り値が無い
    waiting = len(result.output.approvals) if isinstance(result.output, DeferredToolRequests) else 0
    assert len(_parts(result, ToolReturnPart)) + waiting == len(_parts(result, ToolCallPart))
    assert result.output


def test_glossary_result_reaches_the_model():
    model = TestModel(call_tools=["search_glossary"])
    with agent.override(model=model):
        result = agent.run_sync("RAGとは？")
    returns = _parts(result, ToolReturnPart)
    assert returns and returns[0].tool_name == "search_glossary"


@pytest.mark.parametrize(
    ("answers", "saved_contents"),
    [
        (["y", "n"], ["承認された記録"]),
        (["n", "y"], ["承認された記録2"]),
        (["invalid", "n", "n"], []),
    ],
)
def test_cli_resumes_mixed_tool_calls_with_individual_approvals(
    monkeypatch, tmp_path, capsys, answers, saved_contents
):
    observed_returns = []

    def respond(messages, info):
        if not any(isinstance(message, ModelResponse) for message in messages):
            return ModelResponse(parts=[
                ToolCallPart("search_glossary", {"query": "LoRA"}, tool_call_id="search"),
                ToolCallPart("get_lecture_summary", {"lecture": 3}, tool_call_id="summary"),
                ToolCallPart("save_learning_log", '{"content": "承認された記録"}', tool_call_id="save1"),
                ToolCallPart("save_learning_log", {"content": "承認された記録2"}, tool_call_id="save2"),
            ])
        observed_returns.extend(
            part for message in messages for part in message.parts
            if isinstance(part, ToolReturnPart)
        )
        return ModelResponse(parts=[TextPart("完了")])

    inputs = iter(answers)

    def answer(prompt):
        assert not list((tmp_path / "learning_log").glob("*.txt"))
        return next(inputs)

    monkeypatch.setattr("builtins.input", answer)
    monkeypatch.setattr(sys, "argv", ["agent", "テスト"])
    monkeypatch.setattr(agent_module, "build_model", lambda: FunctionModel(respond))
    monkeypatch.chdir(tmp_path)

    agent_module.main()

    assert "完了" in capsys.readouterr().out
    assert [path.read_text(encoding="utf-8") for path in (tmp_path / "learning_log").glob("*.txt")] == saved_contents
    assert [part.tool_call_id for part in observed_returns].count("search") == 1
    assert [part.tool_call_id for part in observed_returns].count("summary") == 1
    assert {part.tool_call_id for part in observed_returns} >= {"search", "summary", "save1", "save2"}
