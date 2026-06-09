"""
Webフォーム自動入力（設計書 5.2 / 6.5）。Playwrightを使用。
安全設計:
  - 応募前に gate.decide で auto 判定のときだけ実行
  - ページ内のCAPTCHA/禁止文言を再チェック（二重の歯止め）
  - フォーム項目を profile.map_form でマッピング、未対応項目があればエスカレーション
  - dry_run=True（既定）では送信ボタンを押さず、入力予定内容を返す
  - 実送信は submit=True を明示したときのみ
Playwright未インストール環境でも import エラーにしない（遅延import）。
"""
import gate
import profile as profile_mod


def _load_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        return None


def apply(item, prof, page_url=None, dry_run=True, submit=False, timeout_ms=15000):
    """
    1懸賞のフォーム応募。
    return dict: {action, reason, filled, unknown, submitted, ...}
    """
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

            # 二重の歯止め: ページHTMLでCAPTCHA/禁止文言を再判定
            decision = gate.decide(item, page_text=page_text)
            result.update({"action": decision["action"], "reason": decision["reason"]})
            if decision["action"] != "auto":
                return result

            # 入力欄を収集（input/textarea/select の name/placeholder/aria-label）
            fields = page.eval_on_selector_all(
                "input, textarea, select",
                """els => els.map(e => ({
                    name: e.name || e.getAttribute('aria-label') || e.placeholder || e.id || '',
                    type: e.type || e.tagName.toLowerCase()
                })).filter(f => f.name && !['submit','button','hidden'].includes(f.type))"""
            )
            field_names = [f["name"] for f in fields]
            filled, unknown = profile_mod.map_form(field_names, prof)
            result["filled"] = filled
            result["unknown"] = unknown

            # 未対応フィールドがあれば安全側でエスカレーション
            if unknown:
                result["action"] = "escalate"
                result["reason"] = f"未対応フォーム項目あり: {unknown}。人間が確認を。"
                return result

            if dry_run:
                result["reason"] = "dry-run（入力予定を確認、未送信）"
                return result

            # 実入力
            for fn, val in filled.items():
                try:
                    page.fill(f"[name='{fn}']", str(val), timeout=3000)
                except Exception:
                    pass

            if submit:
                page.click("button[type=submit], input[type=submit]", timeout=5000)
                # 送信成功の肯定確認
                body = page.content()
                ok = any(k in body for k in ["ありがとうございました", "応募完了", "受付", "完了しました"])
                result["submitted"] = bool(ok)
                result["reason"] = "送信実行" + ("・成功確認" if ok else "・成功未確認")
            else:
                result["reason"] = "入力のみ（submit=Falseのため未送信）"
            return result
        finally:
            ctx.close()
            browser.close()
