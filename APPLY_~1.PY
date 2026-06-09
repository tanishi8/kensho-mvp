"""
メール応募（設計書 5.x / 2.1）。最も低リスクな自動応募。
- テンプレートにプロファイルを差し込み、指定アドレスへ送信
- dry_run=True なら送信せず内容を返す（既定。実送信は明示フラグが必要）
- SMTP情報は環境変数で渡す（SMTP_HOST/PORT/USER/PASS）
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr


def build_body(template, profile):
    """テンプレ内の {key} をプロファイル値で置換。"""
    body = template
    for k, v in profile.items():
        body = body.replace("{" + k + "}", str(v))
    return body


def send(to_addr, subject, template, profile, dry_run=True):
    """
    メール応募を送信。dry_run時は送信せず dict を返す。
    実送信には dry_run=False かつ SMTP_* 環境変数が必要。
    """
    body = build_body(template, profile)
    preview = {"to": to_addr, "subject": subject, "body": body, "sent": False}
    if dry_run:
        preview["note"] = "dry-run（未送信）"
        return preview

    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    pw = os.environ.get("SMTP_PASS")
    if not all([host, user, pw]):
        preview["note"] = "SMTP環境変数が未設定のため送信中止"
        return preview

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr((profile.get("last_name", "") + profile.get("first_name", ""), user))
    msg["To"] = to_addr
    with smtplib.SMTP(host, port, timeout=20) as s:
        s.starttls()
        s.login(user, pw)
        s.send_message(msg)
    preview["sent"] = True
    preview["note"] = "送信完了"
    return preview
