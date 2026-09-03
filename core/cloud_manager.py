import os, sys, json, subprocess, shutil, re, urllib.request, threading, stat, time
from datetime import datetime

try:
    from core.identity_manager import send_identity_webhook
except ModuleNotFoundError:
    from identity_manager import send_identity_webhook

GITHUB_REPOS_API = "https://api.github.com/users/JiaSai67/repos?per_page=100&sort=updated"

def get_silent_flags_and_startupinfo():
    """
    確保在 Windows 下執行所有 Git 與 Pip 指令時 100% 完全無黑窗閃現
    """
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
    return flags, startupinfo

def force_remove_directory(path: str):
    """
    100% 純 Python 記憶體原生刪除目錄與唯讀/.git屬性檔案，零進程生成，絕無任何終端視窗/白窗閃爍
    """
    if not os.path.exists(path):
        return

    def remove_readonly(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
            func(p)
        except Exception:
            pass

    # 1. 深度優先遍歷清除唯讀屬性並刪除檔案
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            fp = os.path.join(root, f)
            try:
                os.chmod(fp, stat.S_IWRITE | stat.S_IREAD)
                os.remove(fp)
            except Exception:
                pass
        for d in dirs:
            dp = os.path.join(root, d)
            try:
                os.chmod(dp, stat.S_IWRITE | stat.S_IREAD)
                os.rmdir(dp)
            except Exception:
                pass

    # 2. 最終目錄清除
    try:
        if os.path.exists(path):
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            shutil.rmtree(path, onerror=remove_readonly)
    except Exception:
        pass

def parse_linkme(target_dir: str) -> dict:
    """
    解析專案目錄下的 linkme.bat 獲取啟動資訊
    """
    linkme_path = os.path.join(target_dir, "linkme.bat")
    if not os.path.exists(linkme_path):
        return None

    content = ""
    for enc in ['utf-8', 'utf-8-sig', 'cp950', 'big5', 'gbk']:
        try:
            with open(linkme_path, 'r', encoding=enc) as f:
                content = f.read()
                break
        except Exception:
            continue

    if not content:
        return None

    name = None
    desc = ""
    exec_file = None

    m_name = re.search(r'set\s+"?PROJECT_NAME=([^"\r\n]+)"?', content, re.IGNORECASE)
    if m_name:
        name = m_name.group(1).strip()

    m_desc = re.search(r'set\s+"?PROJECT_DESC=([^"\r\n]+)"?', content, re.IGNORECASE)
    if m_desc:
        desc = m_desc.group(1).strip()

    m_exec = re.search(r'set\s+"?EXEC_FILE=(?:%CWD%\\|\.\/|\.\\|)([^"\r\n]+)"?', content, re.IGNORECASE)
    if m_exec:
        rel_exec = m_exec.group(1).strip()
        if os.path.isabs(rel_exec):
            exec_file = rel_exec
        else:
            exec_file = os.path.normpath(os.path.join(target_dir, rel_exec))

    return {
        "name": name,
        "description": desc,
        "executable": exec_file
    }

def fetch_github_repos(callback):
    """
    非同步從 GitHub API 獲取雲端倉庫列表 (含離線/限流備援)
    """
    def _fetch():
        fallback_repos = [
            {
                "name": "PTTApp",
                "description": "按鍵發話控制器 (PTTApp) - 語音通訊按鍵發話控制器",
                "clone_url": "https://github.com/JiaSai67/PTTApp.git",
                "html_url": "https://github.com/JiaSai67/PTTApp"
            },
            {
                "name": "SteamManifestUpdater",
                "description": "Steam Manifest Updater - Steam 清單自動更新工具",
                "clone_url": "https://github.com/JiaSai67/SteamManifestUpdater.git",
                "html_url": "https://github.com/JiaSai67/SteamManifestUpdater"
            },
            {
                "name": "xingshili",
                "description": "專屬計畫書 🌸 - 個人目標與排程規劃助手",
                "clone_url": "https://github.com/JiaSai67/xingshili.git",
                "html_url": "https://github.com/JiaSai67/xingshili"
            }
        ]
        try:
            req = urllib.request.Request(GITHUB_REPOS_API)
            req.add_header("Accept", "application/vnd.github.v3+json")
            req.add_header("User-Agent", "AIToolLauncher-2.0")

            with urllib.request.urlopen(req, timeout=8) as response:
                raw_data = response.read().decode('utf-8', errors='ignore')
                data = json.loads(raw_data)

            repos = [r for r in data if r.get('name', '').lower() != 'aitoollauncher']
            if repos:
                callback(True, repos)
            else:
                callback(True, fallback_repos)
        except Exception:
            callback(True, fallback_repos)

    threading.Thread(target=_fetch, daemon=True).start()

def get_cloud_icon_async(repo_name: str, cache_dir: str, on_icon_ready):
    """
    非同步獲取 GitHub 雲端專案的圖示並快取至本地 (若已快取則靜默略過，0 額外耗時)
    """
    if not repo_name:
        return
    os.makedirs(cache_dir, exist_ok=True)
    cached_file = os.path.join(cache_dir, f"{repo_name}.png")
    if os.path.exists(cached_file) and os.path.getsize(cached_file) > 0:
        return

    candidate_raw_urls = [
        f"https://raw.githubusercontent.com/JiaSai67/{repo_name}/main/icon/mic.png",
        f"https://raw.githubusercontent.com/JiaSai67/{repo_name}/main/assets/icon.png",
        f"https://raw.githubusercontent.com/JiaSai67/{repo_name}/main/assets/icon.ico",
        f"https://raw.githubusercontent.com/JiaSai67/{repo_name}/main/resources/icon.png",
        f"https://raw.githubusercontent.com/JiaSai67/{repo_name}/main/icon.png"
    ]

    def _task():
        for url in candidate_raw_urls:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'AIToolLauncher-2.0'})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    content = resp.read()
                    if len(content) > 0:
                        with open(cached_file, "wb") as f:
                            f.write(content)
                        on_icon_ready(cached_file)
                        return
            except Exception:
                continue

    threading.Thread(target=_task, daemon=True).start()

