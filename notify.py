"""
Discord Webhook 通知（設計書 4.8）。LINE Notify は終了済みのため Discord を採用。
DISCORD_WEBHOOK_URL が未設定なら標準出力にフォールバック（ローカル確認用）。
"""
import json
import os
import urllib.request


def build_message(items, top_n=15):
    lines = ["**🎯 本日の狙い目懸賞 TOP{}**".format(min(top_n, len(items)))]
    for i, it in enumerate(items[:top_n], 1):
        wc = it.get("win_count")
        wc_s = f"{wc:,}名" if wc else "本数不明"
        tags = []
        if it.get("manual_lottery"):
            tags.append("手動抽選")
        if it.get("local"):
            tags.append("地域限定")
        tag_s = f" [{'/'.join(tags)}]" if tags else ""
        lines.append(
            f"{i}. **{it['title'][:60]}**\n"
            f"   方式:{it['method']} / ジャンル:{it['genre']} / {wc_s} / "
            f"スコア:{it['score']}{tag_s}\n"
            f"   {it.get('link','')}"
        )
    return "\n".join(lines)


def send(items, top_n=15):
    msg = build_message(items, top_n)
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        print("[DISCORD_WEBHOOK_URL 未設定のため標準出力に表示]\n")
        print(msg)
        return False
    # Discord は2000字制限。超過時は分割送信。
    for chunk in _split(msg, 1900):
        data = json.dumps({"content": chunk}).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json", "User-Agent": "kensho-mvp/1.0 (+https://github.com)"})
        urllib.request.urlopen(req, timeout=15)
    return True


def _split(text, limit):
    out, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > limit:
            out.append(cur)
            cur = line
        else:
            cur = f"{cur}\n{line}" if cur else line
    if cur:
        out.append(cur)
    return out


def build_summary(items, top_n=5):
    """その日の新着を要約（件数・好みヒット・締切近・高ROI上位）。"""
    import datetime
    total = len(items)
    pref = [it for it in items if it.get("preference_hit")]
    manual = [it for it in items if it.get("manual_lottery")]
    top = sorted(items, key=lambda x: x.get("roi", 0), reverse=True)[:top_n]

    lines = [f"**📋 懸賞デイリーサマリー {datetime.date.today().isoformat()}**",
             f"新着 {total}件 / 好み一致 {len(pref)}件 / 手動抽選 {len(manual)}件", ""]
    lines.append(f"**🏆 利益率TOP{min(top_n, total)}**")
    for i, it in enumerate(top, 1):
        mark = "★" if it.get("preference_hit") else ""
        wc = it.get("win_count")
        wc_s = f"{wc:,}名" if wc else "本数不明"
        lines.append(f"{i}.{mark} {it['title'][:48]}")
        lines.append(f"   roi:{it.get('roi','?')} / {it.get('genre','')} / {wc_s} / {it.get('link','')}")
    if pref:
        lines.append("")
        lines.append(f"**🍶 好み一致（地酒・海産物等）{len(pref)}件**")
        for it in pref[:5]:
            lines.append(f"・{it['title'][:48]} … {it.get('link','')}")
    return "\n".join(lines)


def send_summary(items, top_n=5):
    msg = build_summary(items, top_n)
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        print("[DISCORD_WEBHOOK_URL 未設定のため標準出力に表示]\n")
        print(msg)
        return False
    for chunk in _split(msg, 1900):
        data = json.dumps({"content": chunk}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "User-Agent": "kensho-mvp/1.0 (+https://github.com)"})
        urllib.request.urlopen(req, timeout=15)
    return True
