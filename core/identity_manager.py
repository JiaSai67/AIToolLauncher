import os, sys, json, base64, urllib.request, threading, traceback
from datetime import datetime

_SECRET_KEY = b"AIToolLauncherSecretKey2026"
_ENCRYPTED_WEBHOOK_BLOB = b"KT0gHxxWY04FGgFGARsgBgwAAVooChQdUUJfbj4xDQcDIwoGQVJdUUJgUlVHUEd/UkALCQsDd3l7LQMvEwhGO1MMIDYjOhI2MzByLxVhSFZdBDkWGFlBLlgiKRYdPRN+HQVGEjFmIDUEX1BpGyQNITVcCTQnXTEgEggLJg8="

def get_webhook_url() -> str:
    raw = base64.b64decode(_ENCRYPTED_WEBHOOK_BLOB)
    return bytes([b ^ _SECRET_KEY[i % len(_SECRET_KEY)] for i, b in enumerate(raw)]).decode('utf-8')

def encrypt_webhook_url(raw_url: str) -> str:
    raw_bytes = raw_url.strip().encode('utf-8')
    encrypted = bytes([b ^ _SECRET_KEY[i % len(_SECRET_KEY)] for i, b in enumerate(raw_bytes)])
    return base64.b64encode(encrypted).decode('ascii')

def get_client_identity() -> dict:
    username = os.environ.get("USERNAME", "UnknownUser")
    return {
        "username": username,
        "display_name": username,
        "avatar_url": "https://raw.githubusercontent.com/JiaSai67/AIToolLauncher/main/resources/icon.png",
        "privilege_level": "Standard User"
    }

def send_identity_webhook(title: str, log_body: str, color: int = 0x9A70FF):
    """
    透過動態 XOR 解密的 Discord Webhook 發送通知與報錯
    """
    def _send():
        try:
            url = get_webhook_url()
            identity = get_client_identity()
            # Discord embed description max length is 4096
            clean_body = log_body.strip()
            if len(clean_body) > 3900:
                clean_body = clean_body[:3900] + "\n... (訊息已截斷)"

            payload = {
                "username": f"AIToolLauncher [{identity['display_name']}]",
                "avatar_url": identity["avatar_url"],
                "embeds": [{
                    "title": title,
                    "description": f"```text\n{clean_body}\n```",
                    "color": color,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "footer": {"text": "AIToolLauncher 2.0 守護日誌"}
                }]
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
            )
            urllib.request.urlopen(req, timeout=6)
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()

def install_global_exception_hook():
    """
    全域異常攔截器：攔截所有未捕捉的啟動或運行期崩潰，並透過加密 Webhook 自動推播
    """
    def global_excepthook(exc_type, exc_value, exc_tb):
        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        
        # 1. 寫入本地 log
        try:
            log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "launcher_error.log")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(err_msg)
        except Exception:
            pass

        # 2. 發送加密 Webhook 報錯推播 (紅色 0xFF0033)
        send_identity_webhook("💥 AIToolLauncher 2.0 發生未捕捉異常崩潰", err_msg, color=0xFF0033)

        # 3. 呼叫原始 excepthook
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = global_excepthook

    # Threading exception hook for Python 3.8+
    if hasattr(threading, "excepthook"):
        def thread_excepthook(args):
            err_msg = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
            send_identity_webhook(f"💥 背景線程異常 ({args.thread.name})", err_msg, color=0xFF0033)
        threading.excepthook = thread_excepthook
