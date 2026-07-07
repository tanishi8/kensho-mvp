"""
アプリの応募記録(docs/app_applications.json)を applog.json へ取り込む。

アプリ側で「応募した」を押すと、GitHub の docs/app_applications.json に
{id: {id,title,link,applied_at}} が追記される。これを読み、applog に
その懸賞が候補として無ければ登録し、status を applied にする。

GitHub Actions の daily で main の前に実行する想定。ファイルが無ければ何もしない。
"""
import json
import os

import applog

APP_FILE = "docs/app_applications.json"


def main():
    if not os.path.exists(APP_FILE):
        print("app_applications.json なし → スキップ")
        return
    try:
        data = json.load(open(APP_FILE, encoding="utf-8"))
    except Exception as e:
        print(f"読み込み失敗: {e}")
        return

    n = 0
    for rid, rec in data.items():
        # 候補として未登録なら登録（link/titleベース）
        item = {"link": rec.get("link", ""), "title": rec.get("title", "")}
        # make_id はアプリと同じ (link優先→sha1[:12]) なので id は一致する
        applog.upsert_candidate(item)
        try:
            r = applog.mark(rid, "applied", applied_at=rec.get("applied_at"))
            n += 1
        except KeyError:
            # id 不一致（アプリ側idが古い等）→ タイトルで新規登録して応募済みに
            new_id = applog.make_id(item)
            applog.upsert_candidate(item)
            try:
                applog.mark(new_id, "applied", applied_at=rec.get("applied_at"))
                n += 1
            except KeyError:
                pass
    print(f"取り込み: {n} 件を applied に更新")


if __name__ == "__main__":
    main()
