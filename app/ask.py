"""第1回: 対話履歴を保持してLLMと会話するスクリプト。

使い方:
    uv run python -m app.ask

ツールは使わず、会話履歴をモデルに渡す「素の」呼び出し。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

from google import genai
from google.genai import errors
from google.genai import types

from app.config import MODEL, api_error_message, get_api_key


# 講座に固有の質問例。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def main() -> None:
    print(f"[model] {MODEL}")
    print(f"（終了: exit / quit） 質問例: {DEFAULT_QUESTION}")

    try:
        client = genai.Client(api_key=get_api_key())
        # 会話履歴を保持し、各ターンで履歴全体をモデルに渡す。
        contents = []

        while True:
            user_input = input("You: ")
            if user_input.strip().lower() in {"exit", "quit"}:
                print("[終了]")
                break
            if not user_input.strip():
                continue

            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_input)],
                )
            )
            response = client.models.generate_content(model=MODEL, contents=contents)

            answer = response.text
            if answer is None:
                print("AI: (テキスト応答がありません)")
            else:
                print(f"AI: {answer}")
                contents.append(
                    types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=answer)],
                    )
                )

            # 各ターンの応答に含まれる入出力トークン数を表示する。
            usage = response.usage_metadata
            if usage is not None:
                print(
                    f"[tokens] 入力: {usage.prompt_token_count} / "
                    f"出力: {usage.candidates_token_count}"
                )
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
