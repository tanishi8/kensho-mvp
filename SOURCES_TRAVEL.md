# 全国の観光懸賞・宿泊券・名産品 収集セット（広島在住・全国狙い）

方針: 観光協会の常設/期間限定アンケート懸賞を最優先、スタンプラリーも併用。
広島在住だが他地域の名産品・宿泊券を狙うため、全国応募可のオープン懸賞を中心に集める。

---

## 1. 最優先：本命の常設アンケート/クイズ宿泊券懸賞（全国応募可・確認済）

毎月当選者が出る常設型。集約サイトに埋もれて競争が緩い＝当選率が高い。
これらは個別に巡回 or メルマガ登録で取りこぼし防止。

| 主催 | 賞品 | 頻度 | 応募 | URL |
|---|---|---|---|---|
| 那須温泉旅館協同組合 | 宿泊クーポン1万円×5組 | 準常設(回更新) | Webフォーム | https://www.nasuonsen.com/present/ |
| 伊豆網代温泉観光協会 | ペア平日無料宿泊券×毎月1組 | 常設(毎月) | Webアンケート | https://ajirospa.com/ |
| ホテルエピナール那須 | 1泊2食ペア平日宿泊券×毎月1組 | 常設(毎月クイズ) | Webクイズ | https://www.epinard.jp/presentquiz/ |
| ホテル春日居(山梨) | ペア宿泊券 | 常設 | メルマガ会員で自動応募 | https://www.hotel-kasugai.com/kensyo/ |
| THE信州(長野観光情報誌) | 信州の宿泊券+特産品 | 毎号(常設的) | ハガキ | http://www.the-shinshu.com/19_present/present.html |
| 大江戸温泉物語 いいふろ会員 | 全国35施設で使える平日無料宿泊券×200名 | 入会キャンペーン | 会員登録 | (要検索・全国応募可) |

## 2. 横断収集：観光・宿泊・名産品に強い集約カテゴリ

| ソース | カテゴリ | URL | RSS |
|---|---|---|---|
| Koubo（公募ガイド） | 旅行券・チケット・招待券 | https://koubo.jp/category/present/travel-voucher | 要確認(在住制限/締切が明記され選別しやすい) |
| Koubo | アンケート懸賞 | https://koubo.jp/category/nonsection/questionnaire | 要確認 |
| チャンスイット | 旅行・宿泊(日次大量更新・最有力) | https://www.chance.com/present/list/travel/ | HTMLスクレイプ |
| 懸賞当確 | 宿泊券 | https://www.ken-kaku.com/cgi-bin/present/present.cgi?id=105070000 | X@kentoukaku監視 |
| 懸賞当確 | 特産品・名産品 | https://www.ken-kaku.com/cgi-bin/present/present.cgi?id=101030000 | 同上 |
| 懸賞生活 | クイズ・アンケート懸賞 | https://www.knshow.com/quizsurvey/ | ※knshowはAIボット拒否=取得不可。手動閲覧のみ |
| 懸賞ニュース(WordPress) | 宿泊券カテゴリ | https://kensho-news.com/category/accommodation-voucher/feed/ | **/feed/有望** |
| 懸賞主婦(WordPress) | 宿泊券・旅行券タグ | https://kensho-everyday.com/feed/ | **/feed/有望** ※設定済 |

## 3. スタンプラリー（全国・賞品郵送型を狙う）

| ソース | 内容 | URL | RSS |
|---|---|---|---|
| 日本スタンプラリー協会 | 全国横断・景品あり6,940件 | https://stamprally.org/feed | **RSS確認済(最有力)** |
| └景品あり新着順 | 絞り込み(RSS化ツールでフィード化) | https://stamprally.org/s/category2/gift1?sort=date_desc | RSS.app等で生成 |
| ニフティ温泉「湯まわり」 | 会員登録でスタンプ付与・賞品郵送(遠隔可) | https://onsen.nifty.com/campaign/stamprally-ranking2025/ | 個別巡回 |
| 文化庁 100年フード | 上位10名確定・賞品郵送 | https://www.bunka.go.jp/.../hyakunenfood/stamprally/ | 個別巡回 |
| furari(WEB参加可あり) | 開催中一覧 | https://digital-stamprally.jp/open_rally/ | 巡回/RSS化 |

