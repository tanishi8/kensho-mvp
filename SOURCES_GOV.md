# 地方自治体の無料懸賞 取得戦略（実態調査版）

自治体懸賞は「地域限定で母数が小さい・手間で脱落者が多い」ため当たりやすい穴場。
全国懸賞比で約1.7倍当たりやすいという5年検証データもある。実態と取得経路を整理。

---

## 1. 自治体懸賞の4つの型と狙い目

| 型 | 例 | 当選数 | 当たりやすさ | 賞品 | 収集難度 |
|---|---|---|---|---|---|
| **観光クイズ/アンケート懸賞** | 浜田市(特産品1万円×20名)、小樽(Amazonギフト500円×毎月10名)、那須温泉(宿泊券1万円×5組) | 5〜20名・毎月型多い | **高**(常設フォームは応募者極少) | 特産品・宿泊券・金券 | 中(公式サイト/広報誌) |
| **広報誌のクイズ&プレゼント** | 京都府民だより、彩の国だより | 月30〜46名 | 中(府全域は応募3,917通/月の例) | 特産品・図書/QUOカード500円 | 低(マイ広報紙で横断検索) |
| **デジタルスタンプラリー** | 国見町(段階制・上位賞ほど少数)、私鉄10社 | 段階別・先着型あり | **高**(手間大＝脱落多、上位賞・先着が狙い目) | 特産品・商品券・グッズ | 低(スタンプラリー協会RSSあり) |
| **自治体SNS/LINE懸賞** | 高知「リョーマの休日」(クーポン5千円×100名)、ふるまど(特産品×1,000名) | 100〜1,000名と多い | 高(当選枠大) | クーポン・デジタルギフト | 高(SNSはRSS化困難) |

**重要な示唆**: 観光協会の「常設アンケート懸賞」は、専用ページに気づいた人だけが応募するため
応募者が極端に少なく、毎月当選者が出る＝最も効率が良い穴場。

---

## 2. 実在する取得経路（RSS確認状況つき）

### A. スタンプラリー（最も取得しやすい）
- **日本スタンプラリー協会 (stamprally.org)** が全国横断アグリゲーター。
  - **公開RSSあり**: `https://stamprally.org/feed`
  - 「景品あり」категория6,940件、都道府県別・タグ絞り込み可。公式X @jsainfo123 も毎日配信。
  - → **これは即configに追加可能な最有力ソース**。

### B. 広報誌（横断検索が現実解）
- **マイ広報紙 (mykoho.jp)**: 全国約1,000紙をテキスト化。**公開RSSは無い**が、
  全文検索 `https://mykoho.jp/search?keyword=プレゼント` 等が機械可読で横断把握に有効。
  → スクレイピング親和性は高いが、RSSは無いので「定期検索」での取り込みを検討。

### C. 自治体公式サイトのRSS（CMS別にパターンが違う）
自治体CMSごとにURL形式が異なる。find_feedsの<link>解析＋パターン総当たりで取得。
| CMS/自治体 | RSSパターン例 |
|---|---|
| 大阪市 | `/event/rss/rss_new.xml`(イベント・観光) ほか分野別 |
| 福岡市 | `/data/open/rss/RSS_7236.xml`(観光・魅力・イベント) |
| 札幌市 | `/boshu/boshuu.xml`(募集を独立配信) |
| 徳島県(Joruri CMS) | `/file/rss/..._kyoiku_kanko_index.rss`(観光) |
| 愛知県 | `/rss/10/list1.xml`(新着)、list7(記者発表) |
| 栃木県 | `/c05/.../shinchaku.xml` |
| 東京都 | `metro.tokyo.lg.jp/policy/rss`(案内ページ) |
| 観光協会(WordPress) | `/feed/`、`/category/event/feed/` |

→ 自治体RSSは「報道発表・新着の全件」が流れるので **keyword_filter必須**。
   懸賞語(プレゼント/抽選/募集/プレゼントキャンペーン/モニター)で絞る。

### D. 集約まとめ + Googleアラート（取りこぼし防止）
- 懸賞プレゼントキャンペーンPLUS (social-present.com) 都道府県別 + `/feed/`
- 懸賞当確 (ken-kaku.com) の地域カテゴリ
- Googleアラート: `"○○市" ("懸賞" OR "プレゼント") (応募 OR 募集) site:lg.jp -当選発表`
  （○○=居住地。site:lg.jp で自治体公式に絞ると精度UP）

---

## 3. find_feeds.py に渡すURLリスト（接続環境で実行）

```bash
python find_feeds.py \
  https://stamprally.org/ \
  https://www.social-present.com/ \
  https://www.city.osaka.lg.jp/ \
  https://www.city.fukuoka.lg.jp/ \
  https://www.city.sapporo.jp/ \
  https://www.pref.tokushima.lg.jp/ \
  https://www.pref.aichi.jp/ \
  https://www.pref.tochigi.lg.jp/

# 確認済みで直接configに足せるもの:
#   https://stamprally.org/feed            （スタンプラリー・景品あり多数）
# 居住地の自治体トップURLを足して実行するのが最重要
```

---

## 4. 注意点（応募前に必ず確認）

- **応募資格欄を必ず確認**: 「○○県在住者限定」「店舗利用者限定」は地域外だと応募不可。
  観光promotion・スタンプラリーは集客目的で**全国対象が多い**(県外でも応募可)。
- **賞品は換金性が低め**: 特産品・地域商品券・宿泊券が中心。現金/Amazonギフトは稀。
  利益率では「実用品として使う」前提なら高く、「売って稼ぐ」には不向き。
- **ふるさと納税は2025/10から汎用ポイント付与が全面禁止**。抽選型は各ポータルのキャンペーンページ確認。
- **官公庁RSSは個人利用限定**(再配布禁止)。本システムは個人利用なので問題なし。
- **SNS懸賞はRSS化が困難**: まとめサイト経由＋気になる案件のみ本体確認のハイブリッドが現実解。
  応募(RT)はツールB(人間)で。

---

## 5. A/Bへの振り分け
- 観光クイズ/アンケート/スタンプラリー(手間あり・手動抽選) → **ツールB**
  （コメント・属性・継続応募で当選率UP。利益率の主戦場）
- 自治体SNSフォロー&RP → **ツールB**（収集は自動、RTは人間）
- メール/Webフォームのアンケート懸賞 → **ツールA**（CAPTCHA無しなら自動応募）

---

## 出典（主要）
- 日本スタンプラリー協会RSS: https://stamprally.org/feed
- マイ広報紙: https://mykoho.jp/
- 京都府民だより クイズ&プレゼント(応募3,917通): https://www.pref.kyoto.jp/koho/dayori/quiz.html
- 小樽観光アンケート(毎月10名): https://otaru.gr.jp/project/otaru-visitor-survey2024
- 高知「リョーマの休日」(100名): https://www.comnico.jp/news/kochi-kanko-sns-support-twitter-campaign
- 大阪市RSS: https://www.city.osaka.lg.jp/main/site_policy/0000000148.html
- 福岡市RSS: https://www.city.fukuoka.lg.jp/sub/rss.html
- 懸賞主婦 協賛懸賞1.7倍検証: https://kensho-everyday.com/archives/165428
- 達人わこ ローカル懸賞実体験: https://www.moneypost.jp/1034021/3/
