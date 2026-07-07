"""
スマホアプリ用の JSON 出力（docs/app_feed.json）。

GitHub Actions で毎日実行し、収集→抽出→(LLM補完)→スコアリング した懸賞ランキングを
アプリが読める1本のJSONに書き出す。アプリ(Capacitor/PWA)はこのJSONを取得して表示する。

- 応募状況(applog.json)を突合して status を付与（応募済みが分かる）。
- SNS ワンタップ導線(snslink)と、コメント助言(comment)を各懸賞に添える。
- docs/ 配下に出力するので、GitHub Pages を docs/ で有効化すればそのまま配信できる。

使い方:
  python app_export.py                     # 本番フィードから生成
  python app_export.py --sample sample_feed.json  # ローカル確認
  python app_export.py --out docs/app_feed.json --top 80
"""
import argparse
import datetime
import json
import os

import yaml

import extract
import score
import comment as comment_mod
import snslink
import applog
import feedutil

try:
    import llm_extract
except Exception:
    llm_extract = None


def load_cfg(path="config.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _status_map():
    m = {}
    for r in applog.all_records():
        m[r.get("id")] = {"status": r.get("status", "candidate"),
                          "applied_at": r.get("applied_at")}
    return m


def collect(cfg, sample=None, use_llm=True):
    """収集→抽出→(LLM補完)→スコアリング。feedutil でRSS取得（本体と共通）。
    sample が .json ならローカルJSONリストで動作確認できる。"""
    items = []
    if sample and sample.endswith(".json"):
        raw = json.load(open(sample, encoding="utf-8"))
        entries = [(e.get("title", ""), e.get("summary", ""), e.get("link", ""),
                    e.get("source", "sample")) for e in raw]
    else:
        feeds = [(sample, feedutil.parse(sample))] if sample else \
                [(f["url"], feedutil.parse(f["url"])) for f in cfg["feeds"]]
        entries = []
        for src, d in feeds:
            src_title = d.feed.get("title", src) if hasattr(d, "feed") else src
            for e in getattr(d, "entries", []):
                entries.append((e.get("title", ""),
                                e.get("summary", "") or e.get("description", ""),
                                e.get("link", ""), src_title))

    kf = cfg.get("keyword_filter", {})
    for title, summary, link, src in entries:
        if kf.get("enabled") and not extract.is_sweepstakes(
                title, summary, kf.get("any_of", []), kf.get("none_of")):
            continue
        info = extract.extract(title, summary)
        if use_llm and llm_extract is not None:
            info = llm_extract.enrich(info, cfg, summary=summary)
        info["link"] = link
        info["source"] = src
        items.append(score.score(info, cfg))

    rank_by = cfg.get("rank_by", "roi")
    items.sort(key=lambda x: x.get(rank_by, 0), reverse=True)
    return items


def to_app_item(it, status_map):
    rid = applog.make_id(it)
    st = status_map.get(rid, {})
    return {
        "id": rid,
        "title": it.get("title", ""),
        "link": it.get("link", ""),
        "source": it.get("source", ""),
        "method": it.get("method", "不明"),
        "genre": it.get("genre", "その他"),
        "win_count": it.get("win_count"),
        "prize_value": it.get("prize_value"),
        "manual_lottery": bool(it.get("manual_lottery")),
        "local": bool(it.get("local")),
        "preference_hit": bool(it.get("preference_hit")),
        "score": it.get("score"),
        "roi": it.get("roi"),
        "deadline": it.get("deadline"),
        "status": st.get("status", "candidate"),
        "applied_at": st.get("applied_at"),
        "comment_advice": comment_mod.advice(it),
        "comment_suggestions": comment_mod.generate(it, n=2, seed=1),
        "sns": snslink.build(it),
    }


def load_watch():
    try:
        if os.path.exists("watchlist.yaml"):
            wl = (yaml.safe_load(open("watchlist.yaml", encoding="utf-8")) or {})
            return wl.get("watch", []) or []
    except Exception:
        pass
    return []


def build_feed(cfg, sample=None, top=80, use_llm=True):
    items = collect(cfg, sample=sample, use_llm=use_llm)
    status_map = _status_map()
    app_items = [to_app_item(it, status_map) for it in items[:top]]
    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "rank_by": cfg.get("rank_by", "roi"),
        "count": len(app_items),
        "items": app_items,
        "watch": load_watch(),
    }


def main():
    ap = argparse.ArgumentParser(description="スマホアプリ用JSONを出力")
    ap.add_argument("--sample")
    ap.add_argument("--out", default="docs/app_feed.json")
    ap.add_argument("--top", type=int, default=80)
    ap.add_argument("--llm", action="store_true", help="LLM二次抽出を強制する")
    args = ap.parse_args()

    cfg = load_cfg()
    use_llm = args.llm or bool(os.environ.get("GEMINI_API_KEY"))
    feed = build_feed(cfg, sample=args.sample, top=args.top, use_llm=use_llm)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)
    print(f"書き出し: {args.out}（{feed['count']}件, rank_by={feed['rank_by']}）")


if __name__ == "__main__":
    main()
