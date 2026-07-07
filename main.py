"""
懸賞MVP（フェーズ0）エントリポイント。
収集(RSS) → 抽出(正規表現＋LLM) → スコアリング → 重複除去 → Discord通知。
--export を付けると、同じ収集結果からアプリ用 docs/app_feed.json も出力する
（収集・LLM補完を1回で済ませ、通知とアプリ出力の二重実行を避ける）。
"""
import argparse
import json
import os
import sys

import yaml

import extract
import llm_extract
import feedutil
import score
import notify

try:
    import feedparser
except ImportError:
    feedparser = None


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_seen(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(path, seen):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False)


def collect(feeds):
    """RSSフィードから (title, summary, link) を集める。"""
    if feedparser is None:
        raise RuntimeError("feedparser 未インストール: pip install feedparser")
    items = []
    for feed in feeds:
        d = feedutil.parse(feed["url"])
        for e in d.entries:
            items.append({
                "title": e.get("title", "").strip(),
                "summary": e.get("summary", "") or e.get("description", ""),
                "link": e.get("link", ""),
                "source": feed["name"],
            })
    return items


def run(cfg, items=None, dry_run=False, summary_mode=False):
    if items is None:
        items = collect(cfg["feeds"])

    seen_path = cfg.get("seen_db", "seen.json")
    seen = set() if dry_run else load_seen(seen_path)

    results, new_seen = [], set()
    for raw in items:
        key = raw.get("link") or raw.get("title")
        if not key or key in seen:
            continue
        new_seen.add(key)
        kf = cfg.get("keyword_filter", {})
        # none_of（除外語：当選番号/結果発表/まとめ/終了しました 等）も渡してノイズを弾く
        if kf.get("enabled") and not extract.is_sweepstakes(
                raw["title"], raw.get("summary", ""),
                kf.get("any_of", []), kf.get("none_of")):
            continue
        info = extract.extract(raw["title"], raw.get("summary", ""))
        info = llm_extract.enrich(info, cfg, summary=raw.get("summary", ""))
        info["link"] = raw.get("link", "")
        info["source"] = raw.get("source", "")
        results.append(score.score(info, cfg))

    rank_key = cfg.get("rank_by", "score")
    results.sort(key=lambda x: x.get(rank_key, 0), reverse=True)

    if summary_mode:
        notify.send_summary(results, cfg.get("summary_top_n", 5))
    else:
        notify.send(results, cfg.get("notify_top_n", 15))

    if not dry_run and new_seen:
        save_seen(seen_path, seen | new_seen)
    return results


def main():
    ap = argparse.ArgumentParser(description="懸賞MVP フェーズ0")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--dry-run", action="store_true",
                    help="seen.jsonを更新せず実行（テスト用）")
    ap.add_argument("--sample", help="サンプルJSON（RSSの代わり）でテスト")
    ap.add_argument("--summary", action="store_true", help="デイリーサマリー形式で通知")
    ap.add_argument("--export", action="store_true",
                    help="同じ収集結果からアプリ用 docs/app_feed.json も出力")
    ap.add_argument("--export-out", default="docs/app_feed.json")
    ap.add_argument("--export-top", type=int, default=80)
    args = ap.parse_args()

    cfg = load_config(args.config)
    items = None
    if args.sample:
        with open(args.sample, encoding="utf-8") as f:
            items = json.load(f)
    try:
        results = run(cfg, items=items, dry_run=args.dry_run, summary_mode=args.summary)
        if args.export:
            import app_export
            feed = app_export.feed_from_results(results, cfg, top=args.export_top)
            os.makedirs(os.path.dirname(args.export_out) or ".", exist_ok=True)
            with open(args.export_out, "w", encoding="utf-8") as f:
                json.dump(feed, f, ensure_ascii=False, indent=2)
            print(f"アプリ用JSON: {args.export_out}（{feed['count']}件）")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
