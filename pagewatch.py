"""
指定URLの直接監視（観光協会・自治体・地方メディアのキャンペーンページを発信源で監視）。
まとめサイト(集約後)ではなく発信源を直接見るため、競争が生まれる前の低競争案件を捕まえやすい。

watchlist.yaml の pages: に監視URLを登録 → 各ページのHTMLからリンク+テキストを抽出 →
懸賞らしいもの(応募/プレゼント/キャンペーン 等を含み、ノイズ語を含まない)を新着検出 →
スコア → Discord通知。重複は pagewatch_seen.json で防止。

使い方:
  python pagewatch.py            # 監視ページを巡回→新着懸賞をDiscord通知
  python pagewatch.py --dry-run

注意: robots.txt/利用規約を尊重し、監視対象は自分が確認した少数の発信源に限定。
       低頻度(1日1回)で、タイトル/リンクのみ取得する軽量監視。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request

import yaml
import extract
import score
import notify

SEEN = "pagewatch_seen.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 kensho-mvp-pagewatch/1.0")


def load_cfg(path="config.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_pages(path="watchlist.yaml"):
    if not os.path.exists(path):
        return []
    return (yaml.safe_load(open(path, encoding="utf-8")) or {}).get("pages", [])


def _seen():
    return set(json.load(open(SEEN, encoding="utf-8"))) if os.path.exists(SEEN) else set()


def _save_seen(s):
    json.dump(sorted(s), open(SEEN, "w", encoding="utf-8"), ensure_ascii=False)


def fetch_html(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        enc = r.headers.get_content_charset() or "utf-8"
        return raw.decode(enc, errors="replace")


def extract_links(base_url, html):
    """<a href>のリンクとアンカーテキストを (text, abs_url) で返す。"""
    out = []
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        href = m.group(1)
        text = re.sub(r"<[^>]+>", "", m.group(2))  # タグ除去
        text = re.sub(r"\s+", " ", text).strip()
        if not text or len(text) < 6:
            continue
        out.append((text, urllib.parse.urljoin(base_url, href)))
    return out


def run(cfg, dry_run=False):
    kf = cfg.get("keyword_filter", {})
    any_of = kf.get("any_of", ["応募", "プレゼント", "キャンペーン", "懸賞", "抽選"])
    none_of = kf.get("none_of")
    pages = load_pages()
    if not pages:
        print("watchlist.yaml に pages: が未設定です。監視URLを登録してください。")
        return []

    seen = set() if dry_run else _seen()
    results, new_seen = [], set()

    for p in pages:
        url = p.get("url"); name = p.get("name", url)
        if not url:
            continue
        try:
            html = fetch_html(url)
        except Exception as e:
            print(f"  [警告] {name}: 取得失敗 {type(e).__name__}。スキップ")
            continue
        for text, link in extract_links(url, html):
            if not extract.is_sweepstakes(text, "", any_of, none_of):
                continue
            key = hashlib.sha1(link.encode("utf-8")).hexdigest()[:12]
            if key in seen:
                continue
            new_seen.add(key)
            info = extract.extract(text, "")
            info["link"] = link
            info["source"] = "監視:" + name
            results.append(score.score(info, cfg))

    rank = cfg.get("rank_by", "roi")
    results.sort(key=lambda x: x.get(rank, 0), reverse=True)

    if results:
        items = [{"title": "👁" + r["title"][:46], "method": r["method"], "genre": r["genre"],
                  "win_count": r.get("win_count"), "score": r.get("roi"), "link": r.get("link", ""),
                  "manual_lottery": r.get("manual_lottery", False), "local": r.get("local", False),
                  "preference_hit": r.get("preference_hit", False)} for r in results]
        notify.send(items, top_n=cfg.get("notify_top_n", 15))
    else:
        print("監視ページに新着懸賞はありません。")

    if not dry_run and new_seen:
        _save_seen(seen | new_seen)
    return results


def main():
    ap = argparse.ArgumentParser(description="指定URL/地方メディアの直接監視")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    try:
        run(load_cfg(), dry_run=args.dry_run)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    main()
