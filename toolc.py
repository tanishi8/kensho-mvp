"""
当選抽出パイプライン CLI（設計書 5.5）。フェーズ3。
受信した当選通知を詐欺判定にかけ、本物（genuine）だけを Discord に出力する。
review は人間確認用に別途表示、reject は捨てる。

使い方:
  python toolc.py run    [--sample notices_sample.json]   受信→判定→本物のみ通知
  python toolc.py test   --sample notices_sample.json     判定結果を全件表示（通知しない）

入力:
  本番は IMAP（inbox.fetch_unread）。テストは --sample のJSON（notice辞書のリスト）。
ホワイトリスト: whitelist.json（任意）＋ 応募ログ(applog.json)の公式情報を自動利用。
"""
import argparse
import json
import os
import sys

import fraud_check
import applog
import notify
import inbox


def load_whitelist(path="whitelist.json"):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def get_notices(sample):
    if sample:
        with open(sample, encoding="utf-8") as f:
            return json.load(f)
    return inbox.fetch_unread()


def run(sample=None, notify_genuine=True):
    records = applog.all_records()
    wl = load_whitelist()
    notices = get_notices(sample)

    genuine, review, reject = [], [], []
    for n in notices:
        r = fraud_check.check(n, records, wl)
        n["_verdict"] = r
        {"genuine": genuine, "review": review, "reject": reject}[r["verdict"]].append(n)

    print(f"受信 {len(notices)} 件 → 本物 {len(genuine)} / 要確認 {len(review)} / 除外 {len(reject)}")

    # 本物を Discord 出力
    if genuine and notify_genuine:
        items = []
        for n in genuine:
            items.append({
                "title": "🎉当選: " + n.get("subject", "")[:50],
                "method": "", "genre": "", "win_count": None, "score": n["_verdict"]["score"],
                "link": n.get("sender_id", ""), "manual_lottery": False, "local": False,
            })
        notify.send(items, top_n=len(items))

    return {"genuine": genuine, "review": review, "reject": reject}


def show(sample):
    records = applog.all_records()
    wl = load_whitelist()
    notices = get_notices(sample)
    for n in notices:
        r = fraud_check.check(n, records, wl)
        icon = {"genuine": "🟢本物", "review": "🟡要確認", "reject": "🔴除外"}[r["verdict"]]
        print(f"\n{icon} (score={r['score']}) {n.get('subject','')[:46]}")
        print(f"  from: {n.get('sender_id','')}  ch:{n.get('channel','')}")
        for reason in r["reasons"]:
            print(f"   - {reason}")


def reminders(within_days=3, notify_flag=True):
    """受取期限が迫った当選をDiscord通知（失効防止）。"""
    due = applog.due_reminders(within_days)
    if not due:
        print(f"受取期限{within_days}日以内の当選はありません。")
        return []
    items = []
    for r in due:
        dl = r["_days_left"]
        urgency = "⚠️本日" if dl == 0 else f"あと{dl}日"
        items.append({
            "title": f"⏰受取期限{urgency}: " + r.get("title", "")[:44],
            "method": "", "genre": "", "win_count": None,
            "score": "", "link": r.get("link", ""),
            "manual_lottery": False, "local": False,
        })
        print(f"  {urgency} | {r.get('title','')[:40]} | 期限 {r.get('receive_deadline')}")
    if notify_flag:
        notify.send(items, top_n=len(items))
        for r in due:
            applog.mark_reminded(r["id"])
    return due


def main():
    ap = argparse.ArgumentParser(description="当選抽出（フェーズ3）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("run"); p1.add_argument("--sample")
    p2 = sub.add_parser("test"); p2.add_argument("--sample", required=True)
    p3 = sub.add_parser("remind"); p3.add_argument("--days", type=int, default=3)
    args = ap.parse_args()
    if args.cmd == "run":
        run(args.sample)
    elif args.cmd == "remind":
        reminders(args.days)
    else:
        show(args.sample)


if __name__ == "__main__":
    main()
