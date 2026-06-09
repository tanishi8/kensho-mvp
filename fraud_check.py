"""
当選通知の詐欺/スパム判定（設計書 4.6）。フェーズ3の中核。
本物の当選だけを通す多段フィルタ。偽陰性（本物を弾く）を許容する安全側設計。

判定の段:
  必須ゲート1: 応募ログ突合（未応募の「当選」は除外）
  必須ゲート2: 送信者ホワイトリスト（@ID/ドメイン完全一致）
  即除外: 金銭/認証情報/金融情報の要求キーワード（1語でアウト）
  高リスク: 外部誘導・煽り・過剰作業（複数で除外）
  メール: SPF/DKIM/DMARC（fail で減点）、表示名詐称
  なりすまし: confusable正規化で @ID/ドメインの偽装検出
"""
import re
import unicodedata

# --- キーワード辞書 ---
INSTANT_REJECT = [
    # 金銭
    "送料負担", "送料をお振込", "送料を振込", "手数料", "先払い", "先にお支払",
    "デポジット", "保証金", "前金", "振込手数料",
    # 認証情報
    "パスワードを教え", "暗証番号", "認証コードを教え", "ワンタイムコード",
    "ログイン情報", "verコード",
    # 金融情報
    "クレジットカード番号", "カード番号を入力", "セキュリティコード",
    "銀行口座番号", "口座番号を教え", "暗証",
]
HIGH_RISK = [
    "アプリをダウンロード", "アプリdl", "無料クレジットカード", "メルマガ登録",
    "登録後スクショ", "スクリーンショットを送", "ポイントサイト",
    "lineで友だち追加", "友だち追加して", "discordへ", "外部サイト",
    "今すぐ", "24時間以内", "本日中", "アカウント停止", "凍結解除", "最終審査に残",
    "bit.ly", "tinyurl",
]
# 本物に多い肯定シグナル
POSITIVE = ["発送のため", "お届け先", "送付先", "賞品の発送", "当選おめでとう", "ご当選"]

# confusable 正規化（紛らわしい文字を正規化してなりすまし検出）
CONFUSABLE = str.maketrans({
    "０": "0", "Ｏ": "o", "О": "o", "o": "o", "0": "0",
    "１": "1", "ｌ": "l", "Ｉ": "i", "I": "i", "l": "l",
    "＿": "_",
})


def normalize(s):
    s = unicodedata.normalize("NFKC", s or "")
    return s.lower().translate(CONFUSABLE)


def _count_hits(text, words):
    t = normalize(text)
    return [w for w in words if normalize(w) in t]


