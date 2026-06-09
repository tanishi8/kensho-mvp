# 実稼働セットアップ手順（GitHub Actions・方法A）

PCを起動していなくても毎朝自動でDiscordに通知が届く構成。ゼロ円。
上から順にチェックしていけば完了します。所要30〜40分。

---

## STEP 0: 事前に用意するもの

- [ ] GitHubアカウント（無料。未登録なら https://github.com/signup ）
- [ ] Discordアカウントと通知用サーバー（自分専用でOK）
- [ ]（任意）Gemini APIキー（抽出精度UP。無くても正規表現で動く）
- [ ]（任意・当選チェックを使うなら）懸賞専用Gmail

---

## STEP 1: Discord Webhook を作る（5分）

- [ ] Discordで通知用チャンネル（例「当選通知」）を用意
- [ ] チャンネルの歯車（⚙ 編集）→「連携サービス」→「ウェブフックを作成」
- [ ] 名前を付けて「ウェブフックURLをコピー」
- [ ] コピーしたURL `https://discord.com/api/webhooks/...` をメモ（後でSecretsに登録）

⚠️ このURLは秘密。人に見せない・コードに直書きしない。

---

## STEP 2:（任意）Gemini APIキーを取る（5分）

- [ ] https://aistudio.google.com/apikey にアクセス
- [ ] 「Create API key」でキーを発行しメモ
- [ ] ※スキップ可。その場合は config.yaml の `llm.provider` を `none` にするか、キー未設定のまま（自動で正規表現のみ動作）

---

## STEP 3: フィードURLを確定する（GitHub上で実行・ローカルPython不要）

※ローカルにPythonが無くてもOK。GitHub上で検証します。先にSTEP4（リポジトリ作成・アップ）を済ませてから戻ってきても構いません。

- [ ] リポジトリの **Actions** タブを開く
- [ ]「フィード検証（手動）」を選び **Run workflow** を押す
- [ ] 実行が終わったらログを開き、**「✅有効（○件）」と表示されたフィードURL**を確認
- [ ] ログ末尾の「config.yaml に貼れる形式」をコピー
- [ ] config.yaml の `feeds:` を、有効だったURLに整える（既に5件設定済み。不要なものは削除、追加したいものは追記してコミット）
- [ ]（任意）ALERTS.md を見て Googleアラートを作成し、発行されたRSS URLを feeds に追加。アラート併用時は config の `keyword_filter.enabled` を `true` に

> 補足: 現在 config に設定済みの「スタンプラリー協会・せとうちDMO・キャンなび」は稼働確認済みです。
> 検証が面倒なら STEP3 を飛ばし、この3件のまま STEP5・6 へ進んでも動きます（あとから追加可）。

---

## STEP 4: GitHubリポジトリを作って中身をアップ（10分）

- [ ] GitHubで新規リポジトリを作成（**Private推奨**。名前は kensho-mvp 等）
- [ ] kensho-mvp フォルダの中身を全てアップロード
      （GitHubの「Add file」→「Upload files」にドラッグ＆ドロップでも可。
       または git push）
- [ ] `.github/workflows/daily.yml` が含まれていることを確認

⚠️ `profile.json`・`whitelist.json` を作っている場合は個人情報なのでアップしない（.gitignore済み）。

---

## STEP 5: Secrets を登録する（5分）

- [ ] リポジトリの **Settings → Secrets and variables → Actions → New repository secret**
- [ ] 以下を登録:
  - [ ] `DISCORD_WEBHOOK_URL` = STEP1でコピーしたURL（必須）
  - [ ] `GEMINI_API_KEY` = STEP2のキー（任意）
  - [ ]（当選チェックを使うなら）`IMAP_HOST`=imap.gmail.com / `IMAP_USER`=Gmailアドレス / `IMAP_PASS`=アプリパスワード

---

## STEP 6: 動かして確認（5分）

- [ ] リポジトリの **Actions** タブを開く
- [ ]「懸賞 daily 通知」を選び **Run workflow** で手動実行
- [ ] 緑のチェックになり、**Discordに通知が届けば成功** 🎉
- [ ] 以降は毎日 JST 8:07 に自動実行される

---

## 運用後の使い方（手元PCで随時）

| やりたいこと | コマンド |
|---|---|
| 優先リスト＋コメント案（半自動応募の準備） | `python toolb.py list` |
| 応募を記録 / 当選を記録 | `python toolb.py apply <id>` / `python toolb.py won <id>` |
| 当選チェック（本物のみ通知） | `python toolc.py run` |
| 受取期限リマインダー | `python toolc.py remind` |
| 当選率・収支レポート | `python report.py` |

---

## トラブル時

- **Actionsが失敗（赤）**: ログを開き、エラー箇所を確認。多くは requirements か Secrets 名のミス。
- **Discordに来ない**: `DISCORD_WEBHOOK_URL` の値を再確認（前後の空白に注意）。
- **新着が0件**: config の feeds URLが古い/間違い。find_feeds で再確認。
- **cronが時間通り動かない**: GitHub側の仕様（遅延あり）。急ぎなら手動 Run workflow。厳密な定刻が要るなら Cloudflare Workers cron → workflow_dispatch 起動に変更（FINAL_RESEARCH.md 参照）。
- **しばらく放置するとスケジュール無効化**: 60日間コミットが無いとGitHubがcronを止める。たまにcommitするか手動実行で回避。

---

## 注意（再掲）
- このシステムは収集・通知・準備を自動化し、**最終応募は人間が行う半自動**設計です（規約・凍結リスク回避）。
- フィードは各サイトの利用規約・robots.txtを確認のうえ利用してください。
- 当選額が増えたら TAX_CASHOUT.md（税務・換金）を確認。
