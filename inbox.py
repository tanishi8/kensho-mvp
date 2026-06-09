"""
メール受信（IMAP）モジュール（設計書 5.5）。当選通知の取り込み用。
- Gmail等のIMAPから未読メールを取得し、fraud_check向けの notice 辞書に変換
- 認証は環境変数: IMAP_HOST / IMAP_USER / IMAP_PASS（Gmailはアプリパスワード）
- Authentication-Results ヘッダから SPF/DKIM/DMARC を抽出
- ネットワーク不可・未設定でも import エラーにしない（遅延接続）
"""
import os
import re
import email
from email.header import decode_header


def _decode(s):
    if not s:
        return ""
    parts = decode_header(s)
    out = ""
    for txt, enc in parts:
        if isinstance(txt, bytes):
            out += txt.decode(enc or "utf-8", errors="replace")
        else:
            out += txt
    return out


def _parse_auth(raw_headers):
    """Authentication-Results から spf/dkim/dmarc を抽出。"""
    auth = {}
    for key in ("spf", "dkim", "dmarc"):
        m = re.search(rf"{key}=(\w+)", raw_headers, re.IGNORECASE)
        if m:
            auth[key] = m.group(1).lower()
    return auth


def _body_text(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace")
                except Exception:
                    pass
        return ""
    try:
        return msg.get_payload(decode=True).decode(
            msg.get_content_charset() or "utf-8", errors="replace")
    except Exception:
        return msg.get_payload() or ""


def to_notice(msg):
    """email.message.Message → fraud_check用 notice 辞書。"""
    from_hdr = _decode(msg.get("From", ""))
    m = re.search(r"<?([\w.\-+]+@[\w.\-]+)>?", from_hdr)
    addr = m.group(1) if m else ""
    domain = addr.split("@")[-1] if "@" in addr else ""
    display = re.sub(r"<.*?>", "", from_hdr).strip().strip('"')
    auth_raw = " ".join(msg.get_all("Authentication-Results", []))
    return {
        "channel": "mail",
        "sender_id": addr,
        "sender_domain": domain,
        "display_name": display,
        "subject": _decode(msg.get("Subject", "")),
        "body": _body_text(msg),
        "auth": _parse_auth(auth_raw),
        "campaign": _decode(msg.get("Subject", "")),
        "organizer": display,
    }


def fetch_unread(limit=50, mark_seen=False):
    """未読メールを notice のリストで返す。IMAP情報が無ければ空リスト。"""
    host = os.environ.get("IMAP_HOST")
    user = os.environ.get("IMAP_USER")
    pw = os.environ.get("IMAP_PASS")
    if not all([host, user, pw]):
        return []
    import imaplib
    notices = []
    M = imaplib.IMAP4_SSL(host)
    try:
        M.login(user, pw)
        M.select("INBOX")
        typ, data = M.search(None, "UNSEEN")
        ids = data[0].split()[:limit]
        for i in ids:
            fetch_flag = "(RFC822)" if mark_seen else "(BODY.PEEK[])"
            typ, msg_data = M.fetch(i, fetch_flag)
            raw = msg_data[0][1]
            notices.append(to_notice(email.message_from_bytes(raw)))
    finally:
        M.logout()
    return notices
