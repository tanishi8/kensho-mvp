"""
応募者プロファイル管理（設計書 4.7 / 8）。
氏名・住所・連絡先などの応募情報を管理し、フォーム項目へ差し込む。
- 実データはコードに置かず profile.json（gitignore対象）に保存
- フォーム項目名（label/name/placeholder/autocomplete）→ プロファイル値のマッピング辞書を持つ
- なりすまし・虚偽属性には使わない（本人の実情報のみ）
"""
import json
import os

DEFAULT_PATH = "profile.json"

# プロファイルの標準キー
FIELDS = ["last_name", "first_name", "last_kana", "first_kana",
          "zip", "pref", "city", "address1", "address2",
          "tel", "email", "birth_year", "birth_month", "birth_day", "gender"]

# フォーム側の項目名 → プロファイルキー の対応辞書（部分一致・小文字で照合）
FIELD_ALIASES = {
    "last_name": ["姓", "苗字", "氏", "lastname", "last-name", "family", "sei"],
    "first_name": ["名", "名前", "firstname", "first-name", "given", "mei"],
    "last_kana": ["セイ", "姓カナ", "せい", "lastkana"],
    "first_kana": ["メイ", "名カナ", "めい", "firstkana"],
    "zip": ["郵便", "〒", "zip", "postal", "postcode", "yubin"],
    "pref": ["都道府県", "県", "pref", "prefecture", "todofuken"],
    "city": ["市区町村", "市町村", "city", "shikuchoson"],
    "address1": ["番地", "住所1", "町名", "address1", "addr1"],
    "address2": ["建物", "マンション", "部屋", "住所2", "address2", "addr2", "建物名"],
    "tel": ["電話", "tel", "phone", "denwa", "携帯"],
    "email": ["メール", "mail", "email", "e-mail", "メールアドレス"],
    "birth_year": ["生年", "誕生年", "year", "birthyear", "年"],
    "birth_month": ["誕生月", "month", "birthmonth", "月"],
    "birth_day": ["誕生日", "day", "birthday", "日"],
    "gender": ["性別", "gender", "sex", "seibetsu"],
}


def load(path=DEFAULT_PATH):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} が見つかりません。profile.sample.json をコピーして作成してください。")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# 判定の優先順（具体的・複合語のキーを先に評価して誤爆を防ぐ）
MATCH_ORDER = ["address2", "address1", "last_kana", "first_kana",
               "last_name", "first_name", "zip", "pref", "city",
               "tel", "email", "birth_year", "birth_month", "birth_day", "gender"]


def match_field(form_field_name):
    """フォームの項目名から対応するプロファイルキーを推定。不明ならNone。"""
    t = (form_field_name or "").lower()
    # 建物・住所2を最優先（"建物名"の"名"がfirst_nameに誤爆するのを防ぐ）
    if any(a in t for a in ["建物", "マンション", "アパート", "部屋", "号室", "住所2", "address2", "addr2"]):
        return "address2"
    for key in MATCH_ORDER:
        for a in FIELD_ALIASES.get(key, []):
            al = a.lower()
            # 1文字の漢字エイリアス（姓/名/県/年/月/日 等）は誤爆しやすいので
            # 前後に別の漢字がない（=ほぼ単独 or 括弧付き）場合のみ一致とする
            if len(al) == 1 and "\u4e00" <= al <= "\u9fff":
                import re as _re
                if _re.search(rf"(^|[^一-龥]){al}([^一-龥]|$)", t):
                    return key
            elif al in t:
                return key
    return None


def map_form(field_names, profile):
    """
    フォームの項目名リストを受け取り、{項目名: 値} と未対応リストを返す。
    未対応(unknown)があれば呼び出し側で人間にエスカレーションする。
    """
    filled, unknown = {}, []
    for fn in field_names:
        key = match_field(fn)
        if key and profile.get(key) not in (None, ""):
            filled[fn] = profile[key]
        else:
            unknown.append(fn)
    return filled, unknown
