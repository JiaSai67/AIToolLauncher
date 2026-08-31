import os, sys, json, base64, urllib.request
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
    try:
        url = get_webhook_url()
        identity = get_client_identity()
        payload = {
            "username": identity["display_name"],
            "avatar_url": identity["avatar_url"],
            "embeds": [{
                "title": title,
                "description": f"```text\n{log_body.strip()}\n```",
                "color": color,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "footer": {"text": "AIToolLauncher 2.0 [收納盒模式]"}
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