def check(notice, applog_records, whitelist=None):
    """
    1通の当選通知を判定。
    notice: {
        "sender_id": "@xxx"(SNS) or "from@domain"(mail),
        "sender_domain": "example.com"(mailなら),
        "campaign": "...", "organizer": "...",
        "subject": "...", "body": "...",
        "auth": {"spf":"pass","dkim":"pass","dmarc":"pass"}(mailのみ任意),
        "display_name": "...", "channel": "mail"|"sns",
        "verified": "gold"|"blue"|"none"(SNS任意),
    }
    return: {"verdict":"genuine"|"reject"|"review", "score":int, "reasons":[...]}
    """
    whitelist = whitelist or []
    reasons = []
    score = 0

    body = notice.get("body", "")
    subj = notice.get("subject", "")
    text = f"{subj} {body}"

    # --- 即除外キーワード ---
    hits = _count_hits(text, INSTANT_REJECT)
    if hits:
        return {"verdict": "reject", "score": -100,
                "reasons": [f"即除外キーワード: {hits[:3]}"]}

    # --- 必須ゲート1: 応募ログ突合 ---
    applied = _match_applog(notice, applog_records)
    if applied is None:
        reasons.append("応募ログに該当なし（未応募の当選=詐欺の典型）")
        score -= 50
    else:
        reasons.append(f"応募ログ一致: {applied.get('title','')[:30]}")
        score += 40

    # --- 必須ゲート2: ホワイトリスト ---
    wl = _match_whitelist(notice, whitelist, applied)
    if wl == "match":
        reasons.append("送信者がホワイトリストと完全一致")
        score += 40
    elif wl == "spoof":
        return {"verdict": "reject", "score": -100,
                "reasons": ["なりすまし疑い: 主催名は近いが@ID/ドメインが不一致"]}
    else:
        reasons.append("ホワイトリスト未登録の送信者")
        score -= 20

    # --- 高リスクキーワード ---
    hr = _count_hits(text, HIGH_RISK)
    if len(hr) >= 2:
        return {"verdict": "reject", "score": -80,
                "reasons": [f"高リスク語が複数: {hr[:4]}"]}
    elif len(hr) == 1:
        reasons.append(f"高リスク語: {hr}")
        score -= 15

    # --- メール認証 ---
    if notice.get("channel") == "mail":
        auth = notice.get("auth", {})
        if auth:
            if auth.get("dmarc") == "pass":
                score += 15; reasons.append("DMARC=pass")
            else:
                score -= 30; reasons.append(f"DMARC≠pass（{auth.get('dmarc')}）")
            if auth.get("spf") != "pass" or auth.get("dkim") != "pass":
                score -= 10; reasons.append("SPF/DKIMにfailあり")
        # 表示名詐称（表示名に企業名、実ドメインが無関係）
        if _display_name_mismatch(notice):
            score -= 25; reasons.append("表示名とドメインの不一致（詐称疑い）")

    # --- SNS認証バッジ（青は信頼根拠にしない） ---
    if notice.get("channel") == "sns":
        v = notice.get("verified", "none")
        if v == "gold":
            score += 30; reasons.append("金バッジ（認証済み組織）")
        elif v == "blue":
            reasons.append("青バッジ（課金で誰でも取得可・信頼根拠にしない）")

    # --- 肯定シグナル ---
    if _count_hits(text, POSITIVE):
        score += 5

    # --- 判定 ---
    if score >= 50:
        verdict = "genuine"
    elif score >= 10:
        verdict = "review"   # 人間確認推奨
    else:
        verdict = "reject"
    return {"verdict": verdict, "score": score, "reasons": reasons}


def _match_applog(notice, records):
    """通知を応募ログと突合。campaign名 or organizer or ドメインで一致を探す。"""
    camp = normalize(notice.get("campaign", ""))
    org = normalize(notice.get("organizer", ""))
    dom = normalize(notice.get("sender_domain", ""))
    sid = normalize(notice.get("sender_id", ""))
    for r in records:
        if r.get("status") not in ("applied", "candidate", "won", "lost"):
            continue
        rt = normalize(r.get("campaign_name", "") + " " + r.get("title", ""))
        ro = normalize(r.get("organizer", ""))
        rd = normalize(r.get("official_domain", ""))
        ri = normalize(r.get("official_id", ""))
        if camp and camp[:10] and camp[:10] in rt:
            return r
        if org and ro and org == ro:
            return r
        if dom and rd and dom == rd:
            return r
        if sid and ri and sid == ri:
            return r
    return None


def _match_whitelist(notice, whitelist, applied):
    """ホワイトリスト（応募ログの公式情報含む）と完全一致か。なりすましならspoof。"""
    sid = normalize(notice.get("sender_id", ""))
    dom = normalize(notice.get("sender_domain", ""))
    org = normalize(notice.get("organizer", ""))

    entries = list(whitelist)
    if applied:
        entries.append({"organizer": applied.get("organizer", ""),
                        "official_id": applied.get("official_id", ""),
                        "official_domain": applied.get("official_domain", "")})
    spoof = False
    for e in entries:
        eid = normalize(e.get("official_id", ""))
        edom = normalize(e.get("official_domain", ""))
        eorg = normalize(e.get("organizer", ""))
        if (eid and sid and eid == sid) or (edom and dom and edom == dom):
            return "match"
        # 主催名は一致するのに@ID/ドメインが違う → なりすまし
        if eorg and org and eorg == org:
            if (eid and sid and eid != sid) or (edom and dom and edom != dom):
                spoof = True
    return "spoof" if spoof else "none"


def _display_name_mismatch(notice):
    name = normalize(notice.get("display_name", ""))
    dom = normalize(notice.get("sender_domain", ""))
    if not name or not dom:
        return False
    # 表示名に企業名らしき英字があり、ドメインにその語が含まれない場合は疑い
    tokens = re.findall(r"[a-z]{4,}", name)
    if not tokens:
        return False
    return not any(tok in dom for tok in tokens)
