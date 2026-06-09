"""
期待価値スコアリング＋利益率（設計書 4.3 / 4.4 ＋ PROFITABILITY.md）。

期待価値 = 当選確率係数 × 市場価値(対数圧縮) × 換金率 × 必要度 × 各種ボーナス
利益率(roi) = 期待価値 ÷ 応募コスト（cost.py）

- 確定報酬(モニター/座談会)は抽選でないため当選確率=1.0扱い。
- 利益率順に並べると「コスパの良い懸賞」が上位に来る。
"""
import datetime
import math

import cost as cost_mod

# ジャンル別のおおまかな換金率（額面比）。調査の換金率データに基づく。
CASH_RATE = {
    "現金": 1.0, "金券": 0.92, "家電": 0.6,
    "食品": 0.3, "日用品": 0.3, "旅行": 0.5, "その他": 0.4,
}
# 賞品額が取れない場合のジャンル別フォールバック概算額（円）
FALLBACK_VALUE = {
    "現金": 5000, "金券": 1000, "家電": 20000,
    "食品": 1500, "日用品": 1000, "旅行": 50000, "その他": 1500,
}
# 確定報酬とみなす方式（抽選でなく選考だが、当選=ほぼ確定の報酬型）
GUARANTEED_METHODS = {"モニター", "アンケート"}  # アンケートは謝礼確定型を含む


def win_count_factor(win_count, table):
    if win_count is None:
        return 1.0
    for row in sorted(table, key=lambda r: -r["min"]):
        if win_count >= row["min"]:
            return row["factor"]
    return 1.0


def score(item, cfg):
    sc = cfg["scoring"]
    method = item.get("method", "不明")
    genre = item.get("genre", "その他")

    # 当選確率係数（確定報酬は1.0）
    if item.get("guaranteed") or method in GUARANTEED_METHODS and item.get("reward_fixed"):
        prob = 1.0
    else:
        prob = sc["method_weight"].get(method, sc["method_weight"]["不明"])

    value = item.get("prize_value") or FALLBACK_VALUE.get(genre, 1500)
    cash = CASH_RATE.get(genre, 0.4)
    # cash_weight(0〜1)で換金率の効きを調整。小さいほど換金性の差が縮まり、
    # 食品・特産・旅行(換金率低)が金券に埋もれにくくなる。既定0.5。
    cw = sc.get("cash_weight", 1.0)
    cash_eff = cash ** cw
    need = sc["need_factor"].get(genre, sc["need_factor"]["その他"])

    factor = win_count_factor(item.get("win_count"), sc["win_count_bonus"])
    if item.get("local"):
        factor *= sc["local_bonus"]
    if item.get("manual_lottery"):
        factor *= sc["manual_lottery_bonus"]
    if datetime.date.today().month == 12:
        factor *= sc["december_bonus"]

    # 好みジャンル加点（地酒・海産物・食品・特産品など。既存に上乗せ）
    pref = cfg.get("preference", {})
    item["preference_hit"] = False
    if pref.get("enabled"):
        text = f"{item.get('title','')} {item.get('genre','')}"
        if any(k in text for k in pref.get("keywords", [])):
            factor *= pref.get("bonus", 1.5)
            item["preference_hit"] = True

    # 価値は対数で圧縮（高額賞品が支配的になりすぎないように）
    value_term = math.log10(max(value, 1) + 10)

    expected = prob * value_term * cash_eff * need * factor
    item["score"] = round(expected, 3)

    # 利益率（期待価値 ÷ コスト）
    c = cost_mod.estimate_cost(item, cfg)
    item["cost"] = c
    item["roi"] = round(expected / c, 4)

    item["score_breakdown"] = {
        "prob": prob, "value": value, "cash_rate": cash,
        "need": need, "cash_eff": round(cash_eff,3), "factor": round(factor, 3), "cost": c,
        "preference_hit": item["preference_hit"],
    }
    return item
