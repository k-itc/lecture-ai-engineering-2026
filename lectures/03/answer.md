# 第3回 解答

## 演習

* 第1回とエージェントの回答の違い:
  * 第1回 (app.ask) では講座固有の lecNN-start タグという用語を知らないため、推測で回答するか、分からないと返していた。
  * 第3回 (app.agent) では答える前に search_glossary を用いて用語集を検索し、関係する回：第1回 を回答できた。

* --trace で見えたツール呼び出し (ツール名と引数):
  * search_glossary({'query': 'LoRA'})
  * search_glossary({'query': 'QLoRA'})

* 1つの質問での LLM 呼び出し回数 (requests):
  * 2 回

* 追加したツールと、docstring に書いた説明:
  * 追加したツール: make_quiz(lecture: int) -> str
  * docstring に書いた説明:
    ```python
    """指定した回の用語から1つを選び、確認問題と答えを返す。
    「第2回の確認問題を出して」のように、復習用の問題を求められたときに使う。
    """
    ```

## 宿題

* 取り組んだレベル: 実装

* やったこと:
  * app/tools.py に save_learning_log ツールを作成し、learning_log/ フォルダ配下へ日時付きテキストファイルで学習ログを保存する処理を実装した。
  * app/agent.py で output_type=[str, DeferredToolRequests] を設定し、save_learning_log に requires_approval=True を付与して登録した。
  * CLI (main 関数) にて DeferredToolRequests を検知した際、result.output.approvals からツールの実行可否 (y/n) をユーザーに確認し、deferred_results.approvals[call.tool_call_id] = True として SDK 側へ安全に承認結果を渡して再開する Human-in-the-Loop フローを構築した。

* 結果:
  * --trace 付きでログ保存コマンドを実行した際、保存の直前で 承認リクエスト が表示されて一時停止した。
  * y と入力すると承認されてツールの実行が行われ、learning_log/ 内にログファイル（log_20261108_153631.txt）が正常に生成された。
  * uv run pytest -q を実行し、全15件のテストが通過 (15 passed) することを確認した。

* 気づき・疑問:
  * 人間の承認を挟む Human-in-the-Loop 構成にすることで、ファイルの保存や書き換えといった取り消しにくい操作 (Side Effects)を安全に制御できる仕組みを体験できた。
  * Pydantic AI において output_type に DeferredToolRequests を追加し、deferred_results.approvals を通してツールコールIDごとに承認状態を受け渡すことで、エージェントループが安全かつ正確に完結することを理解できた。
  