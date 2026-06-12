"""
メルマガ/LINE経由のキャンペーン収集（低競争の自治体・観光懸賞をプッシュで取得）。
懸賞専用Gmailで観光協会・自治体・酒蔵等のメルマガを購読しておくと、
彼らのキャンペーンが直接届く（検索インデックスを経由しないため穴場に強い）。

仕組み: IMAPで未読メールを取得 → 応募機会(キャンペーン)だけ抽出 → スコア → Discord通知。
当選通知の詐欺判定(toolc)とは別系統。重複通知は campaign_seen.json で防止。

使い方:
  python mailcampaign.py            # 受信→キャンペーン抽出→Discord通知
  python mailcampaign.py --sample notices_sample.json   # テスト

環境変数: IMAP_HOST / IMAP_USER / IMAP_PASS（Gmailアプリパスワード）
"""
import argparse
import hashlib
import json
import os
import sys

import yaml
import extract
import score
import notify
import inbox

SEEN = "campaign_seen.json"


def load_cfg(path="config.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _seen():
    if os.path.exists(SEEN):
        return set(json.load(open(SEEN, encoding="utf-8")))
    return set()


def _save_seen(s):
    json.dump(sorted(s), open(SEEN, "w", encoding="utf-8"), ensure_ascii=False)


def get_notices(sample):
    if sample:
        return json.load(open(sample, encoding="utf-8"))
    return inbox.fetch_unread(mark_seen=False)


def run(cfg, sample=None, dry_run=False):
    kf = cfg.get("keyword_filter", {})
    notices = get_notices(sample)
    seen = set() if dry_run else _seen()
    results, new_seen = [], set()

    for n in notices:
        subj = n.get("subject", "")
        body = n.get("body", "")
        # 当選通知っぽいものは除外（こちらはキャンペーン=応募機会のみ）
        if any(w in f"{subj}" for w in ["ご当選", "当選のお知らせ", "当選しました"]):
            continue
        # 応募機会か（既定の除外語ノイズも自動で弾く）
        if not extract.is_sweepstakes(subj, body, kf.get("any_of", ["応募", "プレゼント", "キャンペーン", "懸賞", "抽選"]),
                                      kf.get("none_of")):
            continue
        key = hashlib.sha1((n.get("sender_id", "") + subj).encode("utf-8")).hexdigest()[:12]
        if key in seen:
            continue
        new_seen.add(key)
        info = extract.extract(subj, body)
        info["link"] = n.get("sender_id", "")
        info["source"] = "メルマガ:" + n.get("display_name", n.get("sender_domain", ""))
        results.append(score.score(info, cfg))

    rank = cfg.get("rank_by", "roi")
    results.sort(key=lambda x: x.get(rank, 0), reverse=True)

    if results:
        items = [{"title": "📩" + r["title"][:48], "method": r["method"], "genre": r["genre"],
                  "win_count": r.get("win_count"), "score": r.get("roi"), "link": r.get("link", ""),
                  "manual_lottery": r.get("manual_lottery", False), "local": r.get("local", False),
                  "preference_hit": r.get("preference_hit", False)} for r in results]
        notify.send(items, top_n=cfg.get("notify_top_n", 15))
    else:
        print("新着キャンペーンメールはありません。")

    if not dry_run and new_seen:
        _save_seen(seen | new_seen)
    return results


def main():
    ap = argparse.ArgumentParser(description="メルマガ経由キャンペーン収集")
    ap.add_argument("--sample")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cfg = load_cfg()
    try:
        run(cfg, sample=args.sample, dry_run=args.dry_run)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    main()
