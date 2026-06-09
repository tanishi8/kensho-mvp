# 懸賞MVP（フェーズ0）

懸賞情報を **収集 → 抽出 → スコアリング → Discord通知** する最小システム。
設計書「10. 開発ロードマップ フェーズ0」に対応。当選率最大化 × 安全 × ゼロ円が方針。

## 何をするか

1. **収集**：設定したRSSフィード（懸賞当確など）から新着懸賞を取得
2. **抽出**：タイトル・本文から賞品ジャンル/応募方式/当選本数/賞品額/地域限定/手動抽選を正規表現で抽出
3. **スコアリング**：期待価値 = 当選確率係数 × 市場価値 × 換金率 × 必要度 × ボーナス（地域限定×1.7、手動抽選、当選本数、12月など）で順位付け
4. **通知**：上位N件を Discord に通知。`seen.json` で重複通知を防止

「手間がかかる方式（クローズド/レシート/はがき）・地域限定・手動抽選・当選本数が多い」ものが上位に来るよう、調査の実測当選率に基づいて重み付けしてあります。

## セットアップ

```bash
pip install -r requirements.txt
```

### Discord Webhook を用意
Discordサーバー → チャンネル設定 → 連携サービス → ウェブフック → 新しいウェブフック → URLをコピー。

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

### RSSフィードURLを設定
`config.yaml` の `feeds:` に実際のフィードURLを記入してください。
※各サイトの利用規約・robots.txt を確認のうえ、公式提供のRSSを使うこと。

## 使い方

```bash
# サンプルデータで動作確認（通知せず標準出力、seen.jsonも更新しない）
python main.py --sample sample_feed.json --dry-run

# 本番実行（RSS収集 → Discord通知）
python main.py

# 手元確認（DISCORD_WEBHOOK_URL未設定なら標準出力に出る）
python main.py --dry-run
```

## 自動実行（GitHub Actions・無料）

1. このフォルダを GitHub リポジトリにプッシュ
2. リポジトリの Settings → Secrets and variables → Actions に
   `DISCORD_WEBHOOK_URL` を登録
3. `.github/workflows/daily.yml` が毎日 JST 8:00 に自動実行（手動実行も可）

> scheduleはGitHub側の都合で遅延することがあります。時刻厳守が必要になったら
> 外部cronから `workflow_dispatch` を叩く構成に変更してください（設計書7章）。

## ファイル構成

| ファイル | 役割 |
|---|---|
| `main.py` | エントリポイント（収集→抽出→スコア→通知） |
| `extract.py` | 懸賞テキストの構造化抽出（正規表現） |
| `score.py` | 期待価値スコアリング |
| `notify.py` | Discord Webhook 通知 |
| `config.yaml` | フィードURL・スコア重み・通知件数 |
| `sample_feed.json` | テスト用サンプル |
| `.github/workflows/daily.yml` | 毎日自動実行 |

## カスタマイズのポイント

- **スコアの重み**：`config.yaml` の `scoring:` を調整
- **ジャンル/方式の判定語**：`extract.py` の各キーワード辞書を追加
- **抽出精度を上げる**：フェーズ1でLLM（Gemini無料枠/ローカルLLM）による二次抽出を追加（設計書4.2）

## 次フェーズ（設計書より）

- フェーズ1：応募ログDB + 優先リスト + コメント案/入力補助（ツールB）
- フェーズ2：メール/CAPTCHA無しフォームの自動応募・即時当選の反復（ツールA）
- フェーズ3：詐欺判定パイプライン → 本物の当選のみメール出力

## 注意

- 自動応募/bot/複数応募を禁止する懸賞・サイトには応募しないこと（このMVPは収集と通知のみで、応募は行いません）。
- 検出回避技術（指紋偽装・CAPTCHA突破等）は使用しない方針です。


## フェーズ1（ツールB：半自動）の使い方

収集した懸賞をスコア順に提示し、コメント案を出し、応募状況を記録します。応募自体は人間が行います。

```bash
# 優先リスト＋コメント案を表示（候補は応募ログに自動登録される）
python toolb.py list --sample sample_feed.xml --top 10
python toolb.py list                      # 本番（config.yamlのRSS）

# 表示された [id] を使って状況を記録
python toolb.py apply <id>    # 応募した
python toolb.py won   <id>    # 当選した
python toolb.py lost  <id>    # 落選した

# 集計（応募ベースの当選率も表示）
python toolb.py stats
```

- `applog.json` が応募ログDB（設計書4.7）。後のフェーズ3「本物の当選だけ抽出」で当選通知の突合に使います。
- コメント案は「応募理由＋具体的な使い道」の2文構成（定型文は避ける）。手動抽選・モニターほど効果的。
- 記録を貯めると、自分がどのジャンル/方式で当たりやすいかを `stats` で振り返れます。

