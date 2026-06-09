# 自治体・メーカーの無料系懸賞 取得戦略（実検証版）

ネット調査で各フィードの実在・規約・robots.txtを確認した結果。
「確認済」=実際にRSS配信/フィードURLを確認できたもの。

---

## 0. 重要な注意（使ってはいけないサイト）

- **懸賞生活 (knshow.com) は自動取得しない**。robots.txtでClaude含む主要AIボットを全面拒否、
  かつアクセスに503を返し自動取得を遮断している。規約・技術の両面でNG。手動閲覧のみ。
- **東京都・厚労省などの官公庁RSSは「再配布禁止」明記**。個人の収集用途に限定し、
  二次配信・メルマガ化はしない。

---

## 1. メーカー系（確認済フィードが最も充実）

| ソース | フィードURL | 確度 | 種別 |
|---|---|---|---|
| キャンなび (camnavi.net) | `https://camnavi.net/feed/` | **確認済**(application/rss+xml応答) | メーカー横断まとめ・WordPress |
| キャンなび カテゴリ別 | `https://camnavi.net/category/item/食品・飲料/feed/` 等 | 確認済(WP標準) | 「その場で当たる」等で絞込可 |
| 懸賞CLUB (kenshou.club) | `https://kenshou.club/feed/` | 高(WordPress確定) | メーカー横断・カテゴリ/タグ別feedも可 |
| おつかいねこ (tokaikensyo.com) | `https://tokaikensyo.com/feed/` ※設定済 | 中〜高(WordPress) | クローズド懸賞・ジャンル別 |
| **サントリー キャンペーン** | `https://www.suntory.co.jp/enjoy/campaign/rss.xml` | **確認済**(公式RSS案内に明記) | メーカー公式で唯一のキャンペーン専用RSS |
| 明治 プレス | `https://www.meiji.co.jp/news/meiji_press.xml` | 確認済(ただしプレスのみ・懸賞非網羅) | 補助 |
| 懸賞ライフ (kensyo-life.com) | RSS無し（静的HTML） | — | メーカー公式LP URLの抽出元として有用 |

メーカー公式の大半（アサヒGF・花王・カゴメ・ライオン等）はRSS非対応。
→ 公式X/LINEフォロー or メルマガ購読→Gmail受信(toolc) で代替。

## 2. 地域・自治体系

| ソース | フィードURL | 確度 | 備考 |
|---|---|---|---|
| 懸賞プレゼントキャンペーンPLUS (social-present.com) | `https://www.social-present.com/feed/` ／ 都道府県別ページ+`/feed/` | 推定(高・WordPress) | robots.txt一般許可(Crawl-Delay 5)。地域別に絞れる |
| にほんブログ村 懸賞 (money.blogmura.com/kenshou/) | カテゴリRSS(要find_feeds確定) | 推定(中) | robots.txtでAIボット非ブロック=取得可 |
| 懸賞当確 (ken-kaku.com) | `https://www.ken-kaku.com/rss.html` から確定 | 確認済(公式RSS配信明言) | 規約クリーン。地域カテゴリの有無は要確認 |
| マイ広報紙 (mykoho.jp) | 自治体広報を横断 | 補助 | 懸賞付きアンケートの発見に |

**自治体懸賞の実態（当たりやすい穴場）**:
- 種類: 観光クイズ懸賞、SNSフォロー&RP(高知「リョーマの休日」等)、アンケート謝礼、
  スタンプラリー、移住promotion、マイナ/アプリ普及(決済ポイント最大1万円超)、LINE公式施策。
- 当たりやすい理由: 地域限定で母数小、クイズ/アンケートで脱落者多、宣伝が地味＝穴場。
  協賛懸賞は全国の約1.7倍当たりやすい。アンケート/ポイント型は実質当選率100%。
- 賞品: 特産品・商品券・宿泊券・地域ポイントが中心。現金/Amazonギフトは稀
  (ふるさと納税は2025/10から汎用ポイント付与が全面禁止)。
