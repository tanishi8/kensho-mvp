"""
懸賞テキストから構造化情報を抽出するモジュール（フェーズ0：正規表現ベース）。
設計書 4.2 抽出・正規化モジュールに対応。後にLLM抽出を二次段として追加可能。
"""
import re

# ジャンル判定用キーワード辞書
GENRE_KEYWORDS = {
    "現金": ["現金", "キャッシュ", "万円分の現金"],
    "金券": ["quoカード", "quo", "amazonギフト", "ギフトカード", "図書カード",
             "商品券", "ギフト券", "paypay", "えらべるpay", "電子マネー", "ペイ"],
    "食品": ["食品", "お菓子", "スイーツ", "飲料", "ドリンク", "コーヒー", "ビール",
             "お米", "新米", "肉", "牛肉", "和牛", "グルメ", "食べ", "飲み", "調味料",
             "日本酒", "地酒", "焼酎", "ワイン", "酒",
             "海鮮", "海産", "魚介", "カニ", "蟹", "ホタテ", "牡蠣", "うに", "いくら",
             "果物", "フルーツ", "特産", "名産", "ご当地"],
    "日用品": ["日用品", "洗剤", "シャンプー", "化粧品", "コスメ", "ティッシュ", "おむつ"],
    "旅行": ["旅行", "宿泊", "ペア", "温泉", "ホテル", "ツアー", "招待", "チケット"],
    "家電": ["家電", "テレビ", "冷蔵庫", "掃除機", "ドライヤー", "イヤホン",
             "スピーカー", "炊飯器", "電子レンジ", "ゲーム機", "switch", "ipad"],
}

# 応募方式判定用キーワード
METHOD_KEYWORDS = {
    "スタンプラリー": ["スタンプラリー", "スタンプ", "周遊", "デジタルラリー"],
    "アンケート": ["アンケート", "クイズ", "回答して", "モニター"],
    "即時当選": ["その場で当たる", "その場で当選", "インスタントウィン", "即時"],
    "レシート": ["レシート"],
    "クローズド": ["対象商品", "購入", "マストバイ", "バーコード", "応募マーク", "対象製品"],
    "instagram": ["instagram", "インスタグラム", "インスタ"],
    "x": ["リポスト", "リツイート", "twitter", "ｘ懸賞", "フォロー&リポスト"],
    "はがき": ["はがき", "ハガキ", "郵送", "投函"],
    "メール": ["メールで応募", "メール応募"],
    "ネット": ["web応募", "ウェブ", "フォーム", "応募フォーム", "会員"],
}

MANUAL_LOTTERY_HINTS = ["後日抽選", "厳正な抽選", "発送をもって", "当選者の発表は",
                        "自治体", "市役所", "町", "県", "商工会", "タウン誌", "フリーペーパー"]

LOCAL_HINTS = ["限定", "在住", "対象店舗", "店舗限定", "地域", "県内", "市内"]

# 当選本数: 「100名様」「1,000名」「5名様」など
RE_WIN_COUNT = re.compile(r"([0-9０-９][0-9０-９,，]*)\s*(名様|名|人|当選)")
# 金額: 「1,000円分」「3万円」「500円」
RE_YEN = re.compile(r"([0-9０-９][0-9０-９,，]*)\s*円")
RE_MAN_YEN = re.compile(r"([0-9０-９]+)\s*万円")


def _to_int(s):
    z = str.maketrans("０１２３４５６７８９，", "0123456789,")
    return int(s.translate(z).replace(",", ""))


def extract_win_count(text):
    """最大の当選本数を返す（複数ヒット時）。不明なら None。"""
    counts = []
    for m in RE_WIN_COUNT.finditer(text):
        try:
            counts.append(_to_int(m.group(1)))
        except ValueError:
            pass
    return max(counts) if counts else None


def extract_prize_value(text):
    """賞品の概算金額（円）を返す。万円表記を優先。不明なら None。"""
    vals = []
    for m in RE_MAN_YEN.finditer(text):
        try:
            vals.append(_to_int(m.group(1)) * 10000)
        except ValueError:
            pass
    for m in RE_YEN.finditer(text):
        try:
            vals.append(_to_int(m.group(1)))
        except ValueError:
            pass
    return max(vals) if vals else None


def detect_genre(text):
    t = text.lower()
    for genre, kws in GENRE_KEYWORDS.items():
        if any(k.lower() in t for k in kws):
            return genre
    return "その他"


# 「その場で当たる」等より優先してSNS/LINE系を人間対応(x)へ回す強シグナル
SNS_STRONG = ["x懸賞", "xキャンペーン", "ｘ懸賞", "ｘキャンペーン",
              "line懸賞", "lineキャンペーン",
              "リポスト", "リツイート", "フォロー&リポスト", "フォロー＆リポスト",
              "rt&フォロー", "フォロー&フォロー"]
# まとめ/一覧記事（応募先ではない）を方式不明にして人間確認へ回す
LISTING_HINTS = ["懸賞情報", "毎日更新", "新着情報", "懸賞ブログ", "当選人数が多い"]


def detect_method(text):
    t = text.lower()
    # SNS/LINE は最優先で人間対応(x)。「即時当選」語での誤autoを防ぐ
    if any(k in t for k in SNS_STRONG):
        return "x"
    # まとめ/一覧記事は方式不明（gateでescalate＝人間確認）
    if any(h in text for h in LISTING_HINTS):
        return "不明"
    for method, kws in METHOD_KEYWORDS.items():
        if any(k.lower() in t for k in kws):
            return method
    return "不明"


def is_manual_lottery(text):
    return any(h in text for h in MANUAL_LOTTERY_HINTS)


def is_local(text):
    return any(h in text for h in LOCAL_HINTS)


def extract(title, summary=""):
    """1懸賞分の構造化辞書を返す。"""
    text = f"{title} {summary}"
    return {
        "title": title,
        "genre": detect_genre(text),
        "method": detect_method(text),
        "win_count": extract_win_count(text),
        "prize_value": extract_prize_value(text),
        "manual_lottery": is_manual_lottery(text),
        "local": is_local(text),
    }


# 既定の除外語（宝くじ結果・当選番号・まとめ/比較記事・終了案件等のノイズ）。
# 呼び出し側が exclude を渡さなくても、この既定で弾く。
DEFAULT_EXCLUDE = [
    "当選番号", "当せん番号", "抽せん結果", "抽選結果", "当選発表", "当選者発表",
    "当選者一覧", "結果発表", "当選報告", "ランキング", "まとめ", "比較", "とは",
    "速報", "値上げ", "終了しました", "受付終了", "締切ました",
]


def is_sweepstakes(title, summary, keywords, exclude=None):
    """応募機会だけを通す。keywords(any_of)を1つ以上含み、exclude(none_of)を
    1つも含まない場合のみ True。exclude未指定なら DEFAULT_EXCLUDE を使う。"""
    if exclude is None:
        exclude = DEFAULT_EXCLUDE
    text = f"{title} {summary}"
    if exclude and any(x in text for x in exclude):
        return False
    return any(k in text for k in keywords)
