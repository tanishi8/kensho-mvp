"""
まとめ記事から「本当の応募ページ(主催者公式)URL」を抽出する。
- Googleアラートの転送URL(google.com/url?...&url=REAL)を実URLに展開
- まとめサイトの記事HTMLを取得し、応募ページへの外部リンクを推定して返す
失敗時は元のURLをそのまま返す（安全フォールバック）。
"""
import re
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 kensho-mvp/1.0")

# 記事を掘って本URLを探す対象（まとめサイトのドメイン）
DIG_DOMAINS = [
    "kensho-news.com", "kensho-everyday.com", "tokaikensyo.com", "kenshou.club",
    "camnavi.net", "otokuchin.com", "chancekensyou.com", "setsuyaku-blog.com",
]
# 応募リンクとして除外するドメイン（広告/アフィリエイト/SNS/集約自身）
BAD_DOMAINS = [
    "a8.net", "px.a8.net", "rakuten.co.jp/rd", "hb.afl.rakuten", "amazon.co.jp/gp",
    "amzn.to", "doubleclick", "googleadservices", "googlesyndication", "google.com/aclk",
    "twitter.com", "x.com", "instagram.com", "facebook.com", "line.me", "youtube.com",
    "pinterest", "hatena", "feedly", "/tag/", "/category/", "/author/",
]
# 応募ページらしさを示す語（アンカーテキスト/href）
GOOD_HINTS = ["応募", "公式", "キャンペーン", "エントリー", "申し込", "詳細はこちら",
              "campaign", "entry", "present", "cp", "apply"]

_cache = {}


def _domain(url):
    try:
        return urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return ""


def unwrap_redirect(url):
    """google.com/url?...&url=REAL / &q=REAL を実URLに展開。"""
    if not url:
        return url
    try:
        pr = urllib.parse.urlparse(url)
        if "google.com" in pr.netloc and pr.path in ("/url", "/aclk"):
            qs = urllib.parse.parse_qs(pr.query)
            for k in ("url", "q", "u"):
                if k in qs and qs[k]:
                    return qs[k][0]
    except Exception:
        pass
    return url


def _fetch(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        enc = r.headers.get_content_charset() or "utf-8"
        return raw.decode(enc, errors="replace")


def _best_link(article_url, html):
    """記事HTMLから主催者応募ページらしき外部リンクを推定。"""
    base_dom = _domain(article_url)
    best, best_score = None, -1
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        href = urllib.parse.urljoin(article_url, m.group(1))
        href = unwrap_redirect(href)
        text = re.sub(r"<[^>]+>", "", m.group(2))
        dom = _domain(href)
        if not dom or dom == base_dom:
            continue
        low = (href + " " + text).lower()
        if any(b in low for b in BAD_DOMAINS):
            continue
        if not href.startswith("http"):
            continue
        score = 0
        if any(g in low for g in GOOD_HINTS):
            score += 3
        if dom.endswith(".lg.jp") or dom.endswith(".go.jp"):
            score += 3
        elif dom.endswith(".co.jp") or dom.endswith(".jp"):
            score += 1
        if score > best_score:
            best, best_score = href, score
    # スコアが低すぎる(応募らしさゼロ)なら採用しない
    return best if best_score >= 1 else None


def resolve(url, dig=True):
    """記事URL → 本応募URL（推定）。失敗時は元URLを返す。"""
    if not url:
        return url
    if url in _cache:
        return _cache[url]
    real = unwrap_redirect(url)
    out = real
    try:
        if dig and _domain(real) in DIG_DOMAINS:
            html = _fetch(real)
            cand = _best_link(real, html)
            if cand:
                out = cand
    except Exception:
        out = real
    _cache[url] = out
    return out
