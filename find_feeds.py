"""
RSSフィード自動発見ツール。
サイトのトップページURLを渡すと、
  1) HTML内の <link rel="alternate" type="application/rss+xml"> を探す
  2) よくあるパス（/rss, /feed, /index.rdf 等）も試す
  3) 各候補に実アクセスして「本当にRSSとして読めるか」を検証
  4) 生きているフィードを config.yaml に貼れる形式で出力
する。

使い方:
  python find_feeds.py https://example.com [https://other.com ...]

※このツールは実ネットワークが必要。GitHub Actions上やご自身のPCで実行してください。
"""
import sys
import re
import urllib.request
import urllib.parse

try:
    import feedparser
except ImportError:
    feedparser = None

UA = "Mozilla/5.0 (compatible; kensho-feedfinder/1.0)"
COMMON_PATHS = ["/rss", "/rss.xml", "/feed", "/feed/", "/index.rdf",
                "/rss/", "/atom.xml", "/feed.xml", "/rdf"]


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def find_in_html(base_url, html):
    """HTMLの<link>からRSS/Atomフィードを抽出。"""
    found = []
    # <link ... type="application/rss+xml" ... href="...">（属性順は不定）
    for m in re.finditer(r"<link\b[^>]*>", html, re.IGNORECASE):
        tag = m.group(0)
        if re.search(r'type=["\'](application/(rss\+xml|atom\+xml|rdf\+xml))["\']', tag, re.I):
            href = re.search(r'href=["\']([^"\']+)["\']', tag, re.I)
            if href:
                found.append(urllib.parse.urljoin(base_url, href.group(1)))
    return found


def validate(url):
    """URLが実際にRSS/Atomとして読めるか検証。エントリ数を返す。"""
    if feedparser is None:
        return None
    try:
        d = feedparser.parse(url)
        if d.entries:
            return len(d.entries)
    except Exception:
        pass
    return 0


def discover(site):
    print(f"\n=== {site} ===")
    candidates = []
    # 1) HTML内のlink
    try:
        html = fetch(site)
        candidates += find_in_html(site, html)
    except Exception as e:
        print(f"  トップページ取得失敗: {e}")
    # 2) よくあるパス
    for p in COMMON_PATHS:
        candidates.append(urllib.parse.urljoin(site, p))
    # 重複除去
    seen, uniq = set(), []
    for c in candidates:
        if c not in seen:
            seen.add(c); uniq.append(c)

    valid = []
    for c in uniq:
        n = validate(c)
        if n:
            print(f"  ✅ 有効 ({n}件): {c}")
            valid.append(c)
    if not valid:
        print("  ⚠ 有効なRSSフィードが見つかりませんでした。")
        print("    → サイトに『RSS』リンクがないか手動で確認するか、メルマガ購読を検討。")
    return valid


def main():
    # Windows(cp932)等でリダイレクト時に絵文字が書けずに落ちるのを防ぐ
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    if feedparser is None:
        print("feedparser未インストール: pip install feedparser", file=sys.stderr)
        sys.exit(1)

    all_valid = []
    for site in sys.argv[1:]:
        all_valid += [(site, u) for u in discover(site)]

    if all_valid:
        print("\n\n===== config.yaml に貼れる形式 =====\n")
        print("feeds:")
        for site, url in all_valid:
            name = urllib.parse.urlparse(site).netloc
            print(f"  - name: {name}")
            print(f"    url: {url}")


if __name__ == "__main__":
    main()