### ファイル追加分

| ファイル | 役割 |
|---|---|
| `toolb.py` | ツールB CLI（優先リスト・コメント案・応募記録・集計） |
| `applog.py` | 応募ログDB（候補登録・ステータス管理） |
| `comment.py` | コメント案の自動生成と助言 |


## LLM二次抽出（精度アップ・既定Gemini）

正規表現で取り切れない曖昧表現（「豪華賞品」「総額100万円相当」「本数が文中に分散」など）をLLMで補完します。正規表現で確実に取れた項目は上書きせず、空欄だけをLLMで埋める安全設計です。

### Geminiを使う場合（無料枠：1日250リクエスト想定）

1. Google AI Studio（https://aistudio.google.com/apikey ）でAPIキーを取得
2. 環境変数に設定し、`config.yaml` の `llm.provider` を `gemini` に（既定でgemini）

```bash
export GEMINI_API_KEY="取得したキー"      # Mac/Linux
# $env:GEMINI_API_KEY="..."               # Windows PowerShell
```

GitHub Actionsで使う場合は、Secretに `GEMINI_API_KEY` を追加し、`daily.yml` の env に
`GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}` を足してください。

### LLMを使わない場合（完全無料）

`config.yaml` で `llm.provider: none` にするか、APIキーを設定しなければ、自動的に正規表現のみで動作します（キーが無い/通信失敗時も安全にフォールバック）。

### Claudeに切り替える場合

`llm.provider: claude` にし、`ANTHROPIC_API_KEY` を設定。日本語の構造化精度が高い一方、無料枠は無く従量課金（Haikuで1件0.1円未満）です。

### モデル・料金の注意

- 既定モデルは `gemini-2.5-flash`（`llm_extract.py` の `GEMINI_MODEL`）。
- Gemini 2.0 Flashは2026年6月1日で終了済みのため2.5を使用。
- 無料枠の条件は変わることがあるため、利用前に公式の料金ページを確認してください。

### ファイル追加分

| ファイル | 役割 |
|---|---|
| `llm_extract.py` | LLM二次抽出（Gemini既定・provider切替・安全フォールバック） |


## フェーズ2（ツールA：ほぼ完全自動の応募）の使い方

完全自動が安全に成立する方式（メール／CAPTCHA無しWebフォーム／即時当選／アンケート）だけを
ガードレールで選び、自動応募します。**SNS・はがき・購入必須クローズドは自動応募しません**（ツールB送り）。

### 安全の二重歯止め

1. `gate.py` が応募前に方式・CAPTCHA・規約を判定。`auto` のものだけ応募
2. `apply_form.py` はページHTMLでCAPTCHA/禁止文言を再判定し、未対応フォーム項目があれば中止
3. **既定は dry-run（実送信しない）**。実送信は `--live` を明示したときだけ

### 準備

```bash
# 応募者情報を用意（自分の実際の情報を入れる。虚偽属性は使わない）
cp profile.sample.json profile.json
# profile.json を編集

# フォーム応募を使う場合のみ Playwright を導入
pip install playwright && python -m playwright install chromium
```

### 使い方

```bash
# 応募可否を一覧（🟢auto=自動応募可 / 🟡escalate=人間対応 / ⚪skip=対象外）
python toola.py plan --sample sample_feed.xml
python toola.py plan                       # 本番（config.yamlのRSS）

# 自動応募（dry-run：内容を確認するだけ、送信しない）
python toola.py run --sample sample_feed.xml

# 実際に応募（規約・内容を確認のうえ）
python toola.py run --live

# 人間が対応すべき懸賞（CAPTCHA・規約NG・項目不明）の一覧
python toola.py escalations
```

### メール応募の実送信に必要な環境変数

```bash
export SMTP_HOST="smtp.example.com"
export SMTP_PORT="587"
export SMTP_USER="you@example.com"
export SMTP_PASS="アプリパスワード"
```

### ファイル追加分

| ファイル | 役割 |
|---|---|
| `toola.py` | ツールA CLI（plan/run/escalations） |
| `gate.py` | 応募可否ガードレール（方式・CAPTCHA・規約判定） |
| `profile.py` | 応募者プロファイル管理・フォーム項目マッピング |
| `profile.sample.json` | プロファイルの雛形（→ profile.json にコピーして編集） |
| `apply_email.py` | メール応募（dry-run既定） |
| `apply_form.py` | Webフォーム自動入力（Playwright・dry-run既定・CAPTCHA再判定） |

### 重要な注意

- このツールは「規約で自動応募が許可/黙認されている方式」だけを自動化します。各サイトの利用規約を必ず確認してください。
- `profile.json` は個人情報のためGit管理対象外（.gitignore済み）。
- 検出回避（CAPTCHA突破・指紋偽装等）は実装していません。CAPTCHAが出たら人間が対応します。


