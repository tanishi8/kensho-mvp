"""
SNS ワンタップ導線の生成（規約遵守・凍結回避の範囲）。

方針（PROJECT_MEMORY 2/3 の不変原則）:
  - API による自動RT/自動フォロー/自動いいねは行わない（規約違反・凍結リスク）。
  - アプリからは「該当投稿・アカウントをワンタップで開く」導線だけを提供し、
    RT/フォロー/投稿の最終操作は人間が1タップで行う。
  - あわせて LLM で肉付けしたコメント案をコピーできるようにする。

ここでは各懸賞から、開くべきURL（intent）と、コメント欄がある場合のヒントを組み立てる。
"""
from urllib.parse import quote


def build(item):
    """item から SNS 導線情報を返す。

    返り値 dict:
      platform: "x" | "instagram" | "web" | "none"
      label:    ボタン表示名
      open_url: タップで開くURL（アプリ/ブラウザが起動）
      action:   人間が行う操作の説明（例: リポスト＆フォロー）
    """
    method = (item.get("method") or "").lower()
    link = item.get("link") or item.get("resolved_url") or ""
    title = item.get("title") or ""

    if method == "x":
        # X（旧Twitter）: 元投稿を開いて人間がRT/フォロー。
        # 元投稿URLが link に入っていればそれを開く。無ければ検索で開く。
        if "twitter.com" in link or "x.com" in link:
            open_url = link
        else:
            # キャンペーン名で検索して該当ポストへ誘導
            open_url = "https://x.com/search?q=" + quote(title[:50]) + "&f=live"
        return {
            "platform": "x",
            "label": "Xで開く（RT/フォロー）",
            "open_url": open_url,
            "action": "元投稿を開き、あなたが1タップでリポスト＆フォロー",
        }

    if method == "instagram":
        if "instagram.com" in link:
            open_url = link
        else:
            open_url = "https://www.instagram.com/explore/tags/" + quote(title[:30])
        return {
            "platform": "instagram",
            "label": "Instagramで開く（フォロー/投稿）",
            "open_url": open_url,
            "action": "投稿を開き、あなたがフォロー／規定ハッシュタグで投稿",
        }

    # それ以外は応募ページを開くだけ
    if link:
        return {
            "platform": "web",
            "label": "応募ページを開く",
            "open_url": link,
            "action": "応募フォーム/ページを開く",
        }
    return {"platform": "none", "label": "", "open_url": "", "action": ""}
