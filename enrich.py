"""
感想・意見の「肉付け」機能（LLM）。

用途:
  手動抽選・モニター・Instagram など「コメントが当落に効く」懸賞で、
  あなたが書いた短い感想（例:「日本酒が好き。父と晩酌したい」）を、
  当選しやすい丁寧な応募コメントに肉付けする。

方針:
  - 調査知見に基づき「①応募理由/ファン度 ＋ ②当選後の具体的な使い道」を2〜3文で。
  - 定型文（「当たりますように」だけ）は避ける。個人の実体験を活かす。
  - LLM は Gemini（既定）。キー未設定/失敗時は comment.py のルールベースへ安全フォールバック。
  - 誇張・虚偽は付けない（本当らしさが逆効果になるため、事実ベースで整える指示）。

CLI:
  python enrich.py --title "..." --genre 食品 --opinion "日本酒が好き。父と晩酌したい" --n 2
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

import comment as rule_comment

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"

PROMPT = """あなたは日本の懸賞応募コメントの作成を手伝うアシスタントです。
応募者が書いた「短い感想・意見」を、当選しやすい丁寧な応募コメントに肉付けしてください。

厳守ルール:
- 応募者が書いていない事実（家族構成・居住地・体験など）を勝手に創作しない。書かれた範囲だけを自然に整える。
- 「①その商品/賞品への関心・応募理由」＋「②当選後の具体的な使い道」を2〜3文で。
- 定型句だけ（「当たりますように」等）にしない。誇張・過剰な媚びは避け、誠実で具体的に。
- 主催者に敬意を払う丁寧語。1案あたり120〜200字程度。
- 出力は JSON のみ。{{"comments": ["案1", "案2", ...]}} の形式。

懸賞情報:
- タイトル: {title}
- ジャンル: {genre}
- 応募方式: {method}

応募者の短い感想・意見:
{opinion}

案を {n} 個、JSONで:"""


def _http_post(url, headers, payload, timeout=25):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _parse(text):
    t = text.strip()
    if "```" in t:
        t = t.split("```")[1]
        if t.startswith("json"):
            t = t[4:]
    t = t.strip()
    s, e = t.find("{"), t.rfind("}")
    if s != -1 and e != -1:
        t = t[s:e + 1]
    return json.loads(t)


def enrich_comment(title, genre="その他", method="", opinion="", n=2, cfg=None):
    """短い感想 opinion を肉付けしたコメント案（リスト）を返す。

    LLM 未設定/失敗時はルールベース(comment.py)で生成し、opinion があれば冒頭に添える。
    返り値: {"comments": [...], "engine": "gemini"|"rule", "note": "..."}
    """
    cfg = cfg or {}
    llm_cfg = cfg.get("llm", {})
    provider = os.environ.get("LLM_PROVIDER", llm_cfg.get("provider", "gemini"))
    key = os.environ.get("GEMINI_API_KEY")

    if provider == "gemini" and key and opinion.strip():
        try:
            model = llm_cfg.get("model", DEFAULT_GEMINI_MODEL)
            prompt = PROMPT.format(title=title, genre=genre, method=method or "不明",
                                   opinion=opinion.strip(), n=n)
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7,
                                     "responseMimeType": "application/json"},
            }
            headers = {"Content-Type": "application/json", "x-goog-api-key": key}
            res = _http_post(f"{GEMINI_BASE}{model}:generateContent", headers, payload)
            text = res["candidates"][0]["content"]["parts"][0]["text"]
            parsed = _parse(text)
            comments = [c.strip() for c in parsed.get("comments", []) if c.strip()]
            if comments:
                return {"comments": comments[:n], "engine": "gemini", "note": ""}
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError,
                ValueError, json.JSONDecodeError, IndexError) as e:
            note = f"LLM失敗({type(e).__name__})→ルールベースに切替"
            base = rule_comment.generate({"genre": genre, "title": title}, n=n)
            if opinion.strip():
                base = [f"{opinion.strip()}。{b}" for b in base]
            return {"comments": base, "engine": "rule", "note": note}

    # ルールベース（LLM未使用時）
    base = rule_comment.generate({"genre": genre, "title": title}, n=n)
    if opinion.strip():
        base = [f"{opinion.strip()}。{b}" for b in base]
    return {"comments": base, "engine": "rule",
            "note": "" if opinion.strip() else "感想未入力のため一般テンプレートを生成"}


def main():
    ap = argparse.ArgumentParser(description="感想・意見の肉付け（応募コメント生成）")
    ap.add_argument("--title", required=True)
    ap.add_argument("--genre", default="その他")
    ap.add_argument("--method", default="")
    ap.add_argument("--opinion", default="")
    ap.add_argument("--n", type=int, default=2)
    args = ap.parse_args()
    cfg = {}
    try:
        import yaml
        if os.path.exists("config.yaml"):
            cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
    except Exception:
        pass
    res = enrich_comment(args.title, args.genre, args.method, args.opinion, args.n, cfg)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
