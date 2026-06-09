# 懸賞自動化システム プロジェクト索引

当選率最大化 × 安全 × ゼロ円を方針に、ツールA(ほぼ完全自動)とツールB(半自動)の
2系統で懸賞に応募し、本物の当選だけを受け取るシステム。

## まず読むもの
- **DEPLOY.md** … 実稼働セットアップ手順（GitHub Actions・チェックリスト式）★まずこれ
- **STARTUP.md** … 稼働開始ガイド（補足）
- **README.md** … 全機能の使い方
- **FEEDS.md** … 懸賞サイトのフィード調査結果と設定
- **INDEX.md**（本書）… 全体の地図

## 調査・設計ドキュメント
| ファイル | 内容 |
|---|---|
| 懸賞システム設計書.docx / .md | システム全体の設計書（全12章） |
| 懸賞システム_調査レポート.md | ①当選率を上げる方法・技術・規約 |
| 懸賞システム_調査レポート2_完全自動と転売.md | ②完全自動の可否・市場価値・換金/転売 |
| 懸賞システム_調査レポート3_当選率最大化.md | ③当選率最大化テク・抽選方式の区別 |
| PROFITABILITY.md | 利益率分析（どこの懸賞が儲かるか） |
| TAX_CASHOUT.md | 税務・換金チェックリスト（当選額が増えたとき用） |
| FINAL_RESEARCH.md | 最終大規模調査（手続き/税務/換金/最新動向/高度化） |
| ALERTS.md | Googleアラート キーワード一式（地酒・海産物・食品狙い） |
| SOURCES.md | 追加データ取得源の拡張プラン |
| SOURCES_LOCAL.md | 自治体・メーカー懸賞の取得戦略 |
| SOURCES_GOV.md | 地方自治体懸賞の取得戦略（実態調査版） |
| SOURCES_TRAVEL.md | 全国の観光懸賞・宿泊券・名産品 収集セット（広島・全国狙い） |

## コード（モジュール）
| ファイル | 役割 | フェーズ |
|---|---|---|
| extract.py | 懸賞テキストの構造化抽出（正規表現） | 0 |
| llm_extract.py | LLM二次抽出（Gemini既定・provider切替） | 0+ |
| score.py | 期待価値＋利益率スコアリング | 0 |
| cost.py | 応募コスト推定（利益率計算用） | + |
| notify.py | Discord通知 | 0 |
| main.py | フェーズ0 CLI（収集→通知） | 0 |
| applog.py | 応募ログDB | 1 |
| comment.py | コメント案生成 | 1 |
| toolb.py | ツールB CLI（半自動：優先リスト・応募記録） | 1 |
| gate.py | 応募可否ガードレール | 2 |
| profile.py | 応募者プロファイル・フォーム項目マッピング | 2 |
| apply_email.py | メール応募 | 2 |
| apply_form.py | Webフォーム自動入力（Playwright） | 2 |
| toola.py | ツールA CLI（自動応募：plan/run/escalations） | 2 |
| fraud_check.py | 当選通知の詐欺判定 | 3 |
| inbox.py | メール受信（IMAP） | 3 |
| toolc.py | 当選抽出 CLI（本物のみ通知） | 3 |
| find_feeds.py | RSSフィード自動発見ツール | 補助 |
| report.py | 当選率・収支の集計CSV出力 | 改善 |

## 設定・データ
| ファイル | 内容 |
|---|---|
| config.yaml | フィード・スコア重み・コスト・LLM・通知設定 |
| profile.sample.json | 応募者情報の雛形（→ profile.json にコピー） |
| whitelist.sample.json | 主催者ホワイトリストの雛形 |
| sample_feed.xml / .json | テスト用サンプル |
| notices_sample.json | 当選通知のテストサンプル |

## コマンド早見表
```bash
python main.py                     # 狙い目を通知（フェーズ0）
python toolb.py list               # 優先リスト＋コメント案（半自動）
python toolb.py apply <id>         # 応募を記録
python toolb.py stats              # 当選率集計
python toola.py plan               # 自動応募の可否確認
python toola.py run [--live]       # 自動応募（dry-run→本番）
python toolc.py run                # 当選チェック（本物のみ通知）
python find_feeds.py <URL>...      # フィードURL自動発見
```

## 並び順の切替（config.yaml）
- `rank_by: roi` … 利益率順（コスパ重視・既定）
- `rank_by: score` … 期待価値順（大きく当てたい）

## 稼働に必要な環境変数（接続後に設定）
| 変数 | 用途 |
|---|---|
| DISCORD_WEBHOOK_URL | 通知先（必須） |
| GEMINI_API_KEY | LLM二次抽出（任意） |
| IMAP_HOST/USER/PASS | 当選チェックのメール受信（toolc） |
| SMTP_HOST/PORT/USER/PASS | メール応募の実送信（toola） |
