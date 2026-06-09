# 懸賞サイト フィード調査結果と推奨設定

過去の調査で挙がった懸賞サイトについて、RSSフィードの提供状況を確認した結果です。
config.yaml には確度の高いものを設定済み。稼働前に `find_feeds.py` で最終検証してください。

## 結論（確度順）

| サイト | 種別 | RSS提供 | 推奨URL（要検証） | 確度 |
|---|---|---|---|---|
| おつかいねこ(tokaikensyo.com) | WordPressブログ | 標準仕様であり | https://tokaikensyo.com/feed/ | 高 |
| 懸賞主婦(kensho-everyday.com) | WordPressブログ | 標準仕様であり | https://kensho-everyday.com/feed/ | 高 |
| 懸賞当確(ken-kaku.com) | 独自システム | 公式に配信を明言 | find_feedsで確定 | 中 |
| にほんブログ村 懸賞(money.blogmura.com/kenshou) | 集約サイト | RSSあり | find_feedsで確定 | 中 |
| チャンスイット(chance.com) | 独自システム | 不明（メルマガ中心） | メルマガ購読で代替 | 低 |
| 懸賞生活(knshow.com) | 独自システム | 不明（メルマガ・X中心） | メルマガ購読で代替 | 低 |
| フルーツメール(fruitmail.net) | 独自システム | 不明（メルマガ中心） | メルマガ購読で代替 | 低 |
| 懸賞なび(kenshonavi.com) | 会員制（一部有料） | 不明 | 規約注意・優先度低 | 低 |

## 調査でわかったこと

1. **WordPress製ブログは `/feed/` で確実にRSSが取れる**（WordPress標準仕様）。
   おつかいねこ・懸賞主婦はこれに該当し、最も確実な情報源。
   カテゴリ別も可：`/category/カテゴリ名/feed/`（例：クローズド懸賞だけ集める等）。

2. **懸賞当確は公式にRSS配信を明言**しているが、正確なフィードURLはJS描画のため
   検索で断定できず。`find_feeds.py https://www.ken-kaku.com/` で確定する。

3. **独自システム系（チャンスイット・懸賞生活・フルーツメール）はメルマガ中心**で
   RSSの有無が不確実。これらは「懸賞専用Gmailでメルマガ購読 → toolc(当選/新着)で
   受信処理」または Google Alerts のRSS化で代替するのが安全。

## 推奨：まず2サイトで開始 → 検証して拡張

config.yaml には確度【高】の2フィード（おつかいねこ・懸賞主婦）を設定済み。
この2つだけでもクローズド懸賞中心に毎日の新着が集まり、当選率の高いジャンルを押さえられる。

### 稼働前の検証手順

```bash
# 設定済みフィードと、追加候補をまとめて検証
python find_feeds.py https://tokaikensyo.com/ https://kensho-everyday.com/ \
                     https://www.ken-kaku.com/ https://money.blogmura.com/kenshou/

# 「✅有効(○件)」と出たURLだけを config.yaml の feeds に残す／追加する
# 動作確認:
python main.py --dry-run        # 「entries: ○件」と出れば取得成功
```

## メルマガ型サイトの取り込み（RSSが無い場合）

1. 懸賞専用Gmailを作成
2. フルーツメール/チャンスイット等のメルマガを購読
3. フェーズ3の `toolc.py` がそのGmailを受信処理（当選通知だけでなく
   新着お知らせも届く）。IMAP設定は STARTUP.md 参照。

## 注意

- 各サイトの利用規約・robots.txt を確認し、公式配信のフィードを使うこと。
- WordPressでもテーマ設定でRSSを止めている場合があるため、必ず find_feeds で実検証する。
- フィードが404や0件の場合は無理にスクレイピングせず、メルマガ/Alertsで代替する（設計の安全方針）。
