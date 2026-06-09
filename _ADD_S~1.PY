code = '''

def build_summary(items, top_n=5):
    """その日の新着を要約（件数・好みヒット・締切近・高ROI上位）。"""
    import datetime
    total = len(items)
    pref = [it for it in items if it.get("preference_hit")]
    manual = [it for it in items if it.get("manual_lottery")]
    top = sorted(items, key=lambda x: x.get("roi", 0), reverse=True)[:top_n]

    lines = [f"**\U0001F4CB 懸賞デイリーサマリー {datetime.date.today().isoformat()}**",
             f"新着 {total}件 / 好み一致 {len(pref)}件 / 手動抽選 {len(manual)}件", ""]
    lines.append(f"**\U0001F3C6 利益率TOP{min(top_n, total)}**")
    for i, it in enumerate(top, 1):
        mark = "★" if it.get("preference_hit") else ""
        wc = it.get("win_count")
        wc_s = f"{wc:,}名" if wc else "本数不明"
        lines.append(f"{i}.{mark} {it['title'][:48]}")
        lines.append(f"   roi:{it.get('roi','?')} / {it.get('genre','')} / {wc_s} / {it.get('link','')}")
    if pref:
        lines.append("")
        lines.append(f"**\U0001F376 好み一致（地酒・海産物等）{len(pref)}件**")
        for it in pref[:5]:
            lines.append(f"・{it['title'][:48]} … {it.get('link','')}")
    return "\\n".join(lines)


def send_summary(items, top_n=5):
    msg = build_summary(items, top_n)
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        print("[DISCORD_WEBHOOK_URL 未設定のため標準出力に表示]\\n")
        print(msg)
        return False
    for chunk in _split(msg, 1900):
        data = json.dumps({"content": chunk}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15)
    return True
'''
with open("notify.py","a",encoding="utf-8") as f:
    f.write(code)
print("appended")
