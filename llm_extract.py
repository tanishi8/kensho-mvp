"""
LLM二次抽出（設計書 4.2）。正規表現で取り切れない曖昧表現を補完する。
- 既定プロバイダ: Gemini。モデルはconfig.yaml の llm.model で指定可。
- provider: gemini | claude | none を config.yaml / 環境変数で切替
- APIキー未設定や失敗時は正規表現の結果をそのまま使う（安全フォールバック）
- 依存を増やさないため標準ライブラリ(urllib)でREST呼び出し
"""
import json
import os
import urllib.request
import urllib.error

# モデル名（2026-06時点）。config.yaml の llm.model で上書き可。
#   gemini-2.5-flash-lite … 低コスト・無料枠大（ただし2026/10/16終了予定）
#   gemini-3.1-flash-lite … 現行世代の低コスト後継（長寿命）
#   gemini-3.5-flash      … 現行主力（高性能・高コスト）
# 終了予定: gemini-2.0系は終了済、2.5系は2026/10/16終了予定。
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"
CLAUDE_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# LLMに補完してほしい項目だけを依頼（正規表現で確実なものは上書きしない方針）
PROMPT_TEMPLATE = """あなたは日本の懸賞情報を構造化するアシスタントです。
次の懸賞テキストから情報を抽出し、JSONのみを出力してください。説明文は不要です。

抽出項目（不明な項目は null）:
- genre: 次のいずれか ["現金","金券","食品","日用品","旅行","家電","その他"]
- method: 次のいずれか ["クローズド","レシート","アンケート","即時当選","instagram","x","はがき","メール","ネット","不明"]
- win_count: 当選本数（整数。「総額」しか書かれず本数不明なら null）
- prize_value: 賞品1点の概算金額（円・整数。「総額○円」÷本数や相場から推定可、不明なら null）
- manual_lottery: 後日抽選/担当者選考なら true、その場で当たる(即時当選)なら false、不明なら null
- local: 地域限定・店舗限定・在住者限定なら true、そうでなければ false
- organizer: 主催者名（企業/自治体名。不明なら ""）

懸賞テキスト:
タイトル: {title}
本文: {summary}

JSON:"""


def _http_post(url, headers, payload, timeout=20):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _parse_json_block(text):
    """LLM出力からJSON部分を取り出す。```json ... ``` も許容。"""
    t = text.strip()
    if "```" in t:
        t = t.split("```")[1]
        if t.startswith("json"):
            t = t[4:]
    t = t.strip()
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1:
        t = t[start:end + 1]
    return json.loads(t)


def _call_gemini(title, summary, api_key, model=DEFAULT_GEMINI_MODEL):
    prompt = PROMPT_TEMPLATE.format(title=title, summary=summary[:1000])
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    url = f"{GEMINI_BASE}{model}:generateContent"
    res = _http_post(url, headers, payload)
    text = res["candidates"][0]["content"]["parts"][0]["text"]
    return _parse_json_block(text)


def _call_claude(title, summary, api_key):
    prompt = PROMPT_TEMPLATE.format(title=title, summary=summary[:1000])
    payload = {
        "model": CLAUDE_MODEL, "max_tokens": 400, "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {"Content-Type": "application/json", "x-api-key": api_key,
               "anthropic-version": "2023-06-01"}
    res = _http_post(CLAUDE_URL, headers, payload)
    text = res["content"][0]["text"]
    return _parse_json_block(text)


# 正規表現の結果を上書きしてよい項目（LLMが得意な曖昧領域）
LLM_FILLABLE = ["genre", "method", "win_count", "prize_value",
                "manual_lottery", "local", "organizer"]


def _cache_path(cfg):
    return (cfg.get("llm", {}) or {}).get("cache_file", "llm_cache.json")


def _load_cache(path):
    try:
        if os.path.exists(path):
            return json.load(open(path, encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_cache(path, cache):
    try:
        json.dump(cache, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


def _content_key(title, summary):
    import hashlib
    return hashlib.sha1((title + "\u0001" + (summary or "")).encode("utf-8")).hexdigest()[:16]


def enrich(item, cfg=None, summary=""):
    """
    正規表現抽出結果 item を LLM で補完して返す。
    - 同一内容（title+summary）はキャッシュ(llm_cache.json)を使い、LLMを再呼び出ししない（G）
    - 正規表現が None/空 の項目のみ LLM 値で埋める（確実な抽出を尊重）
    - LLM未使用・失敗時は item をそのまま返す
    """
    cfg = cfg or {}
    llm_cfg = cfg.get("llm", {})
    provider = os.environ.get("LLM_PROVIDER", llm_cfg.get("provider", "none"))
    if provider == "none":
        return item

    title = item.get("title", "")
    ckey = _content_key(title, summary)
    cpath = _cache_path(cfg)
    cache = _load_cache(cpath)

    if ckey in cache:
        llm = cache[ckey]
        item["llm_status"] = "cache"
    else:
        try:
            if provider == "gemini":
                key = os.environ.get("GEMINI_API_KEY")
                if not key:
                    return item
                model = llm_cfg.get("model", DEFAULT_GEMINI_MODEL)
                llm = _call_gemini(title, summary, key, model)
            elif provider == "claude":
                key = os.environ.get("ANTHROPIC_API_KEY")
                if not key:
                    return item
                llm = _call_claude(title, summary, key)
            else:
                return item
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError,
                ValueError, json.JSONDecodeError, IndexError):
            item["llm_status"] = "failed"
            return item
        # 成功結果のみキャッシュ（必要な項目だけ）
        cache[ckey] = {k: llm.get(k) for k in LLM_FILLABLE}
        _save_cache(cpath, cache)
        llm = cache[ckey]
        item["llm_status"] = "ok"

    for k in LLM_FILLABLE:
        cur = item.get(k)
        new = llm.get(k)
        is_empty = cur is None or cur == "" or cur == "不明" or cur == "その他"
        if is_empty and new not in (None, "", "不明"):
            item[k] = new
    return item
