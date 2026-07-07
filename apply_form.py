"""
Webフォーム自動入力（設計書 5.2 / 6.5）。Playwrightを使用。

安全設計（1次・2次レビュー反映。不完全送信/多重応募の防止を最優先）:
  - gate.decide が auto のときだけ実行。ページHTMLでCAPTCHA/禁止文言を再チェック
  - select / radio / checkbox（プルダウン・性別・規約同意）が1つでもあれば escalate
  - key（name/aria-label/placeholder/id）が全て空のテキスト欄があれば escalate（D）
  - profile.map_form の未対応項目、name属性の無い項目があれば escalate
  - dry_run=True では送信しない
  - submit後は wait_for_load_state で遷移を待ってから完了判定（C）
  - 完了を確認できない場合は attempted=True を返す（B: 呼び出し側で「送信したが結果不明」
    として記録し自動再送しない）。確認画面検知時も同様
"""
import time
import gate
import profile as profile_mod

SUCCESS_HINTS = [
    "ありがとうございました", "応募を受け付", "受け付けました", "受付を完了",
    "応募完了", "完了しました", "送信しました", "送信が完了", "応募ありがとう",
]
CONFIRM_HINTS = ["ご確認", "内容を確認", "この内容で", "確認画面", "以下の内容で"]
TEXT_TYPES = ("", "text", "email", "tel", "number", "search", "url", "textarea")


def _load_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        return None


def apply(item, prof, page_url=None, dry_run=True, submit=False, timeout_ms=15000):
    """1懸賞のフォーム応募。
    return dict: {action, reason, filled, unknown, submitted, attempted}"""
    page_url = page_url or item.get("link")
    result = {"title": item.get("title", ""), "url": page_url,
              "submitted": False, "attempted": False, "filled": {}, "unknown": []}

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

            fields = page.eval_on_selector_all(
                "input, textarea, select",
                """els => els.map(e => ({
                    key: e.name || e.getAttribute('aria-label') || e.placeholder || e.id || '',
                    nameAttr: e.name || '',
                    tag: e.tagName.toLowerCase(),
                    type: (e.type || '').toLowerCase()
                }))"""
            )

            # 選択系（select/radio/checkbox）があれば escalate
            if [f for f in fields if f["tag"] == "select" or f["type"] in ("radio", "checkbox")]:
                result["action"] = "escalate"
                result["reason"] = ("プルダウン/選択/チェックボックス（都道府県・性別・規約同意等）"
                                    "を含むため自動応募しない。人間が確認を。")
                return result

            # テキスト系のうち submit/button/hidden を除く入力欄
            text_inputs = [f for f in fields
                           if f["tag"] in ("input", "textarea")
                           and f["type"] in TEXT_TYPES
                           and f["type"] not in ("submit", "button", "hidden")]

            # key が全く取れないテキスト欄がある → 必須かもしれず埋め漏れの恐れ → escalate（D）
            if [f for f in text_inputs if not f["key"]]:
                result["action"] = "escalate"
                result["reason"] = "識別子(name/label)の無い入力欄があり埋め漏れの恐れ。人間が確認を。"
                return result

            field_keys = [f["key"] for f in text_inputs]
            key_to_name = {f["key"]: f["nameAttr"] for f in text_inputs}
            filled, unknown = profile_mod.map_form(field_keys, prof)
            result["filled"] = filled
            result["unknown"] = unknown

            if unknown:
                result["action"] = "escalate"
                result["reason"] = f"未対応フォーム項目あり: {unknown}。人間が確認を。"
                return result

            no_name = [k for k in filled if not key_to_name.get(k)]
            if no_name:
                result["action"] = "escalate"
                result["reason"] = f"name属性の無い項目があり確実に入力できない: {no_name}。人間が確認を。"
                return result

            if dry_run:
                result["reason"] = "dry-run（入力予定を確認、未送信）"
                return result

            for k, val in filled.items():
                page.fill(f"[name='{key_to_name[k]}']", str(val), timeout=3000)

            if not submit:
                result["reason"] = "入力のみ（submit=Falseのため未送信）"
                return result

            # 送信 → 遷移を待つ（C）
            result["attempted"] = True
            page.click("button[type=submit], input[type=submit]", timeout=5000)
            try:
                page.wait_for_load_state("load", timeout=8000)
            except Exception:
                pass
            time.sleep(1.5)
            body = page.content()
            ok = any(k in body for k in SUCCESS_HINTS)
            is_confirm = any(k in body for k in CONFIRM_HINTS)

            if ok and not is_confirm:
                result["submitted"] = True
                result["reason"] = "送信実行・完了確認"
            elif is_confirm:
                result["action"] = "escalate"
                result["reason"] = "確認画面（2段階フロー）を検知。未完了のため人間が確認を。"
            else:
                # 送信は押したが完了を確認できない → attempted のまま（自動再送しない）
                result["reason"] = "送信したが完了を確認できず。結果不明として記録し人間が確認を。"
            return result
        finally:
            ctx.close()
            browser.close()