広島から狙う現実解: ①会員/マイページでスタンプ付与される企画(湯まわり型) ②SNSフォロー&RP型(完全在宅) ③通販レシートで成立する購入型 ④賞品郵送の全国GPS型で広島が対象。

## 4. 期間限定・新設サイトの早期捕捉（当選率が高い段階で捕まえる）

新キャンペーンは検索インデックス前にプレスリリースで告知される。これを起点に。

- PR TIMES 全体RSS（確認済）: `https://prtimes.jp/index.rdf` → keyword_filterで観光・懸賞語に絞る
- PR TIMES 企業別RSS: `https://prtimes.jp/companyrdf.php?company_id=ID`（DMO/さとふる等を登録＝低ノイズ）
- 国土交通省 プレスRSS（確認済）: `https://www.mlit.go.jp/pressrelease.rdf`
- @Press 最新: `https://www.atpress.ne.jp/rss/index.rdf`
- Googleアラート(RSS出力): 「観光 キャンペーン 特設サイト」「宿泊券 プレゼント」「フォトコンテスト 応募 観光」「デジタルスタンプラリー 開始」

## 5. 参考：広島・中国地方で全国応募可（確認済RSS）

- **せとうちDMO**: `https://setouchitourism.or.jp/ja/info/feed/` ← **RSS稼働確認済**
- Dive! Hiroshima: `https://dive-hiroshima.com/feed/`（WordPress・要確認）
- ひろしま観光ナビ: `https://www.hiroshima-kankou.com/feed/`（同上）

---

## 6. find_feeds.py 検証リスト（接続環境で実行）

```bash
python find_feeds.py \
  https://stamprally.org/ \
  https://setouchitourism.or.jp/ja/info/ \
  https://kensho-news.com/ \
  https://kensho-everyday.com/ \
  https://dive-hiroshima.com/ \
  https://www.hiroshima-kankou.com/ \
  https://koubo.jp/

# 確認済みで直接configに足せる:
#   https://stamprally.org/feed                     （スタンプラリー）
#   https://setouchitourism.or.jp/ja/info/feed/     （せとうちDMO）
#   https://prtimes.jp/index.rdf                    （keyword_filter ON）
#   https://www.mlit.go.jp/pressrelease.rdf         （keyword_filter ON）
```

## 7. 運用のコツ
- 常設アンケート懸賞(セクション1)は巡回 or メルマガ自動応募で「毎月応募」を習慣化。試行回数が当選数に直結。
- PR TIMES/国交省/Googleアラートは keyword_filter を ON にして懸賞語に絞る。
- 応募前に必ず「対象者/居住地」欄を確認(観光promotionは全国可が多いが稀に在住限定)。
- 遠方の宿泊券は交通費自己負担を踏まえて応募判断。名産品(郵送)は気にせず全国狙い。
- 当選通知のなりすましDM注意(toolcの詐欺判定が自動で弾く)。

## 出典（主要・確認済フィード）
- 日本スタンプラリー協会RSS: https://stamprally.org/feed
- せとうちDMO RSS: https://setouchitourism.or.jp/ja/info/feed/
- PR TIMES RSS: https://prtimes.jp/index.rdf
- 国交省 プレスRSS: https://www.mlit.go.jp/pressrelease.rdf
- 那須温泉組合 宿泊券: https://www.nasuonsen.com/present/
- エピナール那須 毎月クイズ: https://www.epinard.jp/presentquiz/
- Koubo 旅行券カテゴリ: https://koubo.jp/category/present/travel-voucher
- チャンスイット 旅行宿泊: https://www.chance.com/present/list/travel/