def install_cloud_repo_async(repo: dict, cloud_tools_dir: str, python_exe: str, on_finished, on_progress=None):
    """
    下載並安裝雲端小工具 (git clone + linkme.bat 註冊 + pip 安裝，100% 靜默無任何黑窗)
    """
    def _task():
        repo_name = repo.get('repo_name') or repo.get('name', '')
        clone_url = repo.get('clone_url', '') or f"https://github.com/JiaSai67/{repo_name}.git"
        target_dir = os.path.join(cloud_tools_dir, repo_name)
        flags, startupinfo = get_silent_flags_and_startupinfo()

        def _report(pct, msg):
            if on_progress:
                on_progress(pct, msg)

        try:
            _report(5, "正在連線 GitHub 倉庫...")
            os.makedirs(cloud_tools_dir, exist_ok=True)

            # 若目錄已存在，先嘗試清理或遷移，確保 git clone 順利執行
            if os.path.exists(target_dir):
                force_remove_directory(target_dir)
                if os.path.exists(target_dir):
                    # 若仍有被 Windows 鎖定的檔案殘留，自動遷移至暫存目錄
                    try:
                        trash_dir = os.path.join(cloud_tools_dir, f".trash_{repo_name}_{int(time.time())}")
                        os.rename(target_dir, trash_dir)
                        threading.Thread(target=lambda: force_remove_directory(trash_dir), daemon=True).start()
                    except Exception:
                        pass

            _report(15, "開始下載原始碼...")

            # 1. Git Clone (逐行讀取進度輸出，100% 靜默)
            p = subprocess.Popen(
                ["git", "clone", "--progress", clone_url, repo_name],
                cwd=cloud_tools_dir, creationflags=flags, startupinfo=startupinfo,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace'
            )
            
            for line in p.stdout:
                line_str = line.strip()
                m = re.search(r'(\d+)%', line_str)
                if m:
                    pct = int(m.group(1))
                    scaled = int(15 + pct * 0.55)
                    _report(scaled, f"下載中 {pct}%")
            p.wait(timeout=120)

            if p.returncode != 0:
                # 若 clone 失敗但目錄已具備 git，嘗試 fetch + reset
                if os.path.exists(os.path.join(target_dir, ".git")):
                    subprocess.run(["git", "fetch", "--all"], cwd=target_dir, creationflags=flags, startupinfo=startupinfo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=target_dir, creationflags=flags, startupinfo=startupinfo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    on_finished(False, f"Git clone 失敗 (代碼: {p.returncode})", None)
                    return

            _report(75, "解析專案啟動配置...")

            # 2. 解析 linkme.bat 或尋找 main.py / start.bat
            name = repo_name
            desc = repo.get('description') or ""
            exec_file = None

            info = parse_linkme(target_dir)
            if info:
                if info.get("name"): name = info["name"]
                if info.get("description"): desc = info["description"]
                if info.get("executable") and os.path.exists(info["executable"]):
                    exec_file = info["executable"]

            if not exec_file:
                for candidate in ["main.py", "start.bat", "app.py", "src/main.py"]:
                    cand_path = os.path.normpath(os.path.join(target_dir, candidate))
                    if os.path.exists(cand_path):
                        exec_file = cand_path
                        break

            if not exec_file:
                on_finished(False, "下載完成，但找不到標準啟動檔 (如 linkme.bat 或 main.py)", None)
                return

            _report(85, "正在檢查依賴環境...")

            # 3. 安裝 requirements.txt (100% 靜默)
            req_path = os.path.join(target_dir, "requirements.txt")
            if os.path.exists(req_path):
                _report(90, "正在安裝依賴套件...")
                pip_cmd = python_exe.lower().replace("pythonw.exe", "python.exe") if "pythonw.exe" in python_exe.lower() else python_exe
                subprocess.run(
                    [pip_cmd, "-m", "pip", "install", "-r", req_path],
                    cwd=target_dir, creationflags=flags, startupinfo=startupinfo,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=180
                )

            _report(100, "安裝完成！")

            tool_entry = {
                "name": name,
                "description": desc,
                "executable": exec_file,
                "working_dir": target_dir
            }

            send_identity_webhook(f"📥 成功下載小工具: {name}", f"倉庫: {clone_url}\n路徑: {exec_file}")
            on_finished(True, f"【{name}】已成功下載並註冊！", tool_entry)

        except Exception as e:
            send_identity_webhook(f"💥 下載小工具失敗: {repo_name}", str(e), color=0xFF0033)
            on_finished(False, str(e), None)

    threading.Thread(target=_task, daemon=True).start()

def reinstall_tool_async(tool_data: dict, python_exe: str, on_finished):
    """
    重新拉取與安裝已安裝的小工具 (git fetch + reset + linkme + pip，100% 靜默)
    """
    def _task():
        name = tool_data.get('name', '小工具')
        wdir = tool_data.get('working_dir', '')
        flags, startupinfo = get_silent_flags_and_startupinfo()

        if not os.path.exists(wdir):
            on_finished(False, f"找不到工作目錄: {wdir}", tool_data)
            return

        try:
            # 1. git fetch origin
            subprocess.run(["git", "fetch", "origin"], cwd=wdir, creationflags=flags, startupinfo=startupinfo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            
            # 2. git reset --hard origin/main
            p = subprocess.Popen(
                ["git", "reset", "--hard", "origin/main"],
                cwd=wdir, creationflags=flags, startupinfo=startupinfo,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace'
            )
            p.wait(timeout=30)

            if p.returncode != 0:
                p2 = subprocess.Popen(
                    ["git", "pull"],
                    cwd=wdir, creationflags=flags, startupinfo=startupinfo,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace'
                )
                p2.wait(timeout=30)

            # 3. 重新解析 linkme.bat
            info = parse_linkme(wdir)
            if info:
                if info.get("name"): tool_data["name"] = info["name"]
                if info.get("description"): tool_data["description"] = info["description"]
                if info.get("executable") and os.path.exists(info["executable"]):
                    tool_data["executable"] = info["executable"]

            # 4. 檢查 requirements.txt
            req_path = os.path.join(wdir, "requirements.txt")
            if os.path.exists(req_path):
                pip_cmd = python_exe.lower().replace("pythonw.exe", "python.exe") if "pythonw.exe" in python_exe.lower() else python_exe
                subprocess.run(
                    [pip_cmd, "-m", "pip", "install", "-r", req_path],
                    cwd=wdir, creationflags=flags, startupinfo=startupinfo,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=180
                )

            send_identity_webhook(f"🔄 重新拉取小工具: {name}", f"工作目錄: {wdir}")
            on_finished(True, f"【{name}】重新拉取與更新完成！", tool_data)

        except Exception as e:
            send_identity_webhook(f"💥 重新拉取失敗: {name}", str(e), color=0xFF0033)
            on_finished(False, str(e), tool_data)

    threading.Thread(target=_task, daemon=True).start()

def uninstall_tool(tool_data: dict, cloud_tools_dir: str) -> bool:
    """
    移除小工具：若位於 CloudTools 則刪除資料夾 (含 .git 屬性清除)
    """
    wdir = tool_data.get("working_dir", "")
    try:
        if wdir and os.path.exists(wdir):
            if os.path.abspath(wdir).startswith(os.path.abspath(cloud_tools_dir)):
                force_remove_directory(wdir)
        return True
    except Exception:
        return False
