import os
import glob
import re
import getpass
import socket
import uuid
import hashlib

def get_client_identity():
    """
    非侵入式身分識別引擎：
    1. 優先從本地 Discord / DiscordPTB / DiscordCanary 的 LevelDB 快取中提取使用者資訊
       - 包含：顯示名稱 (Display Name / global_name)、使用者名稱 (username)、Discord Snowflake ID
    2. 自動擷取 Windows 設備硬體指紋 (Device UID / Hostname / Username)
    3. 組合成標準化身分標籤，提供錯誤報告與回饋使用。
    """
    discord_info = {
        "display_name": None,
        "username": None,
        "user_id": None,
        "avatar_url": None
    }
    
    discord_dirs = [
        os.path.expandvars(r"%APPDATA%\discord\Local Storage\leveldb"),
        os.path.expandvars(r"%APPDATA%\discordptb\Local Storage\leveldb"),
        os.path.expandvars(r"%APPDATA%\discordcanary\Local Storage\leveldb")
    ]
    
    for d in discord_dirs:
        if not os.path.exists(d):
            continue
        try:
            for ext in ("*.ldb", "*.log"):
                for fpath in glob.glob(os.path.join(d, ext)):
                    try:
                        with open(fpath, "rb") as f:
                            raw = f.read().decode("utf-8", errors="ignore")
                            
                            # 1. 搜尋主要帳號狀態 (含 id 與 username)
                            if not discord_info["username"] or not discord_info["user_id"]:
                                user_match = re.search(r'\{"id":"(\d{17,19})"[^}]*?"username":"([^"]+)"', raw)
                                if user_match:
                                    discord_info["user_id"] = user_match.group(1)
                                    discord_info["username"] = user_match.group(2)
                            
                            # 2. 搜尋顯示名稱 (displayName / global_name)
                            if not discord_info["display_name"]:
                                disp_match = re.search(r'"displayName":"([^"]+)"', raw)
                                if disp_match:
                                    discord_info["display_name"] = disp_match.group(1)
                                else:
                                    glob_match = re.search(r'"global_name":"([^"]+)"', raw)
                                    if glob_match:
                                        discord_info["display_name"] = glob_match.group(1)
                            
                            # 3. 搜尋頭像 Hash
                            if not discord_info["avatar_url"] and discord_info["user_id"]:
                                av_match = re.search(rf'/avatars/{discord_info["user_id"]}/([a-zA-Z0-9_]+)\.png', raw)
                                if av_match:
                                    discord_info["avatar_url"] = f"https://cdn.discordapp.com/avatars/{discord_info['user_id']}/{av_match.group(1)}.png"
                    except Exception:
                        pass
        except Exception:
            pass

    # Windows 設備指紋 (Device Fingerprint)
    pc_user = getpass.getuser()
    pc_host = socket.gethostname()
    node_id = hex(uuid.getnode())
    device_uid = hashlib.sha256(f"{pc_user}-{pc_host}-{node_id}".encode()).hexdigest()[:8].upper()
    
    # 決定最終識別標籤 (Display Label)
    # 優先順序：顯示名稱 (JiaSai) > 使用者名稱 (xiaoan0000) > Windows 使用者
    display_title = discord_info["display_name"] or discord_info["username"] or pc_user
    sub_tag = f"@{discord_info['username']}" if discord_info["username"] else f"PC: {pc_user}@{pc_host}"
    
    return {
        "display_name": discord_info["display_name"] or discord_info["username"] or "未知使用者",
        "username": discord_info["username"] or "N/A",
        "user_id": discord_info["user_id"] or "N/A",
        "avatar_url": discord_info["avatar_url"],
        "pc_user": pc_user,
        "pc_host": pc_host,
        "device_uid": device_uid,
        "formatted_identity": f"{display_title} ({sub_tag} | #{device_uid})"
    }

if __name__ == "__main__":
    import pprint
    pprint.pprint(get_client_identity())
