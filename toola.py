"""
ツールA（ほぼ完全自動）CLI（設計書 5章）。
収集した候補のうち「自動応募してよいもの」だけをガードレールで選び、
メール/フォームで応募する。既定は dry-run（実送信しない）。

使い方:
  python toola.py plan  [--sample sample_feed.xml]      応募可否を一覧（auto/escalate/skip）
  python toola.py run   [--sample sample_feed.xml] [--live]   自動応募（--liveで実送信）
  python toola.py escalations                            人間対応が必要な懸賞一覧

安全方針:
  - --live を付けない限り実送信しない（dry-run）
  - gate.decide が auto のものだけ応募。CAPTCHA/規約NG/未対応はescalate
  - 応募したら applog にstatus=appliedで記録
"""
import argparse
import sys
import yaml

import extract
import llm_extract
import score
import gate
import applog
import profile as profile_mod
import apply_email
import apply_form

try:
    import feedparser
except ImportError:
    feedparser = None


def load_cfg(path="config.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def collect(cfg, sample=None):
    items = []
    feeds = [(sample, feedparser.parse(sample))] if sample else \
            [(f["url"], feedparser.parse(f["url"])) for f in cfg["feeds"]]
    for src, d in feeds:
        for e in d.entries:
            _t = e.get("title", ""); _s = e.get("summary", "") or e.get("description", "")
            kf = cfg.get("keyword_filter", {})
            if kf.get("enabled") and not extract.is_sweepstakes(_t, _s, kf.get("any_of", [])):
                continue
            info = extract.extract(_t, _s)
            info = llm_extract.enrich(info, cfg, summary=e.get("summary", ""))
            info["link"] = e.get("link", "")
            info["source"] = d.feed.get("title", src)
            items.append(score.score(info, cfg))
    items.sort(key=lambda x: x.get(cfg.get("rank_by","score"), 0), reverse=True)
    return items


def cmd_plan(args, cfg):
    items = collect(cfg, args.sample)
    counts = {"auto": 0, "escalate": 0, "skip": 0}
    for it in items:
        d = gate.decide(it)
        counts[d["action"]] += 1
        icon = {"auto": "🟢", "escalate": "🟡", "skip": "⚪"}[d["action"]]
        print(f"{icon} {d['action']:8} | {it['method']:6} | {it['title'][:42]}")
        print(f"          {d['reason']}")
    print(f"\n集計: 自動応募可 {counts['auto']} / 人間対応 {counts['escalate']} / 対象外 {counts['skip']}")


def cmd_run(args, cfg):
    dry = not args.live
    try:
        prof = profile_mod.load()
    except FileNotFoundError as e:
        print(f"⚠ {e}", file=sys.stderr)
        print("  profile.sample.json を profile.json にコピーして自分の情報に編集してください。")
        if not dry:
            sys.exit(1)
        prof = {}

    items = collect(cfg, args.sample)
    applied = 0
    for it in items:
        d = gate.decide(it)
        if d["action"] != "auto":
            continue
        rid, _ = applog.upsert_candidate(it)
        method = it["method"]
        print(f"\n▶ {it['title'][:46]}  [{method}]")
        if method in ("メール",):
            tmpl = "{last_name}{first_name}と申します。本キャンペーンに応募します。\n" \
                   "〒{zip} {pref}{city}{address1}{address2}\nTEL: {tel}\nMail: {email}"
            res = apply_email.send(it.get("link", ""), f"応募: {it['title'][:30]}",
                                   tmpl, prof, dry_run=dry)
            print(f"  メール {'送信' if res.get('sent') else 'dry-run'}: {res.get('note','')}")
        else:  # ネット/即時当選/アンケート → フォーム
            res = apply_form.apply(it, prof, dry_run=dry, submit=args.live)
            print(f"  フォーム[{res.get('action')}]: {res.get('reason','')}")
            if res.get("unknown"):
                print(f"  未対応項目: {res['unknown']}")
            if res.get("filled"):
                print(f"  入力予定: {list(res['filled'].keys())}")

        if not dry and (res.get("sent") or res.get("submitted")):
            applog.mark(rid, "applied")
            applied += 1
    mode = "実送信" if args.live else "dry-run（未送信）"
    print(f"\n完了（{mode}）。応募記録: {applied}件")
    if dry:
        print("実際に送信するには --live を付けて実行してください（規約・内容を確認のうえ）。")


def cmd_escalations(args, cfg):
    items = collect(cfg, args.sample)
    n = 0
    for it in items:
        d = gate.decide(it)
        if d["action"] == "escalate":
            n += 1
            print(f"🟡 {it['title'][:46]}\n   {d['reason']}\n   {it.get('link','')}")
    print(f"\n人間対応が必要: {n}件")


def main():
    ap = argparse.ArgumentParser(description="ツールA（ほぼ完全自動）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("plan"); p1.add_argument("--sample")
    p2 = sub.add_parser("run"); p2.add_argument("--sample"); p2.add_argument("--live", action="store_true")
    p3 = sub.add_parser("escalations"); p3.add_argument("--sample")
    args = ap.parse_args()
    cfg = load_cfg()
    if feedparser is None:
        print("feedparser未インストール: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)
    {"plan": cmd_plan, "run": cmd_run, "escalations": cmd_escalations}[args.cmd](args, cfg)


if __name__ == "__main__":
    main()
