"""app.ask の対話ループのテスト（実際のAPIは呼ばず、Gemini クライアントを差し替える）。"""

from types import SimpleNamespace

import pytest

from app import ask


class FakeModels:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []  # 呼び出し時点の履歴のスナップショット

    def generate_content(self, model, contents):
        self.calls.append([(c.role, c.parts[0].text) for c in contents])
        text = self.replies.pop(0)
        usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=5)
        return SimpleNamespace(text=text, usage_metadata=usage)


def run_chat(monkeypatch, inputs, replies):
    models = FakeModels(replies)
    client = SimpleNamespace(models=models)  # chats は持たせない（使われたら失敗する）
    monkeypatch.setattr(ask.genai, "Client", lambda api_key: client)
    monkeypatch.setattr(ask, "get_api_key", lambda: "dummy")
    it = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(it))
    ask.main()
    return models


def test_history_is_accumulated_and_passed_each_turn(monkeypatch):
    models = run_chat(monkeypatch, ["こんにちは", "続き", "exit"], ["A1", "A2"])

    assert models.calls[0] == [("user", "こんにちは")]
    assert models.calls[1] == [
        ("user", "こんにちは"),
        ("model", "A1"),
        ("user", "続き"),
    ]
    assert len(models.calls) == 2


@pytest.mark.parametrize("word", ["exit", "quit", " EXIT "])
def test_exit_words_end_loop_without_calling_model(monkeypatch, word):
    models = run_chat(monkeypatch, [word], [])
    assert models.calls == []


def test_empty_input_is_skipped(monkeypatch):
    models = run_chat(monkeypatch, ["", "   ", "質問", "quit"], ["A1"])
    assert models.calls == [[("user", "質問")]]


def test_prints_prompt_header_and_token_counts(monkeypatch, capsys):
    run_chat(monkeypatch, ["質問", "exit"], ["回答"])
    out = capsys.readouterr().out
    assert "AI: 回答" in out
    assert "入力: 10" in out
    assert "出力: 5" in out