- 告知場所: 観光協会サイト・自治体公式SNS/LINE・広報誌・移住特設サイト。

## 3. プレスリリース系（新キャンペーンを開始直後に捕捉）

| ソース | フィードURL | 確度 | 絞り込み |
|---|---|---|---|
| PR TIMES 全体 | `https://prtimes.jp/index.rdf` | **確認済**(XML応答) | 全件(1日数百件)→keyword_filter必須 |
| PR TIMES 企業別 | `https://prtimes.jp/companyrdf.php?company_id=<ID>` | 確認済(公式仕様) | **企業単位=最も低ノイズ**。狙いメーカーを登録 |
| @Press 最新 | `https://www.atpress.ne.jp/rss/index.rdf` | **確認済**(XML本文取得) | 全件→keyword_filter必須 |
| @Press(本文充実) | `https://www.atpress.ne.jp/rss/rdf.php?media_id=presscarry` | 確認済 | 同上 |

PR TIMESの`?keyword=`版は公式保証された仕様でないため、本番前に実出力を要検証。
基本は「全体/企業別RSS + keyword_filter(config)」で運用。

## 4. Googleアラート（取りこぼし防止・自治体狙い撃ち）

**RSS取得手順**: alerts作成時に頻度=「その都度」にする(これ以外だとRSS選択不可)→
配信先=RSSフィード→一覧のRSSアイコンを右クリックでURL取得。
形式: `https://www.google.com/alerts/feeds/<ID>/<ID>`

**すぐ使えるキーワード例**（「テーマ語 (懸賞語OR) (応募 OR 募集) -除外語」テンプレ）:
- 自治体: `"移住" ("プレゼント" OR "キャンペーン") -当選発表 -結果`
- 自治体: `("市" OR "町") "プレゼントキャンペーン" 応募 site:lg.jp`
- 居住地: `"○○市" ("懸賞" OR "プレゼント") (応募 OR 募集) -当選発表`（○○=居住地に置換）
- メーカー: `"新商品" "プレゼントキャンペーン" 応募 -当選発表`
- メーカー: `"レシート" ("応募" OR "キャンペーン") (抽選 OR プレゼント) -終了`
- 除外語テンプレ: `-当選発表 -当選者 -結果発表 -締切 -終了しました -ランキング`
- 演算子: 引用符=完全一致、大文字OR、丸括弧でグループ化、`-`除外、`site:lg.jp`/`go.jp`で公式に寄せる
- 件数: 15〜25件が現実的。全て「その都度+すべての結果+日本語/日本」。

---

## 5. find_feeds.py で検証するURLリスト（接続環境で実行）

```bash
python find_feeds.py \
  https://camnavi.net/ \
  https://kenshou.club/ \
  https://tokaikensyo.com/ \
  https://www.social-present.com/ \
  https://www.ken-kaku.com/ \
  https://money.blogmura.com/kenshou/

# メーカー公式の確認済フィードは直接configへ:
#   https://www.suntory.co.jp/enjoy/campaign/rss.xml
# プレスリリースは keyword_filter をONにして:
#   https://prtimes.jp/index.rdf
#   https://www.atpress.ne.jp/rss/index.rdf
```

## 6. A/Bへの振り分け（再掲）
- 自治体・地域・特産品（手動抽選・低競争）→ **ツールB**（コメント/属性/ペルソナで当選率UP）
- メーカーWeb即時当選・無料応募（自動抽選）→ **ツールA**（毎日反復で量産）
- メーカーのクローズド/レシート（普段買う商品限定）→ **ツールB**（高利益率）
- プレスリリース由来は keyword_filter で懸賞だけに絞ってから各ツールへ

## 7. 規約遵守メモ
- camnavi/kenshou.club/social-present/blogmura は取得許容範囲（robots.txt確認済）。
- knshow.com は除外（AIボット拒否＋503）。
- 官公庁RSSは個人利用限定（再配布禁止）。
- 取得時は実ブラウザUA・適切な間隔(Crawl-Delay尊重)で。
