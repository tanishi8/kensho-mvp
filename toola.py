"""
ツールA（ほぼ完全自動）CLI（設計書 5章）。
収集した候補のうち「自動応募してよいもの」だけをガードレールで選び、
メール/フォームで応募する。既定は dry-run（実送信しない）。

使い方:
  python toola.py plan  [--sample sample_feed.xml]            応募可否を一覧（auto/escalate/skip）
  python toola.py run   [--sample ...] [--live] [--max N]     自動応募（--liveで実送信）
  python toola.py escalations                                 人間対応が必要な懸賞一覧

安全方針（レビュー反映）:
  - --live を付けない限り実送信しない（dry-run）
  - gate.decide が auto のものだけ応募。CAPTCHA/規約NG/未対応はescalate
  - 重複応募しない: applog が applied/won/lost/invalid の懸賞は再応募しない
  - resolve() でまとめ記事URL→本応募URLを特定してからフォームを開く
  - --max で1回の応募数に上限（暴走防止・既定10）
  - メール方式は宛先が確実に取れないため escalate（誤送信防止）
  - 応募できたものは applog に記録し、結果を Discord に報告
"""
import argparse
import sys
import yaml

import extract
import llm_extract
import feedutil
import score
import gate
import applog
import resolve
import notify
import profile as profile_mod
import apply_email
import apply_form

try:
    import feedparser
except ImportError:
    feedparser = None

# 「応募済み扱い」で再応募しないステータス（invalid も含めて再送しない）
DONE_STATUSES = {"applied", "won", "lost", "invalid"}


def load_cfg(path="config.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def collect(cfg, sample=None, use_llm=True):
    items = []
    feeds = [(sample, feedutil.parse(sample))] if sample else \
            [(f["url"], feedutil.parse(f["url"])) for f in cfg["feeds"]]
    kf = cfg.get("keyword_filter", {})
    for src, d in feeds:
        for e in d.entries:
            _t = e.get("title", ""); _s = e.get("summary", "") or e.get("description", "")
            if kf.get("enabled") and not extract.is_sweepstakes(
                    _t, _s, kf.get("any_of", []), kf.get("none_of")):
                continue
            info = extract.extract(_t, _s)
            if use_llm:
                info = llm_extract.enrich(info, cfg, summary=e.get("summary", ""))
            info["link"] = e.get("link", "")
            info["source"] = d.feed.get("title", src)
            items.append(score.score(info, cfg))
    items.sort(key=lambda x: x.get(cfg.get("rank_by", "score"), 0), reverse=True)
    return items


def already_applied(rid):
    for r in applog.all_records():
        if r.get("id") == rid and r.get("status") in DONE_STATUSES:
            return True
    return False


def cmd_plan(args, cfg):
    # 毎朝のスケジュール用。正規表現のみで十分（LLM消費を避ける）
    items = collect(cfg, args.sample, use_llm=False)
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
    max_apply = args.max
    try:
        prof = profile_mod.load()
    except FileNotFoundError as e:
        print(f"⚠ {e}", file=sys.stderr)
        print("  profile.sample.json を profile.json にコピーして自分の情報に編集してください。")
        if not dry:
            sys.exit(1)
        prof = {}

    items = collect(cfg, args.sample, use_llm=True)
    applied_items, attempted_items = [], []
    skipped_dupe = 0
    n_attempt = 0

    for it in items:
        # 上限: live は応募成功数、dry-run は試行数で頭打ち（H）
        done = len(applied_items) if not dry else n_attempt
        if done >= max_apply:
            print(f"\n[上限] --max {max_apply} に達したため停止。")
            break

        d = gate.decide(it)
        if d["action"] != "auto":
            continue

        rid, _ = applog.upsert_candidate(it)
        if already_applied(rid):
            skipped_dupe += 1
            continue

        method = it["method"]
        print(f"\n▶ {it['title'][:46]}  [{method}]")

        if method == "メール":
            print("  ⏭ メール方式は宛先特定不可のため escalate（人間が応募）。")
            continue

        # 1サイトの障害で全体が止まらないよう per-item で try/except（A）
        try:
            real_url = resolve.resolve(it.get("link", "")) or it.get("link", "")
            res = apply_form.apply(it, prof, page_url=real_url, dry_run=dry, submit=args.live)
        except Exception as e:
            print(f"  ⚠ エラーによりスキップ: {type(e).__name__}: {e}")
            continue

        n_attempt += 1
        print(f"  フォーム[{res.get('action')}]: {res.get('reason','')}")
        if res.get("unknown"):
            print(f"  未対応項目: {res['unknown']}")
        if res.get("filled"):
            print(f"  入力予定: {list(res['filled'].keys())}")

        if not dry:
            if res.get("submitted"):
                applog.mark(rid, "applied")
                applied_items.append(it)
            elif res.get("attempted"):
                # 送信は押したが完了未確認 → attempted 記録（自動再送しない・人間確認）
                applog.mark(rid, "attempted", note=res.get("reason", ""))
                attempted_items.append(it)

    mode = "実送信" if args.live else "dry-run（未送信）"
    print(f"\n完了（{mode}）。応募成功 {len(applied_items)} / 結果不明 {len(attempted_items)} / "
          f"試行 {n_attempt} / 重複スキップ {skipped_dupe}")
    if dry:
        print("実際に送信するには --live を付けて実行してください（規約・内容を確認のうえ）。")

    # Discord 報告（実送信時。成功と「要確認(結果不明)」を分けて通知）
    if not dry and (applied_items or attempted_items):
        try:
            payload = []
            for i in applied_items:
                payload.append({"title": "✅応募:" + i["title"][:42], "method": i["method"],
                                "genre": i.get("genre", ""), "win_count": i.get("win_count"),
                                "score": i.get("roi"), "link": i.get("link", ""),
                                "manual_lottery": False, "local": i.get("local", False),
                                "preference_hit": i.get("preference_hit", False)})
            for i in attempted_items:
                payload.append({"title": "⚠要確認(結果不明):" + i["title"][:36], "method": i["method"],
                                "genre": i.get("genre", ""), "win_count": i.get("win_count"),
                                "score": i.get("roi"), "link": i.get("link", ""),
                                "manual_lottery": False, "local": i.get("local", False),
                                "preference_hit": i.get("preference_hit", False)})
            notify.send(payload, top_n=len(payload))
        except Exception as e:
            print(f"  (Discord報告失敗: {type(e).__name__})")


def cmd_escalations(args, cfg):
    items = collect(cfg, args.sample, use_llm=False)
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
    p2 = sub.add_parser("run"); p2.add_argument("--sample")
    p2.add_argument("--live", action="store_true"); p2.add_argument("--max", type=int, default=10)
    p3 = sub.add_parser("escalations"); p3.add_argument("--sample")
    args = ap.parse_args()
    cfg = load_cfg()
    if feedparser is None:
        print("feedparser未インストール: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)
    {"plan": cmd_plan, "run": cmd_run, "escalations": cmd_escalations}[args.cmd](args, cfg)


if __name__ == "__main__":
    main()
