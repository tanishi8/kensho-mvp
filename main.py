"""
懸賞MVP（フェーズ0）エントリポイント。
収集(RSS) → 抽出(正規表現＋LLM) → スコアリング → 重複除去 → Discord通知。

--export を付けると、同じ収集結果からアプリ用 docs/app_feed.json も出力する。
  通知(summary)は「その日の新着」だけ、アプリJSONは「開催中の全件」を出す
  （seen除外はスコアリングの後に行うため、アプリから既知の開催中懸賞が消えない）。
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
    """収集→抽出→スコアリングを全件に対して行い、通知は新着のみ。
    戻り値は「開催中の全件（スコア済み・ソート済み）」＝アプリ出力用。"""
    if items is None:
        items = collect(cfg["feeds"])

    seen_path = cfg.get("seen_db", "seen.json")
    seen = set() if dry_run else load_seen(seen_path)

    all_results, new_results, new_seen = [], [], set()
    kf = cfg.get("keyword_filter", {})
    for raw in items:
        key = raw.get("link") or raw.get("title")
        if not key:
            continue
        if kf.get("enabled") and not extract.is_sweepstakes(
                raw["title"], raw.get("summary", ""),
                kf.get("any_of", []), kf.get("none_of")):
            continue
        info = extract.extract(raw["title"], raw.get("summary", ""))
        info = llm_extract.enrich(info, cfg, summary=raw.get("summary", ""))
        info["link"] = raw.get("link", "")
        info["source"] = raw.get("source", "")
        scored = score.score(info, cfg)
        all_results.append(scored)
        if key not in seen:
            new_results.append(scored)
            new_seen.add(key)

    rank_key = cfg.get("rank_by", "score")
    all_results.sort(key=lambda x: x.get(rank_key, 0), reverse=True)
    new_results.sort(key=lambda x: x.get(rank_key, 0), reverse=True)

    # 通知は新着のみ（新着が無い日は通知しない）
    if new_results:
        if summary_mode:
            notify.send_summary(new_results, cfg.get("summary_top_n", 5))
        else:
            notify.send(new_results, cfg.get("notify_top_n", 15))
    else:
        print("新着なし（通知はスキップ）")

    if not dry_run and new_seen:
        save_seen(seen_path, seen | new_seen)
    return all_results


def main():
    ap = argparse.ArgumentParser(description="懸賞MVP フェーズ0")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--dry-run", action="store_true", help="seen.jsonを更新せず実行（テスト用）")
    ap.add_argument("--sample", help="サンプルJSON（RSSの代わり）でテスト")
    ap.add_argument("--summary", action="store_true", help="デイリーサマリー形式で通知")
    ap.add_argument("--export", action="store_true",
                    help="開催中の全件からアプリ用 docs/app_feed.json も出力")
    ap.add_argument("--export-out", default="docs/app_feed.json")
    ap.add_argument("--export-top", type=int, default=80)
    args = ap.parse_args()

    cfg = load_config(args.config)
    items = None
    if args.sample:
        with open(args.sample, encoding="utf-8") as f:
            items = json.load(f)
    try:
        all_results = run(cfg, items=items, dry_run=args.dry_run, summary_mode=args.summary)
        if args.export:
            import app_export
            feed = app_export.feed_from_results(all_results, cfg, top=args.export_top)
            os.makedirs(os.path.dirname(args.export_out) or ".", exist_ok=True)
            with open(args.export_out, "w", encoding="utf-8") as f:
                json.dump(feed, f, ensure_ascii=False, indent=2)
            print(f"アプリ用JSON: {args.export_out}（開催中 {feed['count']}件）")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
