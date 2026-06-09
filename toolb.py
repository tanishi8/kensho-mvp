"""
ツールB（半自動）CLI（設計書 6章）。
収集した懸賞をスコア順に提示し、コメント案を表示。
応募したものを人間が記録し、当選/落選も記録。応募ログDBに蓄積。

使い方:
  python toolb.py list   [--sample sample_feed.xml] [--top 10]   優先リスト＋コメント案
  python toolb.py apply  <id>                                    応募済みに記録
  python toolb.py won    <id>                                    当選に記録
  python toolb.py lost   <id>                                    落選に記録
  python toolb.py stats                                          ステータス集計・当選率
"""
import argparse
import sys
import yaml

import extract
import llm_extract
import score
import applog
import comment

try:
    import feedparser
except ImportError:
    feedparser = None


def load_cfg(path="config.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def collect_and_score(cfg, sample=None):
    items = []
    if sample:
        d = feedparser.parse(sample)
        feeds = [(sample, d)]
    else:
        feeds = [(f["url"], feedparser.parse(f["url"])) for f in cfg["feeds"]]
    for src, d in feeds:
        for e in d.entries:
            raw = {"title": e.get("title", "").strip(),
                   "summary": e.get("summary", "") or e.get("description", ""),
                   "link": e.get("link", ""), "source": d.feed.get("title", src)}
            kf = cfg.get("keyword_filter", {})
            if kf.get("enabled") and not extract.is_sweepstakes(
                    raw["title"], raw["summary"], kf.get("any_of", [])):
                continue
            info = extract.extract(raw["title"], raw["summary"])
            info = llm_extract.enrich(info, cfg, summary=raw["summary"])
            info["link"] = raw["link"]
            info["source"] = raw["source"]
            items.append(score.score(info, cfg))
    items.sort(key=lambda x: x.get(cfg.get("rank_by","score"), 0), reverse=True)
    return items


def cmd_list(args, cfg):
    items = collect_and_score(cfg, args.sample)
    shown = 0
    for it in items:
        rid, _ = applog.upsert_candidate(it)  # 候補として登録
        if shown >= args.top:
            continue
        shown += 1
        wc = f"{it['win_count']:,}名" if it["win_count"] else "本数不明"
        tags = []
        if it["manual_lottery"]:
            tags.append("手動抽選")
        if it["local"]:
            tags.append("地域限定")
        print(f"\n[{rid}] roi={it.get('roi',0):.3f} score={it['score']:.3f} cost={it.get('cost','?')}円  {it['method']}/{it['genre']}/{wc}"
              f"{'  ['+'/'.join(tags)+']' if tags else ''}")
        print(f"  {it['title']}")
        print(f"  {it.get('link','')}")
        print(f"  💡 {comment.advice(it)}")
        for j, c in enumerate(comment.generate(it, n=2, seed=hash(rid) % 9999), 1):
            print(f"  コメント案{j}: {c}")
    print(f"\n（候補{len(items)}件を応募ログに登録。応募したら python toolb.py apply <id>）")


def cmd_status(args, cfg, status):
    rec = applog.mark(args.id, status)
    print(f"[{args.id}] → {status}: {rec['title'][:50]}")


def cmd_stats(args, cfg):
    s = applog.summary()
    print("=== 応募ログ集計 ===")
    print(f"候補:{s['candidate']}  応募済:{s['applied']}  当選:{s['won']}  "
          f"落選:{s['lost']}  無効:{s['invalid']}  合計:{s['total']}")
    if s["win_rate"] is not None:
        print(f"応募ベース当選率: {s['win_rate']*100:.1f}%（{s['won']}/{s['applied_total']}）")
    else:
        print("まだ応募記録がありません。")


def main():
    ap = argparse.ArgumentParser(description="ツールB（半自動）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("--sample"); p.add_argument("--top", type=int, default=10)
    for name in ("apply", "won", "lost", "invalid"):
        q = sub.add_parser(name); q.add_argument("id")
    sub.add_parser("stats")
    args = ap.parse_args()
    cfg = load_cfg()

    if feedparser is None and args.cmd == "list":
        print("feedparser 未インストール: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    if args.cmd == "list":
        cmd_list(args, cfg)
    elif args.cmd == "apply":
        cmd_status(args, cfg, "applied")
    elif args.cmd == "won":
        cmd_status(args, cfg, "won")
    elif args.cmd == "lost":
        cmd_status(args, cfg, "lost")
    elif args.cmd == "invalid":
        cmd_status(args, cfg, "invalid")
    elif args.cmd == "stats":
        cmd_stats(args, cfg)


if __name__ == "__main__":
    main()
