"""
応募コストの推定（PROFITABILITY.md の利益率分析に基づく）。
利益率 = 期待価値 ÷ コスト。コストは「金銭＋時間（円換算）＋リスク」の合算。

ポイント:
- 無料系(SNS/即時当選/ネット/メール/アンケート)は金銭コスト0、時間のみ。
- クローズド/レシートは購入が必要だが「普段買う商品」なら追加コストは小。
  → buy_list(普段買う商品キーワード)に一致すれば追加コストを大幅圧縮。
- はがきは郵送費(85円)。
"""

# 方式ごとの「時間コスト（円換算）」目安。1件の手間を時給1000円で換算した概算。
TIME_COST = {
    "即時当選": 2,    # 数秒
    "x": 2,
    "instagram": 5,
    "ネット": 10,
    "メール": 10,
    "アンケート": 30,  # 回答に手間
    "レシート": 20,    # 撮影・入力
    "クローズド": 20,
    "はがき": 40,      # 記入の手間
    "不明": 10,
}
# 郵送費（円）
POSTAGE = {"はがき": 85}


def estimate_cost(item, cfg):
    """
    1懸賞の応募コスト（円）を推定して返す。最低1円（ゼロ割回避）。
    cfg['cost'] で各種パラメータを上書き可能。
    """
    cc = (cfg or {}).get("cost", {})
    method = item.get("method", "不明")

    # 時間コスト
    time_cost = cc.get("time_cost", {}).get(method, TIME_COST.get(method, 10))

    # 郵送費
    postage = POSTAGE.get(method, 0)

    # 購入コスト（クローズド/レシート/マストバイ）
    purchase = 0
    if method in ("クローズド", "レシート"):
        # 普段買う商品リストに一致すれば追加コスト≒0、しなければ既定購入額を計上
        title = item.get("title", "")
        buy_list = cc.get("buy_list", [])
        if buy_list and any(kw in title for kw in buy_list):
            purchase = cc.get("routine_purchase_cost", 0)  # 既定0（どのみち買う）
        else:
            purchase = cc.get("default_purchase_cost", 500)  # 買い増し想定

    total = time_cost + postage + purchase
    return max(total, 1)
