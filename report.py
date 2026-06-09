"""
応募ログから当選率・収支の集計CSVを出力（可視化用。Looker Studio/Excel等で読む）。
使い方:
  python report.py            # 集計サマリを表示＋report.csv出力
  python report.py --csv out.csv
"""
import argparse
import csv

import applog


def aggregate(path=applog.DEFAULT_PATH):
    recs = applog.all_records(path)
    s = applog.summary(path)

    # ジャンル別・方式別の応募/当選集計
    by_genre, by_method = {}, {}
    won_value = 0
    for r in recs:
        st = r.get("status")
        g = r.get("genre", "その他") or "その他"
        m = r.get("method", "不明") or "不明"
        by_genre.setdefault(g, {"応募": 0, "当選": 0})
        by_method.setdefault(m, {"応募": 0, "当選": 0})
        if st in ("applied", "won", "lost", "invalid"):
            by_genre[g]["応募"] += 1
            by_method[m]["応募"] += 1
        if st == "won":
            by_genre[g]["当選"] += 1
            by_method[m]["当選"] += 1
    return s, by_genre, by_method


def write_csv(path_out, by_genre, by_method):
    with open(path_out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["区分", "項目", "応募数", "当選数", "当選率(%)"])
        for label, table in (("ジャンル", by_genre), ("方式", by_method)):
            for k, v in sorted(table.items(), key=lambda x: -x[1]["応募"]):
                rate = round(v["当選"] / v["応募"] * 100, 1) if v["応募"] else 0
                w.writerow([label, k, v["応募"], v["当選"], rate])


def main():
    ap = argparse.ArgumentParser(description="応募ログ集計レポート")
    ap.add_argument("--csv", default="report.csv")
    args = ap.parse_args()

    s, by_genre, by_method = aggregate()
    print("=== 全体 ===")
    print(f"候補:{s['candidate']} 応募:{s['applied']} 当選:{s['won']} "
          f"落選:{s['lost']} 無効:{s['invalid']} 合計:{s['total']}")
    if s["win_rate"] is not None:
        print(f"応募ベース当選率: {s['win_rate']*100:.1f}%")
    print("\n=== ジャンル別 ===")
    for k, v in sorted(by_genre.items(), key=lambda x: -x[1]["応募"]):
        rate = round(v["当選"]/v["応募"]*100, 1) if v["応募"] else 0
        print(f"  {k}: 応募{v['応募']} 当選{v['当選']} ({rate}%)")
    print("\n=== 方式別 ===")
    for k, v in sorted(by_method.items(), key=lambda x: -x[1]["応募"]):
        rate = round(v["当選"]/v["応募"]*100, 1) if v["応募"] else 0
        print(f"  {k}: 応募{v['応募']} 当選{v['当選']} ({rate}%)")

    write_csv(args.csv, by_genre, by_method)
    print(f"\nCSV出力: {args.csv}（Looker Studio/Excelで可視化可）")


if __name__ == "__main__":
    main()
