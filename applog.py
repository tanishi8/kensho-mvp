"""
応募ログDB（設計書 4.7）。フェーズ1の中核。
後のフェーズ3「本物の当選だけ抽出」の詐欺判定で、当選通知をこのログと突合する。
保存形式は JSON（依存ゼロ・人間も読める）。1懸賞=1レコード。
"""
import json
import os
import datetime
import hashlib

DEFAULT_PATH = "applog.json"

# ステータスの定義
STATUS = ["candidate", "applied", "won", "lost", "invalid"]
# candidate=候補（未応募） applied=応募済 won=当選 lost=落選 invalid=無効


def _load(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def make_id(item):
    """link優先、なければtitleからハッシュIDを生成。"""
    key = item.get("link") or item.get("title", "")
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def upsert_candidate(item, path=DEFAULT_PATH):
    """収集した懸賞を候補として登録（既存なら更新しない）。"""
    db = _load(path)
    rid = make_id(item)
    if rid in db:
        return rid, False
    db[rid] = {
        "id": rid,
        "title": item.get("title", ""),
        "link": item.get("link", ""),
        "source": item.get("source", ""),
        "genre": item.get("genre", ""),
        "method": item.get("method", ""),
        "win_count": item.get("win_count"),
        "manual_lottery": item.get("manual_lottery", False),
        "local": item.get("local", False),
        "score": item.get("score"),
        # 詐欺判定用フィールド（応募時に人間/将来の自動応募が埋める）
        "organizer": item.get("organizer", ""),       # 主催者名
        "official_id": item.get("official_id", ""),     # 公式@ID
        "official_domain": item.get("official_domain", ""),  # 公式ドメイン
        "campaign_name": item.get("campaign_name", item.get("title", "")),
        "status": "candidate",
        "applied_at": None,
        "deadline": item.get("deadline"),
        "receive_deadline": None,  # 当選後の受取期限（won時にmarkで設定）
        "reminded": False,         # 受取期限リマインダー送信済みフラグ
        "note": "",
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    _save(path, db)
    return rid, True


def mark(rid, status, path=DEFAULT_PATH, **fields):
    """ステータス更新と任意フィールドの追記。"""
    db = _load(path)
    if rid not in db:
        raise KeyError(f"id not found: {rid}")
    if status not in STATUS:
        raise ValueError(f"invalid status: {status}（{STATUS}）")
    db[rid]["status"] = status
    if status == "applied" and not db[rid].get("applied_at"):
        db[rid]["applied_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    for k, v in fields.items():
        db[rid][k] = v
    _save(path, db)
    return db[rid]


def all_records(path=DEFAULT_PATH):
    return list(_load(path).values())


def summary(path=DEFAULT_PATH):
    """ステータス別件数を返す。"""
    db = _load(path)
    out = {s: 0 for s in STATUS}
    for r in db.values():
        out[r.get("status", "candidate")] = out.get(r.get("status", "candidate"), 0) + 1
    out["total"] = len(db)
    # 当選率（応募ベース）
    applied = out["applied"] + out["won"] + out["lost"] + out["invalid"]
    out["applied_total"] = applied
    out["win_rate"] = round(out["won"] / applied, 4) if applied else None
    return out


def due_reminders(within_days=3, path=DEFAULT_PATH):
    """受取期限が within_days 日以内に迫った当選(won)レコードを返す。
    receive_deadline は ISO日付文字列(YYYY-MM-DD)を想定。"""
    db = _load(path)
    today = datetime.date.today()
    due = []
    for r in db.values():
        if r.get("status") != "won":
            continue
        rd = r.get("receive_deadline")
        if not rd:
            continue
        try:
            d = datetime.date.fromisoformat(str(rd)[:10])
        except ValueError:
            continue
        days_left = (d - today).days
        if 0 <= days_left <= within_days:
            r["_days_left"] = days_left
            due.append(r)
    due.sort(key=lambda x: x["_days_left"])
    return due


def mark_reminded(rid, path=DEFAULT_PATH):
    db = _load(path)
    if rid in db:
        db[rid]["reminded"] = True
        _save(path, db)