## フェーズ3（ツールA：当選抽出）の使い方

受信した当選通知を詐欺判定にかけ、**本物（genuine）だけ**をDiscordに通知します。
要確認（review）は人間判断用、詐欺（reject）は捨てます。これまで貯めた応募ログ（applog.json）が判定の土台です。

### 判定ロジック（多段・安全側）

1. 即除外キーワード（送料/手数料/先払い/クレカ番号/暗証番号など）→ 1語でも即アウト
2. 応募ログ突合 → 未応募の「当選」は詐欺の典型として大幅減点
3. ホワイトリスト → 送信者の@ID/ドメインが正規と完全一致で加点、主催名一致なのにID違いは「なりすまし」で除外
4. メール認証 → DMARC=pass必須（failで減点）、表示名とドメインの不一致を検出
5. SNSバッジ → 金バッジは加点、青バッジは課金で誰でも取れるため信頼根拠にしない

### 準備（あなたに用意してもらうもの）

**メール受信（必須）** — 懸賞専用Gmailで2段階認証を有効化し「アプリパスワード」を発行：

```bash
export IMAP_HOST="imap.gmail.com"
export IMAP_USER="あなたの懸賞用@gmail.com"
export IMAP_PASS="アプリパスワード（16桁）"
```

**ホワイトリスト（任意・精度向上）** — `whitelist.sample.json` を `whitelist.json` にコピーし、
応募した主催の公式ドメイン/公式@IDを追記。応募ログ（applog.json）の公式情報も自動で使われます。

**出力先** — Discord（既定）。`DISCORD_WEBHOOK_URL` を設定すれば本物の当選がDiscordに届きます。

### 使い方

```bash
# サンプルで判定結果を確認（通知しない）
python toolc.py test --sample notices_sample.json

# 本番：未読メールを受信→判定→本物だけDiscordに通知
python toolc.py run
```

### ファイル追加分

| ファイル | 役割 |
|---|---|
| `toolc.py` | 当選抽出CLI（受信→判定→本物のみ通知） |
| `fraud_check.py` | 詐欺/スパム判定（多段フィルタ） |
| `inbox.py` | メール受信（IMAP）→ notice 変換、SPF/DKIM/DMARC抽出 |
| `whitelist.sample.json` | 主催者ホワイトリストの雛形（→ whitelist.json にコピー） |
| `notices_sample.json` | 当選通知のテストサンプル |

### 重要

- 判定は「本物を弾いてでも詐欺を通さない」安全側設計です。reviewに落ちた本物は手動で確認してください。
- SNSの当選を本物判定させるには、応募時（ツールB）に主催の公式@IDを記録するのが有効です。
- ブラックリスト（既知の詐欺ドメイン/@ID）は定期的に更新すると精度が上がります。


## 利益率スコアリング（コスパ順の並び替え）

期待価値に加えて「利益率（roi＝期待価値÷応募コスト）」を計算し、コスパの良い懸賞を上位に出せます。

- **コスト推定（cost.py）**: 方式別の時間コスト＋郵送費＋購入費。クローズド懸賞でも
  config の `cost.buy_list`（普段買う商品キーワード）に一致すれば追加コスト0扱い＝高利益率。
- **確定報酬**: モニター等は当選率=1.0として期待値計算（抽選でないため）。
- **並び替え**: config の `rank_by` で切替。
  - `rank_by: roi` … 利益率順（コスパ重視・既定）
  - `rank_by: score` … 期待価値順（大きく当てたい）

利益率順にすると「コストほぼゼロで当たりやすい無料系・自治体懸賞」が上位に、
買い増しが必要なクローズドは下位に並びます（PROFITABILITY.md の分析に基づく）。

### 結合テスト

```bash
python selftest.py     # 全モジュールの連携を検証（オフライン・12項目）
```

### ファイル追加分

| ファイル | 役割 |
|---|---|
| cost.py | 応募コスト推定（利益率計算用） |
| selftest.py | 結合テスト（品質ゲート・ネット不要） |
| INDEX.md | プロジェクト全体の索引 |


## 追加機能（改善実装）

```bash
# デイリーサマリー通知（件数・好み一致・締切近・利益率TOP5を要約）
python main.py --summary

# 受取期限リマインダー（当選後の失効防止。期限N日以内の当選を通知）
python toolc.py remind --days 3

# 当選率・収支レポート（CSV出力。Looker Studio/Excelで可視化）
python report.py
```

- 受取期限は `applog` の `receive_deadline`(YYYY-MM-DD) に記録（当選記録時に設定）。
- 好みジャンル加点は `config.yaml` の `preference` で調整（地酒・海産物・特産品など）。
- 税務・換金の実務メモは `TAX_CASHOUT.md`、Googleアラートのキーワードは `ALERTS.md` を参照。
