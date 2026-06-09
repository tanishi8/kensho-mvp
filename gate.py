"""
応募可否ガードレール（設計書 5.4 / 2.3）。ツールAの安全装置。
「完全自動で応募してよいか」を判定し、ダメなものは理由つきで人間にエスカレーション。

判定の柱:
  1) 応募方式が自動化可能か（メール/CAPTCHA無しフォーム/即時当選/アンケート のみ許可）
  2) SNS・はがき・購入必須クローズドは自動応募しない（ツールB送り）
  3) CAPTCHA検知 → 応募中止・エスカレーション
  4) 規約に自動応募/bot禁止の文言 → 応募中止・エスカレーション
"""

# ツールAで自動応募してよい方式
AUTO_ALLOWED_METHODS = {"メール", "ネット", "即時当選", "アンケート"}
# 明確に人間（ツールB）に回す方式
HUMAN_ONLY_METHODS = {"x", "instagram", "はがき", "クローズド", "レシート", "スタンプラリー"}

# 規約・本文から自動応募禁止を示す語
BOT_BAN_HINTS = [
    "自動応募", "ボットによる", "botによる", "プログラムによる", "マクロ",
    "スクリプト", "自動化ツール", "自動投稿", "自動取得",
]
# CAPTCHAの存在を示す語（フォームHTMLや説明文から）
CAPTCHA_HINTS = ["recaptcha", "hcaptcha", "captcha", "私はロボットではありません",
                 "g-recaptcha", "認証画像", "画像認証"]


def _contains(text, hints):
    t = (text or "").lower()
    return any(h.lower() in t for h in hints)


def decide(item, page_text="", terms_text=""):
    """
    応募可否を判定して dict を返す。
    return: {"action": "auto"|"escalate"|"skip", "reason": str}
      auto     … ツールAで自動応募してよい
      escalate … 人間が対応すべき（CAPTCHA/規約/未対応）→ツールBや手動へ
      skip     … 対象外（方式的に自動応募しない）
    """
    method = item.get("method", "不明")

    # 1) 明確に人間対応の方式
    if method in HUMAN_ONLY_METHODS:
        return {"action": "skip",
                "reason": f"方式『{method}』はツールB（人間）対象。自動応募しない。"}

    # 2) CAPTCHA 検知 → エスカレーション
    if _contains(page_text, CAPTCHA_HINTS) or _contains(item.get("title", ""), CAPTCHA_HINTS):
        return {"action": "escalate",
                "reason": "CAPTCHA検知。サイトが自動化を拒否。人間が解決を。"}

    # 3) 規約に自動応募禁止 → エスカレーション（＝自動はしない）
    if _contains(terms_text, BOT_BAN_HINTS) or _contains(page_text, BOT_BAN_HINTS):
        return {"action": "escalate",
                "reason": "規約に自動応募/bot禁止の記載。規約遵守のため自動応募しない。"}

    # 4) 自動応募可能な方式
    if method in AUTO_ALLOWED_METHODS:
        return {"action": "auto", "reason": f"方式『{method}』は自動応募可能。"}

    # 5) 方式不明 → 安全側でエスカレーション
    return {"action": "escalate",
            "reason": f"方式『{method}』が不明。安全のため人間が確認を。"}
