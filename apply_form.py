"""
Webフォーム自動入力（設計書 5.2 / 6.5）。Playwrightを使用。

安全設計（レビュー反映・不完全送信の防止を最優先）:
  - 応募前に gate.decide で auto 判定のときだけ実行
  - ページ内のCAPTCHA/禁止文言を再チェック（二重の歯止め）
  - select / radio / checkbox（プルダウン・性別・規約同意等）が1つでもあれば escalate
    （現状これらを安全に埋められないため、人間に回す）
  - 入力欄は name 属性で確実に埋められるものだけを対象。name 無し項目があれば escalate
  - profile.map_form で未対応項目があれば escalate
  - dry_run=True（既定）では送信しない
  - 実送信は submit=True のときのみ。送信後は肯定的な完了キーワードで成功確認。
    確認画面（2段階フロー）を検知したら submitted=False として応募記録しない
"""
import gate
import profile as profile_mod

# 送信「完了」を肯定的に示すキーワード（「受付中」等の誤検知を避け、完了系のみ）
SUCCESS_HINTS = [
    "ありがとうございました", "応募を受け付", "受け付けました", "受付を完了",
    "応募完了", "完了しました", "送信しました", "送信が完了", "応募ありがとう",
]
# 確認画面（入力→確認→送信）を示すキーワード
CONFIRM_HINTS = ["ご確認", "内容を確認", "この内容で", "確認画面", "以下の内容で"]


def _load_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        return None


def apply(item, prof, page_url=None, dry_run=True, submit=False, timeout_ms=15000):
    """1懸賞のフォーム応募。return dict: {action, reason, filled, unknown, submitted}"""
    page_url = page_url or item.get("link")
    result = {"title": item.get("title", ""), "url": page_url,
              "submitted": False, "filled": {}, "unknown": []}

    sync_playwright = _load_playwright()
    if sync_playwright is None:
        result["action"] = "error"
        result["reason"] = "playwright未インストール: pip install playwright && playwright install chromium"
        return result

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        try:
            page.goto(page_url, timeout=timeout_ms)
            page_text = page.content()

            # 二重の歯止め: CAPTCHA/禁止文言を再判定
            decision = gate.decide(item, page_text=page_text)
            result.update({"action": decision["action"], "reason": decision["reason"]})
            if decision["action"] != "auto":
                return result

            # フォーム要素を収集（name属性・タグ・typeも保持）
            fields = page.eval_on_selector_all(
                "input, textarea, select",
                """els => els.map(e => ({
                    key: e.name || e.getAttribute('aria-label') || e.placeholder || e.id || '',
                    nameAttr: e.name || '',
                    tag: e.tagName.toLowerCase(),
                    type: (e.type || '').toLowerCase()
                }))"""
            )

            # 選択系（select/radio/checkbox）が1つでもあれば安全側で escalate
            complex_els = [f for f in fields
                           if f["tag"] == "select" or f["type"] in ("radio", "checkbox")]
            if complex_els:
                result["action"] = "escalate"
                result["reason"] = ("プルダウン/選択/チェックボックス（都道府県・性別・規約同意等）"
                                    "を含むため自動応募しない。人間が確認を。")
                return result

            # テキスト系の入力欄（name属性があるものだけ確実に扱える）
            text_types = ("", "text", "email", "tel", "number", "search", "url", "textarea")
            usable = [f for f in fields
                      if f["tag"] in ("input", "textarea")
                      and f["type"] in text_types
                      and f["type"] not in ("submit", "button", "hidden")]

            field_keys = [f["key"] for f in usable if f["key"]]
            key_to_name = {f["key"]: f["nameAttr"] for f in usable if f["key"]}
            filled, unknown = profile_mod.map_form(field_keys, prof)
            result["filled"] = filled
            result["unknown"] = unknown

            # 未対応フィールドがあれば escalate
            if unknown:
                result["action"] = "escalate"
                result["reason"] = f"未対応フォーム項目あり: {unknown}。人間が確認を。"
                return result

            # 埋める対象に name 属性が無いものがあれば確実に入力できない → escalate
            no_name = [k for k in filled if not key_to_name.get(k)]
            if no_name:
                result["action"] = "escalate"
                result["reason"] = f"name属性の無い項目があり確実に入力できない: {no_name}。人間が確認を。"
                return result

            if dry_run:
                result["reason"] = "dry-run（入力予定を確認、未送信）"
                return result

            # 実入力（name属性で確実に）
            for k, val in filled.items():
                page.fill(f"[name='{key_to_name[k]}']", str(val), timeout=3000)

            if not submit:
                result["reason"] = "入力のみ（submit=Falseのため未送信）"
                return result

            # 送信
            page.click("button[type=submit], input[type=submit]", timeout=5000)
            body = page.content()
            ok = any(k in body for k in SUCCESS_HINTS)
            is_confirm = any(k in body for k in CONFIRM_HINTS)

            if ok and not is_confirm:
                result["submitted"] = True
                result["reason"] = "送信実行・完了確認"
            elif is_confirm:
                # 確認画面で止まった＝未完了。安全のため応募記録しない
                result["action"] = "escalate"
                result["reason"] = "確認画面（2段階フロー）を検知。未完了のため人間が確認を。"
            else:
                # 完了が確認できない → 応募記録しない（偽陽性を避ける）
                result["reason"] = "送信したが完了を確認できず（記録しない）。人間が確認を。"
            return result
        finally:
            ctx.close()
            browser.close()
