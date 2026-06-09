# 稼働開始ガイド（はじめに読む）

懸賞MVPを実際に動かすための手順です。まず **Discord Webhook** を用意し、
次に **方法A（自動）** か **方法B（手元）** のどちらかで起動します。

---

## 0. 共通: Discord Webhook を作る（5分）

通知の受け取り口です。

1. Discordで通知用サーバー／チャンネル（例「当選通知」）を用意
2. チャンネルの歯車（⚙ チャンネルの編集）→「連携サービス」→「ウェブフックを作成」
3. 名前を付けて「ウェブフックURLをコピー」
4. `https://discord.com/api/webhooks/...` が取得できる

⚠ このURLは秘密。コードに直書きせず、環境変数／GitHub Secretsに入れる。

---

## 方法A: GitHub Actions で自動運用（推奨・ゼロ円）

PCを起動していなくても毎朝自動で動く。

**必要なもの**: GitHubアカウント、Discord Webhook URL、(任意)Gemini APIキー

1. GitHubで新規リポジトリ作成（Privateで可）
2. `kensho-mvp` の中身を全部アップロード
3. Settings → Secrets and variables → Actions → New repository secret
   - `DISCORD_WEBHOOK_URL` = コピーしたURL
   - (任意) `GEMINI_API_KEY` = Geminiキー
   - (当選チェックを使うなら) `IMAP_HOST` `IMAP_USER` `IMAP_PASS`
4. Actionsタブ →「懸賞 daily 通知」→「Run workflow」で手動テスト
5. 成功すれば以降は毎日 JST 8:00 に自動実行

> scheduleはGitHub都合で遅延することがある（設計書7章）。時刻厳守が必要なら
> 外部cronから workflow_dispatch を叩く構成に変更。

---

## 方法B: 手元のPCで動かす

**必要なもの**: Python 3.10+、Discord Webhook URL

```bash
cd kensho-mvp
pip install -r requirements.txt

# Mac/Linux
export DISCORD_WEBHOOK_URL="コピーしたURL"
# Windows PowerShell:  $env:DISCORD_WEBHOOK_URL="..."

python main.py --sample sample_feed.xml --dry-run   # サンプルで確認
python main.py                                       # 本番（RSS→通知）
```

毎日自動化したい場合は cron（Mac/Linux）／タスクスケジューラ（Windows）に登録。
常時自動が欲しくなったら方法Aへ。

---

## 必須: 実フィードURLの設定

`config.yaml` の `feeds:` は仮のURL。**利用規約を確認のうえ**、公式配信のRSS URLに差し替える。
これが入って初めて実データが流れる。

---

## 各ツールの起動コマンドまとめ

| やりたいこと | コマンド |
|---|---|
| 狙い目を通知（フェーズ0） | `python main.py` |
| 優先リスト＋コメント案（ツールB） | `python toolb.py list` |
| 応募を記録／集計 | `python toolb.py apply <id>` / `python toolb.py stats` |
| 自動応募の可否確認（ツールA） | `python toola.py plan` |
| 自動応募（dry-run→本番） | `python toola.py run` → `python toola.py run --live` |
| 当選チェック（本物のみ通知） | `python toolc.py run` |

## 段階的な始め方（おすすめ順）

1. まず方法Bでサンプル実行 → 動きを把握
2. 実フィードURLを設定 → `python main.py` で毎日の通知を受ける
3. 慣れたら方法Aに載せて自動化
4. 当選チェック（toolc）用にGmailのアプリパスワードを設定
5. 自動応募（toola）は dry-run で十分確認してから --live


---

## 実フィードURLの見つけ方（詳しい手順）

「RSSフィードURL」とは、サイトが新着情報を機械向けに配信しているXMLの置き場所です。
`config.yaml` にこのURLを書くと、システムが毎回そこを見て新着懸賞を取り込みます。

### 方法1: 付属ツールで自動発見（おすすめ）

サイトのトップページURLを渡すと、生きているフィードを探して config.yaml 形式で出力します。
（実ネットワークが必要。ご自身のPC、またはGitHub ActionsのRun logで実行）

```bash
python find_feeds.py https://www.ken-kaku.com/ https://www.chance.com/
```

出力された `feeds:` ブロックを `config.yaml` にそのまま貼り替えればOK。
✅有効と出たURLだけが実際に読めるフィードです。

### 方法2: 手動で探す

1. サイトで「RSS」「フィード」「新着情報」リンクを探す
2. ブラウザでそのページを開き、アドレスバーのURLが `.xml` `.rdf` `/rss` `/feed` などなら候補
3. そのURLを `config.yaml` の `url:` に設定
4. `python main.py --dry-run` で「entries: ○件」と出れば成功

### フィードが無いサイトの場合

RSSを出していないサイト（フルーツメール等のメルマガ型）は、
- メルマガを懸賞専用Gmailで購読 → フェーズ3の当選チェック(toolc)が受信を処理
- または Google Alerts（「懸賞」等）のRSS出力を feeds に追加
で代替できます。

### 注意

- 各サイトの利用規約・robots.txt を確認し、公式に配信されているフィードを使ってください。
- うまく取れないサイトは無理にスクレイピングせず、公式RSS/メルマガのある情報源を優先します（設計の安全方針）。
