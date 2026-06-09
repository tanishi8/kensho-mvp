"""
RSSフィード取得の共通ヘルパー。
- ブラウザらしい User-Agent を送って 403 を回避
- 1フィードが失敗しても例外を投げず、空扱いで次へ進む（堅牢性）
"""
import feedparser

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/124.0 Safari/537.36 kensho-mvp/1.0")


def parse(url):
    """1フィードを取得。失敗時は entries 空のオブジェクトを返す（例外を投げない）。"""
    try:
        d = feedparser.parse(url, agent=USER_AGENT)
        status = getattr(d, "status", 200)
        if status in (401, 403, 404, 410, 500, 503):
            print(f"  [警告] {url} がHTTP {status}。スキップします。")
            return feedparser.util.FeedParserDict(entries=[])
        return d
    except Exception as e:
        print(f"  [警告] {url} の取得に失敗: {type(e).__name__}。スキップします。")
        return feedparser.util.FeedParserDict(entries=[])
