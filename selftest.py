"""
結合テスト（オフラインで完結）。全モジュールの連携を検証する品質ゲート。
実ネットワーク不要。CI（GitHub Actions）でも回せる。
  python selftest.py
"""
import sys
import yaml
import feedparser

import extract, llm_extract, score, cost, gate, applog, comment, fraud_check, profile

PASS, FAIL = 0, 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {name}")
    else: FAIL += 1; print(f"  ❌ {name}")

cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))

print("[1] 収集→抽出→スコア（利益率）")
d = feedparser.parse("sample_feed.xml")
items = []
for e in d.entries:
    info = extract.extract(e.get("title",""), e.get("summary",""))
    info = llm_extract.enrich(info, cfg, summary=e.get("summary",""))  # キー無し→正規表現のまま
    items.append(score.score(info, cfg))
check("8件抽出できる", len(items) == 8)
check("全件にroiが付く", all("roi" in it for it in items))
check("全件にcostが付く", all(it["cost"] >= 1 for it in items))

print("[2] 利益率順の並び替え")
roi_sorted = sorted(items, key=lambda x: -x["roi"])
check("roi降順で先頭が最大", roi_sorted[0]["roi"] == max(i["roi"] for i in items))

print("[3] ガードレール（gate）")
check("即時当選はauto", gate.decide({"method":"即時当選","title":""})["action"]=="auto")
check("XはツールB送り(skip)", gate.decide({"method":"x","title":""})["action"]=="skip")
check("CAPTCHA検知でescalate",
      gate.decide({"method":"ネット","title":""}, page_text="g-recaptcha")["action"]=="escalate")

print("[4] プロファイル・マッピング")
prof = profile.load("profile.sample.json")
filled, unknown = profile.map_form(["お名前(姓)","郵便番号","建物名","ご職業"], prof)
check("建物名→建物(誤爆なし)", filled.get("建物名")=="サンプルマンション101")
check("未対応(ご職業)を検出", "ご職業" in unknown)

print("[5] 詐欺判定（fraud_check）")
recs=[{"campaign_name":"テスト懸賞","organizer":"テスト社","official_domain":"test.co.jp",
       "status":"applied","title":"テスト懸賞"}]
genuine=fraud_check.check({"channel":"mail","sender_id":"a@test.co.jp","sender_domain":"test.co.jp",
  "organizer":"テスト社","campaign":"テスト懸賞","subject":"ご当選","body":"発送のため住所登録を",
  "auth":{"spf":"pass","dkim":"pass","dmarc":"pass"}}, recs, [])
check("正規の当選はgenuine", genuine["verdict"]=="genuine")
scam=fraud_check.check({"channel":"mail","sender_id":"x@evil.com","sender_domain":"evil.com",
  "subject":"当選","body":"送料を先にお振込ください。クレジットカード番号を入力"}, recs, [])
check("詐欺(送料/カード)はreject", scam["verdict"]=="reject")

print("[6] コメント生成")
cm = comment.generate({"genre":"旅行","title":"温泉"}, n=2)
check("コメント2件生成", len(cm)==2 and all("当選しましたら" in c for c in cm))

print(f"\n結果: {PASS} passed / {FAIL} failed")
sys.exit(1 if FAIL else 0)
