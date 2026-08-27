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
       - 包含：顯示名稱 (Display Name / global_name)、使用者名稱 (username)、Discord Snowflake ID、最新頭像 Hash
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
        os.path.expandvars(r"%APPDATA%\discordptb\Local Storage\leveldb"),
        os.path.expandvars(r"%APPDATA%\discord\Local Storage\leveldb"),
        os.path.expandvars(r"%APPDATA%\discordcanary\Local Storage\leveldb")
    ]
    
    found_avatar_hashes = []
    
    for d in discord_dirs:
        if not os.path.exists(d):
            continue
        try:
            # 依檔案修改時間排序，優先讀取最新的 log/ldb
            files = glob.glob(os.path.join(d, "*.ldb")) + glob.glob(os.path.join(d, "*.log"))
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            for fpath in files:
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
                        
                        # 3. 搜尋頭像 patterns (32 位元 hex hash)
                        av_matches = re.findall(r'(\d{17,19})/([a-f0-9]{32})\.png', raw)
                        for uid, h in av_matches:
                            if h not in found_avatar_hashes:
                                found_avatar_hashes.append((uid, h))
                                
                        av_simple = re.findall(r'"avatar":"([a-f0-9]{32})"', raw)
                        for h in av_simple:
                            if (discord_info["user_id"], h) not in found_avatar_hashes:
                                found_avatar_hashes.append((discord_info["user_id"], h))
                except Exception:
                    pass
        except Exception:
            pass

    # 驗證並套用第一個找到的有效頭像 URL
    if found_avatar_hashes:
        for uid, h in found_avatar_hashes:
            target_uid = uid or discord_info["user_id"]
            if target_uid and h:
                discord_info["avatar_url"] = f"https://cdn.discordapp.com/avatars/{target_uid}/{h}.png"
                break

    # Windows 設備指紋 (Device Fingerprint)
    pc_user = getpass.getuser()
    pc_host = socket.gethostname()
    node_id = hex(uuid.getnode())
    device_uid = hashlib.sha256(f"{pc_user}-{pc_host}-{node_id}".encode()).hexdigest()[:8].upper()
    
    display_title = discord_info["display_name"] or discord_info["username"] or pc_user
    sub_tag = f"@{discord_info['username']}" if discord_info["username"] else f"PC: {pc_user}@{pc_host}"
    
    return {
        "display_name": discord_info["display_name"] or discord_info["username"] or pc_user,
        "username": discord_info["username"] or "N/A",
        "user_id": discord_info["user_id"] or "N/A",
        "avatar_url": discord_info["avatar_url"],
        "pc_user": pc_user,
        "pc_host": pc_host,
        "device_uid": device_uid,
        "formatted_identity": f"{display_title} ({sub_tag})"
    }

if __name__ == "__main__":
    import pprint
    pprint.pprint(get_client_identity())
