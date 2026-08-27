import os
import sys
import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime
import urllib.request
import threading
import shutil
import re
import traceback
import importlib.metadata
try:
    from core.theme_utils import get_theme_colors
except ModuleNotFoundError:
    from theme_utils import get_theme_colors

try:
    from core.identity_manager import get_client_identity
except ModuleNotFoundError:
    from identity_manager import get_client_identity

VERSION = "1.0.45"

if not os.path.basename(sys.executable).lower().startswith("python"):
    PYTHON_CMD = "python"
else:
    PYTHON_CMD = sys.executable

APPDATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "config")
ENV_CACHE_FILE = os.path.join(APPDATA_DIR, "env_cache.json")
REGISTRY_FILE = os.path.join(APPDATA_DIR, "registry.json")
CLOUD_TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CloudTools")
DISCORD_WEBHOOK_URL = "https://ptb.discord.com/api/webhooks/1540376553479999560/BlC_i3U0dEDp_qDVD9JlSxdkEpBw6-b9WGuuXa-xf4wE-EL6ob_ZmYNZ0EUR3RHwzXCl"

def send_discord_report(title, log_body, color=0xE74C3C, is_error=True, sync=False):
    """
    全自動 Discord Webhook 回報引擎
    1. 支援大頭貼與顯示名稱呈現
    2. 全資訊整合至統一程式碼塊 (One-Click Copy for Agent)
    3. 自動分段 (Multi-message Chunks) 避免超過 Discord 2000 字元上限
    4. 支援同步 (sync=True) 確保致命崩潰退出前 100% 成功發出
    """
    def _task():
        try:
            identity = get_client_identity()
            sender_name = identity['display_name']
            avatar = identity.get("avatar_url") or "https://raw.githubusercontent.com/JiaSai67/AIToolLauncher/main/resources/icon.png"
            author_tag = f"{identity['display_name']} (@{identity['username']})" if identity['username'] != "N/A" else identity['formatted_identity']
            
            MAX_CHUNK = 1700
            chunks = []
            if len(log_body) <= MAX_CHUNK:
                chunks = [log_body]
            else:
                for i in range(0, len(log_body), MAX_CHUNK):
                    chunks.append(log_body[i:i+MAX_CHUNK])
                    
            total_parts = len(chunks)
            for idx, chunk in enumerate(chunks):
                part_suffix = f" (第 {idx+1}/{total_parts} 頁)" if total_parts > 1 else ""
                
                embed_obj = {
                    "author": {
                        "name": author_tag,
                        "icon_url": avatar
                    },
                    "title": f"{title}{part_suffix}",
                    "description": f"```text\n{chunk.strip()}\n```",
                    "color": color,
                    "thumbnail": {
                        "url": avatar
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "footer": {"text": f"AIToolLauncher v{VERSION} 監控防護"}
                }
                
                payload = {
                    "username": sender_name,
                    "avatar_url": avatar,
                    "embeds": [embed_obj]
                }
                
                req = urllib.request.Request(
                    DISCORD_WEBHOOK_URL,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
                )
                urllib.request.urlopen(req, timeout=8)
        except Exception:
            pass
            
    if sync:
        _task()
    else:
        threading.Thread(target=_task, daemon=True).start()

def global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    大廳主程序全域未捕捉異常攔截器
    當 AIToolLauncher 本身發生崩潰時，100% 同步發送錯誤日誌至 Discord Webhook
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
        
    tb_lines = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    report_body = f"""[AIToolLauncher 大廳主程式崩潰日誌]
專案名稱: AIToolLauncher (主啟動器)
執行版本: v{VERSION}
執行檔案: {os.path.abspath(__file__)}
工作目錄: {os.getcwd()}
發生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

-------------------- 完整崩潰日誌 (Traceback) --------------------
{tb_lines.strip()}"""

    send_discord_report(
        title="💥 大廳核心崩潰：AIToolLauncher 發生未預期異常",
        log_body=report_body,
        color=0xE74C3C,
        is_error=True,
        sync=True
    )
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = global_exception_handler
if hasattr(threading, 'excepthook'):
    def thread_exception_handler(args):
        global_exception_handler(args.exc_type, args.exc_value, args.exc_traceback)
    threading.excepthook = thread_exception_handler

os.makedirs(APPDATA_DIR, exist_ok=True)
os.makedirs(CLOUD_TOOLS_DIR, exist_ok=True)



class EnvironmentManager:
    def __init__(self):
        self.installed_packages = {}
        self.refresh()
        
    def refresh(self):
        try:
            self.installed_packages = {dist.metadata['Name'].lower(): dist.version for dist in importlib.metadata.distributions()}
        except Exception:
            pass
            
    def needs_install_content(self, content):
        missing = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'): continue
            
            match = re.match(r'^([a-zA-Z0-9_\-]+)', line)
            if match:
                pkg_name = match.group(1).lower()
                if pkg_name not in self.installed_packages:
                    missing.append(pkg_name)
                    continue
                if '==' in line:
                    required_version = line.split('==')[1].strip()
                    if self.installed_packages.get(pkg_name) != required_version:
                        missing.append(f"{pkg_name}=={required_version}")
        return missing

    def needs_install(self, req_path):
        try:
            with open(req_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                # 處理 PowerShell 產生之 UTF-16 檔案
                with open(req_path, 'r', encoding='utf-16') as f:
                    content = f.read()
                # 強制轉換回 UTF-8 覆寫，避免 pip install 失敗
                with open(req_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception:
                return ["unknown_error"]
        except Exception:
            return ["unknown_error"]
            
        return self.needs_install_content(content)

class EnvCacheManager:
    def __init__(self, env_mgr):
        self.env_mgr = env_mgr
        self.cache_file = ENV_CACHE_FILE
        self.cache = self.load()
        
    def load(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {}
        
    def save(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=4)
            
    def check_local(self, req_path):
        if not os.path.exists(req_path):
            return "no_req", []
            
        current_mtime = os.path.getmtime(req_path)
        cache_key = f"local_{req_path}"
        
        if cache_key in self.cache and self.cache[cache_key].get("mtime") == current_mtime:
            return self.cache[cache_key]["status"], self.cache[cache_key].get("missing", [])
            
        missing = self.env_mgr.needs_install(req_path)
        status = "needs_install" if missing else "ready"
        
        self.cache[cache_key] = {"mtime": current_mtime, "status": status, "missing": missing}
        self.save()
        return status, missing
        
    def check_cloud_async(self, repo, callback):
        cache_key = f"cloud_{repo['full_name']}"
        updated_at = repo.get('pushed_at', repo.get('updated_at'))
        
        if cache_key in self.cache and self.cache[cache_key].get("updated_at") == updated_at:
            callback(self.cache[cache_key]["status"])
            return
            
        def fetch():
            try:
                branch = repo.get('default_branch', 'main')
                raw_url = f"https://raw.githubusercontent.com/{repo['full_name']}/{branch}/requirements.txt"
                req = urllib.request.Request(raw_url)
                with urllib.request.urlopen(req) as response:
                    content = response.read().decode('utf-8')
                
                needs = self.env_mgr.needs_install_content(content)
                status = "needs_install" if needs else "ready"
            except urllib.error.HTTPError as e:
                status = "no_req" if e.code == 404 else "error"
            except Exception:
                status = "error"
                
            self.cache[cache_key] = {"updated_at": updated_at, "status": status}
            self.save()
            callback(status)
            
        threading.Thread(target=fetch, daemon=True).start()

def load_registry():
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for t in data.get("tools", []):
                    if "CloudTools" in t.get("working_dir", ""):
                        repo_name = os.path.basename(t["working_dir"])
                        new_cwd = os.path.join(CLOUD_TOOLS_DIR, repo_name)
                        t["executable"] = t.get("executable", "").replace(t["working_dir"], new_cwd)
                        t["working_dir"] = new_cwd
                return data
        except Exception: pass
    return {"tools": []}

def save_registry(data):
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class ToolLauncherApp(tk.Tk):
    def __init__(self):
        try:
            import ctypes
            myappid = 'ai.tool.launcher.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception: pass
            
        super().__init__()
        self.title(f"AI Tool Launcher (AI專案啟動器) v{VERSION}")
        self.geometry("900x650")
        self.colors = get_theme_colors()
        self.configure(bg=self.colors.bg_root)
        
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "icon.png")
        if os.path.exists(icon_path):
            try:
                img = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, img)
            except Exception: pass

        self.registry = load_registry()
        self.running_processes = {}
        self.updates_available = {}
        self.env_manager = EnvironmentManager()
        self.env_cache = EnvCacheManager(self.env_manager)
        
        self.after(1000, self.async_check_all_updates)
        self.after(2000, self.check_launcher_update)
        
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TFrame", background=self.colors.bg_root, borderwidth=0, lightcolor=self.colors.bg_root, darkcolor=self.colors.bg_root, bordercolor=self.colors.bg_root)
        style.configure("TLabel", background=self.colors.bg_root, foreground=self.colors.text_main, font=('Microsoft JhengHei', 10), lightcolor=self.colors.bg_root, darkcolor=self.colors.bg_root, bordercolor=self.colors.bg_root)
        style.configure("Title.TLabel", font=('Microsoft JhengHei', 16, 'bold'), foreground=self.colors.text_title)
        style.configure("TButton", font=('Microsoft JhengHei', 10), padding=5, background=self.colors.bg_card, foreground=self.colors.text_main, borderwidth=1, bordercolor=self.colors.bg_root, lightcolor=self.colors.bg_card, darkcolor=self.colors.bg_card)
        style.map("TButton", background=[('active', self.colors.select_bg)], foreground=[('active', 'white')])
        style.configure("Launch.TButton", font=('Microsoft JhengHei', 12, 'bold'), background=self.colors.success, foreground="white")
        style.configure("Stop.TButton", font=('Microsoft JhengHei', 12, 'bold'), background=self.colors.error, foreground="white")
        style.configure("Restart.TButton", font=('Microsoft JhengHei', 12, 'bold'), background="#f39c12", foreground="white")
        style.configure("Cloud.TButton", font=('Microsoft JhengHei', 12, 'bold'), background=self.colors.select_bg, foreground="white")
        
        # Notebook styling
        style.configure("TNotebook", background=self.colors.bg_root, borderwidth=0, lightcolor=self.colors.bg_root, darkcolor=self.colors.bg_root, bordercolor=self.colors.bg_root)
        style.configure("TNotebook.Tab", background=self.colors.bg_card, foreground=self.colors.text_main, padding=[15, 5], font=('Microsoft JhengHei', 10), borderwidth=0, lightcolor=self.colors.bg_root, darkcolor=self.colors.bg_root, bordercolor=self.colors.bg_root)
        style.map("TNotebook.Tab", background=[('selected', self.colors.bg_root)], foreground=[('selected', self.colors.text_title)])
        
        # Radiobutton styling
        style.configure("TRadiobutton", background=self.colors.bg_root, foreground=self.colors.text_main, font=('Microsoft JhengHei', 10))
        style.map("TRadiobutton", background=[('active', self.colors.bg_root)], indicatorcolor=[('selected', self.colors.select_bg), ('!selected', self.colors.bg_card)])
        
        # Launcher Update Frame (Hidden by default)
        self.launcher_update_frame = ttk.Frame(self)
        self.btn_update_launcher = ttk.Button(self.launcher_update_frame, text="✨ 啟動器有新版本，點擊更新", style="Cloud.TButton", command=self.do_launcher_update)
        self.btn_update_launcher.pack(fill=tk.X, padx=10, pady=(10, 0))
        
        # Main Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.tab_local = ttk.Frame(self.notebook)
        self.tab_cloud = ttk.Frame(self.notebook)
        self.tab_env = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_local, text='💻 本地專案')
        self.notebook.add(self.tab_cloud, text='☁️ GitHub 雲端專案')
        self.notebook.add(self.tab_env, text='⚙️ 環境報告')
        
        self.setup_local_tab()
        self.setup_cloud_tab()
        self.setup_env_tab()
        
    def set_status_message(self, text, color=None):
        self.status_var.set(text)
        if hasattr(self, 'lbl_status'):
            fg = color if color else self.colors.text_main
            self.lbl_status.configure(foreground=fg)
        
    def check_launcher_update(self):
        def task():
            try:
                flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                local = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=cwd, creationflags=flags, text=True).strip()
                remote_out = subprocess.check_output(["git", "ls-remote", "origin", "-h", "refs/heads/main"], cwd=cwd, creationflags=flags, text=True).strip()
                if remote_out:
                    remote = remote_out.split()[0]
                    if local and remote and local != remote:
                        self.after(0, lambda: self.launcher_update_frame.pack(fill=tk.X, before=self.notebook))
            except: pass
        threading.Thread(target=task, daemon=True).start()
        
    def do_launcher_update(self):
        self.btn_update_launcher.config(text="⏳ 正在更新啟動器...", state=tk.DISABLED)
        def task():
            try:
                flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                p = subprocess.Popen(["git", "pull"], cwd=cwd, creationflags=flags, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
                p.wait()
                if p.returncode == 0:
                    self.after(0, self.launcher_update_frame.pack_forget)
                    self.after(0, self.restart_launcher)
                else:
                    self.after(0, lambda: messagebox.showerror("更新失敗", "無法自動更新啟動器，請檢查網路連線或手動執行 git pull。"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("更新錯誤", str(e)))
            finally:
                self.after(0, lambda: self.btn_update_launcher.config(text="✨ 啟動器有新版本，點擊更新", state=tk.NORMAL))
        threading.Thread(target=task, daemon=True).start()

    def restart_launcher(self):
        import tempfile
        bat_path = os.path.join(tempfile.gettempdir(), "restart_launcher.bat")
        cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(bat_path, "w", encoding="utf-8") as f:
            launcher_cmd = PYTHON_CMD
            if launcher_cmd.lower().endswith("python.exe"):
                launcher_cmd = launcher_cmd[:-10] + "pythonw.exe"
            elif launcher_cmd.lower() == "python":
                launcher_cmd = "pythonw"
                
            f.write("@echo off\n")
            f.write("timeout /t 1 /nobreak >nul\n")
            f.write(f"cd /d \"{cwd}\"\n")
            f.write(f"start \"\" \"{launcher_cmd}\" core\\launcher.py\n")
            f.write("del \"%~f0\"\n")
        subprocess.Popen([bat_path], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000))
        self.destroy()
        sys.exit(0)
        
    def async_check_all_updates(self):
        def check_all():
            cloud_prefix = os.path.abspath(CLOUD_TOOLS_DIR)
            for t in self.registry.get("tools", []):
                cwd = t.get("working_dir")
                name = t.get("name")
                
                # 只有存放在 CloudTools 目錄下的專案才檢查更新
                if not os.path.abspath(cwd).startswith(cloud_prefix):
                    continue
                    
                git_dir = os.path.join(cwd, ".git")
                if os.path.exists(git_dir):
                    try:
                        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                        subprocess.run(["git", "fetch"], cwd=cwd, creationflags=flags, timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        local = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=cwd, creationflags=flags, text=True).strip()
                        remote = subprocess.check_output(["git", "rev-parse", "@{u}"], cwd=cwd, creationflags=flags, text=True).strip()
                        if local and remote and local != remote:
                            self.updates_available[name] = True
                            self.after(0, self.refresh_action_buttons)
                    except: pass
        threading.Thread(target=check_all, daemon=True).start()

    def update_tool(self, name):
        tool = next((t for t in self.registry["tools"] if t["name"] == name), None)
        if not tool: return
        cwd = tool.get("working_dir")
        
        was_running = name in self.running_processes
        if was_running:
            self.stop_tool(name)
            
        self.status_var.set(f"狀態: ⏳ 正在更新 {name}...")
        for w in self.action_frame.winfo_children(): w.state(['disabled'])
        
        def pull_task():
            try:
                flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                p = subprocess.Popen(["git", "pull"], cwd=cwd, creationflags=flags, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
                for line in p.stdout:
                    l = line.strip()
                    if l: self.after(0, lambda text=l[:50]: self.status_var.set(f"狀態: 🔄 {text}"))
                p.wait()
                if p.returncode == 0:
                    self.updates_available[name] = False
                    
                    # 更新後順便檢查並自動補齊套件
                    req_path = os.path.join(cwd, "requirements.txt")
                    if os.path.exists(req_path):
                        self.after(0, lambda: self.status_var.set("狀態: ⏳ 正在檢查是否有新套件需要安裝..."))
                        status, _ = self.env_cache.check_local(req_path)
                        if status == "needs_install":
                            self.after(0, lambda: self.status_var.set("狀態: 📦 正在自動安裝新套件..."))
                            pip_cmd = PYTHON_CMD.lower().replace("pythonw.exe", "python.exe") if "pythonw.exe" in PYTHON_CMD.lower() else "python"
                            
                            pip_log_path = os.path.join(cwd, "pip_install.log")
                            with open(pip_log_path, "w", encoding="utf-8") as log_file:
                                p_install = subprocess.run([pip_cmd, "-m", "pip", "install", "-r", req_path], cwd=cwd, creationflags=flags, stdout=log_file, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
                                if p_install.returncode != 0:
                                    log_file.write("\n[Fallback] 批量安裝失敗，啟動逐行安裝模式...\n")
                                    try:
                                        with open(req_path, 'r', encoding='utf-8') as f: lines = f.readlines()
                                        for req_line in lines:
                                            req_line = req_line.strip()
                                            if not req_line or req_line.startswith('#'): continue
                                            subprocess.run([pip_cmd, "-m", "pip", "install", req_line], cwd=cwd, creationflags=flags, stdout=log_file, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
                                    except Exception as e:
                                        log_file.write(f"\n[Fallback Error] {e}\n")
                            
                            self.env_manager.refresh()
                            self.after(0, self.update_env_tab)
                            self.env_cache.check_local(req_path)
                            
                    if was_running:
                        self.after(0, lambda: self.status_var.set("狀態: 🟢 更新與套件補齊完成！正在自動重啟..."))
                        self.after(0, lambda: self.launch_tool(name))
                    else:
                        self.after(0, lambda: self.status_var.set("狀態: 🟢 更新與套件補齊完成！可以啟動專案了。"))
                else:
                    self.after(0, lambda: self.status_var.set("狀態: 🔴 更新失敗 (請檢查網路或衝突)"))
            except Exception as e:
                self.after(0, lambda: self.status_var.set(f"狀態: 🔴 更新錯誤: {e}"))
            finally:
                self.after(0, self.refresh_action_buttons)
                
        threading.Thread(target=pull_task, daemon=True).start()

    def setup_local_tab(self):
        left_frame = ttk.Frame(self.tab_local)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        ttk.Label(left_frame, text="已註冊的 AI 專案", font=('Microsoft JhengHei', 12, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        self.listbox = tk.Listbox(left_frame, width=30, font=('Microsoft JhengHei', 11), bg=self.colors.bg_card, fg=self.colors.text_main, selectbackground=self.colors.select_bg, relief=tk.FLAT, borderwidth=0, highlightthickness=1, highlightbackground=self.colors.bg_root, highlightcolor=self.colors.bg_root)
        self.listbox.pack(fill=tk.Y, expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.on_select_local)
        
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="🔄 重新安裝", command=self.reinstall_tool).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(btn_frame, text="🗑 刪除專案", command=self.delete_tool).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
        self.right_frame = ttk.Frame(self.tab_local)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.lbl_name = ttk.Label(self.right_frame, text="請在左側選擇一個專案來查看細節", style="Title.TLabel")
        self.lbl_name.pack(anchor=tk.W, pady=(0, 10))
        
        self.lbl_desc = tk.Label(self.right_frame, text="", bg=self.colors.bg_root, fg=self.colors.text_dim, font=('Microsoft JhengHei', 10), justify=tk.LEFT, wraplength=480)
        self.lbl_desc.pack(anchor=tk.W, pady=(0, 20))
        
        self.action_frame = ttk.Frame(self.right_frame)
        self.action_frame.pack(fill=tk.X, pady=(10, 20))
        
        self.status_var = tk.StringVar(value="狀態: 待命")
        self.lbl_status = ttk.Label(self.right_frame, textvariable=self.status_var, font=('Microsoft JhengHei', 10, 'bold'))
        self.lbl_status.pack(anchor=tk.W, pady=(0, 20))
        
        tk.Frame(self.right_frame, bg=self.colors.border, height=1).pack(fill=tk.X, pady=10)
        
        self.feedback_container = ttk.Frame(self.right_frame)
        self.feedback_container.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(self.feedback_container, text="💬 快速意見回饋 (將針對此專案提交)", font=('Microsoft JhengHei', 11, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        type_frame = ttk.Frame(self.feedback_container)
        type_frame.pack(fill=tk.X, pady=(0, 5))
        self.feedback_type_var = tk.StringVar(value="BUG")
        ttk.Radiobutton(type_frame, text="🐛 BUG回報", variable=self.feedback_type_var, value="BUG").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(type_frame, text="💡 功能建議", variable=self.feedback_type_var, value="建議").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(type_frame, text="🤔 其他", variable=self.feedback_type_var, value="其他").pack(side=tk.LEFT)
        
        self.local_feedback_text = tk.Text(self.feedback_container, font=('Microsoft JhengHei', 10), height=5, relief=tk.FLAT, bg=self.colors.bg_card, fg=self.colors.text_main, insertbackground=self.colors.text_main, bd=0, highlightthickness=1, highlightbackground=self.colors.border, highlightcolor=self.colors.select_bg)
        self.local_feedback_text.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        fb_btn_frame = ttk.Frame(self.feedback_container)
        fb_btn_frame.pack(fill=tk.X)
        
        self.local_feedback_status = ttk.Label(fb_btn_frame, text="", font=('Microsoft JhengHei', 9), foreground=self.colors.success)
        self.local_feedback_status.pack(side=tk.LEFT)
        
        ttk.Button(fb_btn_frame, text="🚀 送出回饋", command=self.submit_local_feedback).pack(side=tk.RIGHT)
        
        self.refresh_list()

    def setup_cloud_tab(self):
        left_frame = ttk.Frame(self.tab_cloud)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        header_frame = ttk.Frame(left_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header_frame, text="JiaSai 小工具倉庫", font=('Microsoft JhengHei', 12, 'bold')).pack(side=tk.LEFT)
        
        self.cloud_filter_var = tk.StringVar(value="uninstalled")
        ttk.Radiobutton(header_frame, text="全部", variable=self.cloud_filter_var, value="all", command=self.update_cloud_listbox).pack(side=tk.RIGHT)
        ttk.Radiobutton(header_frame, text="未安裝", variable=self.cloud_filter_var, value="uninstalled", command=self.update_cloud_listbox).pack(side=tk.RIGHT, padx=(0, 5))
        self.cloud_listbox = tk.Listbox(left_frame, width=30, font=('Microsoft JhengHei', 11), bg=self.colors.bg_card, fg=self.colors.text_main, selectbackground=self.colors.select_bg, relief=tk.FLAT, borderwidth=0, highlightthickness=1, highlightbackground=self.colors.bg_root, highlightcolor=self.colors.bg_root)
        self.cloud_listbox.pack(fill=tk.Y, expand=True)
        self.cloud_listbox.bind('<<ListboxSelect>>', self.on_select_cloud)
        
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="🔄 重新整理", command=self.fetch_cloud_repos).pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        self.cloud_right_frame = ttk.Frame(self.tab_cloud)
        self.cloud_right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.lbl_cloud_name = ttk.Label(self.cloud_right_frame, text="正在讀取 GitHub 倉庫...", style="Title.TLabel")
        self.lbl_cloud_name.pack(anchor=tk.W, pady=(0, 10))
        
        self.lbl_cloud_desc = tk.Label(self.cloud_right_frame, text="", bg=self.colors.bg_root, fg=self.colors.text_dim, font=('Microsoft JhengHei', 10), justify=tk.LEFT, wraplength=480)
        self.lbl_cloud_desc.pack(anchor=tk.W, pady=(0, 20))
        
        self.cloud_action_frame = ttk.Frame(self.cloud_right_frame)
        self.cloud_action_frame.pack(fill=tk.X, pady=(10, 20))
        
        self.cloud_status_var = tk.StringVar(value="狀態: 待命")
        ttk.Label(self.cloud_right_frame, textvariable=self.cloud_status_var, font=('Microsoft JhengHei', 10, 'bold')).pack(anchor=tk.W)
        
        self.cloud_repos = []
        self.fetch_cloud_repos()

    def setup_env_tab(self):
        frame = ttk.Frame(self.tab_env)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="系統 Python 環境報告", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 10))
        
        info_frame = ttk.Frame(frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        identity = get_client_identity()
        user_disp = f"{identity['display_name']} (@{identity['username']})" if identity['username'] != "N/A" else identity['formatted_identity']
        ttk.Label(info_frame, text="客戶端身分:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(info_frame, text=f"👤 {user_disp}  [硬體碼: #{identity['device_uid']}]", foreground=self.colors.link).grid(row=0, column=1, sticky=tk.W, padx=10)
        
        ttk.Label(info_frame, text="Python 路徑:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(info_frame, text=sys.executable, foreground=self.colors.text_dim).grid(row=1, column=1, sticky=tk.W, padx=10)
        
        ttk.Label(info_frame, text="Python 版本:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(info_frame, text=sys.version.split(' ')[0], foreground=self.colors.text_dim).grid(row=2, column=1, sticky=tk.W, padx=10)
        
        ttk.Button(info_frame, text="🔄 重新掃描", command=self.update_env_tab).grid(row=0, column=2, rowspan=3, padx=20)
        
        ttk.Button(frame, text="💀 終極自爆：清除 Python 與 Git 環境", style="Stop.TButton", command=self.nuke_environment).pack(anchor=tk.E, pady=(0, 10))
        
        ttk.Label(frame, text="目前已安裝的套件 (避免啟動時重複安裝):").pack(anchor=tk.W, pady=(10, 5))
        
        self.env_text = tk.Text(frame, height=20, bg=self.colors.bg_card, fg=self.colors.text_main, insertbackground=self.colors.text_main, font=('Consolas', 11), state=tk.DISABLED, bd=0, highlightthickness=1, highlightbackground=self.colors.bg_root, highlightcolor=self.colors.bg_root)
        self.env_text.pack(fill=tk.BOTH, expand=True)
        
        self.update_env_tab()

    def nuke_environment(self):
        confirm = messagebox.askyesno("💀 終極自爆確認", "【警告】此操作將徹底清除系統中的所有開發環境！\n\n包含：\n1. 解除安裝所有版本的 Python 與 Git (支援 winget、官方 uninstaller、註冊表搜尋)\n2. 清除所有 Python pip 快取、套件庫、全域設定檔\n3. 清除 AIToolLauncher 所有快取與設定檔\n4. 清理系統 PATH 環境變數中的 Python/Git 殘留路徑\n\n執行後，本啟動器會立刻強制退出。\n\n確定要徹底自爆清除嗎？")
        if not confirm: return
        
        import tempfile
        import sys
        
        python_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        python_exe = sys.executable
        python_dir = os.path.dirname(python_exe)
        python_uninstaller = os.path.join(python_dir, "Uninstall.exe")
        
        bat_path = os.path.join(tempfile.gettempdir(), "nuke_env.bat")
        
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write("@echo off\n")
            f.write("chcp 65001 >nul\n")
            f.write("title [NUKE] 正在徹底清除 Python 與 Git 環境...\n")
            f.write("echo ========================================================\n")
            f.write("echo              [NUKE] 終極自爆環境清理程式\n")
            f.write("echo ========================================================\n")
            f.write("echo.\n")
            f.write("echo [1/6] 正在等待 Launcher 進程釋放...\n")
            f.write("timeout /t 3 /nobreak >nul\n")
            f.write("echo.\n")
            
            # 1. 終結殘留進程
            f.write("echo [2/6] 強制終結所有 Python 與 Git 殘留進程...\n")
            f.write("taskkill /F /IM python.exe /T >nul 2>&1\n")
            f.write("taskkill /F /IM pythonw.exe /T >nul 2>&1\n")
            f.write("taskkill /F /IM git.exe /T >nul 2>&1\n")
            f.write("echo 殘留進程已終結。\n")
            f.write("echo.\n")
            
            # 2. 解除安裝 Git
            f.write("echo [3/6] 正在解除安裝 Git...\n")
            f.write("winget uninstall Git.Git --silent >nul 2>&1\n")
            f.write("if exist \"%ProgramFiles%\\Git\\unins000.exe\" (\n")
            f.write("    echo 正在呼叫 Git 官方反安裝程式...\n")
            f.write("    \"%ProgramFiles%\\Git\\unins000.exe\" /VERYSILENT /NORESTART /SUPPRESSMSGBOXES\n")
            f.write(")\n")
            f.write("if exist \"%ProgramFiles(x86)%\\Git\\unins000.exe\" (\n")
            f.write("    \"%ProgramFiles(x86)%\\Git\\unins000.exe\" /VERYSILENT /NORESTART /SUPPRESSMSGBOXES\n")
            f.write(")\n")
            f.write("if exist \"%LOCALAPPDATA%\\Programs\\Git\\unins000.exe\" (\n")
            f.write("    \"%LOCALAPPDATA%\\Programs\\Git\\unins000.exe\" /VERYSILENT /NORESTART /SUPPRESSMSGBOXES\n")
            f.write(")\n")
            f.write("powershell -Command \"Get-Package -Name '*Git*' -ErrorAction SilentlyContinue | Uninstall-Package -Force -ErrorAction SilentlyContinue\" >nul 2>&1\n")
            f.write("echo Git 解除安裝程序完成。\n")
            f.write("echo.\n")
            
            # 3. 解除安裝 Python
            f.write("echo [4/6] 正在解除安裝 Python...\n")
            f.write(f"winget uninstall Python.Python.{python_ver} --silent >nul 2>&1\n")
            f.write("powershell -Command \"Get-Package -Name '*Python*' -ErrorAction SilentlyContinue | Uninstall-Package -Force -ErrorAction SilentlyContinue\" >nul 2>&1\n")
            f.write("powershell -Command \"Get-CimInstance Win32_Product -Filter \\\"Name like 'Python%'\\\" -ErrorAction SilentlyContinue | ForEach-Object { $_.Uninstall() }\" >nul 2>&1\n")
            f.write("echo Python 解除安裝程序完成。\n")
            f.write("echo.\n")
            
            # 4. 清理殘留資料夾與快取 (pip cache, appdata, registry config)
            f.write("echo [5/6] 正在清除所有 Python/Git/Pip/大廳 設定與快取資料夾...\n")
            f.write("rmdir /s /q \"%LOCALAPPDATA%\\pip\" >nul 2>&1\n")
            f.write("rmdir /s /q \"%LOCALAPPDATA%\\Programs\\Python\" >nul 2>&1\n")
            f.write("rmdir /s /q \"%LOCALAPPDATA%\\Programs\\Git\" >nul 2>&1\n")
            f.write("rmdir /s /q \"%APPDATA%\\Python\" >nul 2>&1\n")
            f.write("rmdir /s /q \"%USERPROFILE%\\.gitconfig\" >nul 2>&1\n")
            f.write("del /f /q \"%USERPROFILE%\\.gitconfig\" >nul 2>&1\n")
            f.write("rmdir /s /q \"%ProgramFiles%\\Git\" >nul 2>&1\n")
            f.write(f"rmdir /s /q \"{APPDATA_DIR}\" >nul 2>&1\n")
            f.write("echo 快取與殘留目錄已全數清除。\n")
            f.write("echo.\n")
            
            # 5. 清理環境變數 PATH
            f.write("echo [6/6] 正在清理系統與使用者環境變數 PATH 殘留路徑...\n")
            f.write("powershell -Command \"$p = [Environment]::GetEnvironmentVariable('PATH', 'User'); $newP = ($p -split ';' | Where-Object { $_ -notlike '*Python*' -and $_ -notlike '*Git*' -and $_ -notlike '*pip*' }) -join ';'; [Environment]::SetEnvironmentVariable('PATH', $newP, 'User')\" >nul 2>&1\n")
            f.write("powershell -Command \"$p = [Environment]::GetEnvironmentVariable('PATH', 'Machine'); $newP = ($p -split ';' | Where-Object { $_ -notlike '*Python*' -and $_ -notlike '*Git*' -and $_ -notlike '*pip*' }) -join ';'; [Environment]::SetEnvironmentVariable('PATH', $newP, 'Machine')\" >nul 2>&1\n")
            f.write("echo PATH 清理完畢。\n")
            f.write("echo.\n")
            
            f.write("echo ========================================================\n")
            f.write("echo  💥 [NUKE 完成] Python、Git 與所有相關快取已徹底清除完畢！\n")
            f.write("echo  視窗將在 5 秒後自動關閉...\n")
            f.write("echo ========================================================\n")
            f.write("timeout /t 5 /nobreak >nul\n")
            f.write("del \"%~f0\" >nul 2>&1\n")
            f.write("exit\n")
            
        # 啟動終端機自爆腳本
        subprocess.Popen([bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        # 關閉自己
        self.destroy()
        sys.exit(0)

    def submit_local_feedback(self):
        selection = self.listbox.curselection()
        if not selection:
            return messagebox.showwarning("提示", "請先選擇一個專案再提交意見！")
            
        project_name = self.registry["tools"][selection[0]]["name"]
        fb_type = self.feedback_type_var.get()
        content = self.local_feedback_text.get("1.0", tk.END).strip()
        
        if not content:
            return messagebox.showwarning("提示", "請先輸入意見內容！")
            
        self.local_feedback_status.config(text="狀態: ⏳ 正在發送中...", foreground="#e67e22")
        self.local_feedback_text.config(state=tk.DISABLED)
        
        def send_task():
            try:
                type_colors = {
                    "BUG": 0xE74C3C,      # 紅色
                    "建議": 0x3498DB,     # 藍色
                    "其他": 0x9B59B6      # 紫色
                }
                type_emoji = {
                    "BUG": "🐛 BUG 回報",
                    "建議": "💡 功能建議",
                    "其他": "🤔 其他意見"
                }
                
                report_body = f"""[使用者意見回饋]
專案名稱: {project_name}
回饋類別: {type_emoji.get(fb_type, fb_type)}
發生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

-------------------- 回饋內容 --------------------
{content}"""
                
                send_discord_report(
                    title=f"📬 使用者意見回饋：{project_name} [{fb_type}]",
                    log_body=report_body,
                    color=type_colors.get(fb_type, 0x3498DB),
                    is_error=(fb_type == "BUG")
                )
                
                self.after(0, lambda: self.local_feedback_status.config(text=f"狀態: ✅ 已成功發送針對 [{project_name}] 的回饋！", foreground="#00CC6A"))
                self.after(0, lambda: self.local_feedback_text.delete("1.0", tk.END))
            except Exception as e:
                self.after(0, lambda: self.local_feedback_status.config(text=f"狀態: 🔴 發送失敗: {e}", foreground="#e74c3c"))
            finally:
                self.after(0, lambda: self.local_feedback_text.config(state=tk.NORMAL))
            
        threading.Thread(target=send_task, daemon=True).start()

    def update_env_tab(self):
        self.env_manager.refresh()
        self.env_text.config(state=tk.NORMAL)
        self.env_text.delete(1.0, tk.END)
        packages = [f"{pkg.ljust(35)} {ver}" for pkg, ver in sorted(self.env_manager.installed_packages.items())]
        self.env_text.insert(tk.END, "\n".join(packages))
        self.env_text.config(state=tk.DISABLED)

    # --- GitHub Logic ---
    def fetch_cloud_repos(self):
        self.cloud_listbox.delete(0, tk.END)
        self.lbl_cloud_name.config(text="正在連線至 GitHub...")
        self.cloud_status_var.set("狀態: ⏳ 正在抓取雲端倉庫清單...")
        
        def fetch():
            try:
                url = "https://api.github.com/users/JiaSai67/repos"
                req = urllib.request.Request(url)
                req.add_header("Accept", "application/vnd.github.v3+json")
                req.add_header("User-Agent", "AIToolLauncher")
                
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode('utf-8'))
                
                self.cloud_repos = [r for r in data if r['name'].lower() != 'aitoollauncher']
                self.after(0, self.update_cloud_listbox)
            except Exception as e:
                self.after(0, lambda: self.lbl_cloud_name.config(text="讀取失敗"))
                self.after(0, lambda: self.cloud_status_var.set(f"狀態: 🔴 無法連線至 GitHub: {e}"))
                
        threading.Thread(target=fetch, daemon=True).start()

    def update_cloud_listbox(self):
        self.cloud_listbox.delete(0, tk.END)
        filter_val = getattr(self, 'cloud_filter_var', tk.StringVar(value="all")).get()
        
        for repo in self.cloud_repos:
            if filter_val == "uninstalled" and os.path.exists(os.path.join(CLOUD_TOOLS_DIR, repo['name'])):
                continue
            self.cloud_listbox.insert(tk.END, repo['name'])
        self.lbl_cloud_name.config(text="請在左側選擇一個倉庫來安裝")
        self.cloud_status_var.set("狀態: 🟢 GitHub 倉庫抓取完畢")

    def on_select_cloud(self, event):
        selection = self.cloud_listbox.curselection()
        if not selection: return
        
        repo_name = self.cloud_listbox.get(selection[0])
        repo = next((r for r in self.cloud_repos if r['name'] == repo_name), None)
        if not repo: return
        
        self.lbl_cloud_name.config(text=repo['name'])
        self.lbl_cloud_desc.config(text=repo.get('description', '無描述'))
        for widget in self.cloud_action_frame.winfo_children(): widget.destroy()
            
        target_dir = os.path.join(CLOUD_TOOLS_DIR, repo['name'])
        is_installed = os.path.exists(target_dir) and os.path.exists(os.path.join(target_dir, ".git"))
        if is_installed:
            ttk.Button(self.cloud_action_frame, text="🔄 重新拉取 (git pull)", style="Cloud.TButton", command=lambda: self.update_cloud_repo(repo)).pack(side=tk.LEFT, padx=(0, 10))
            self.cloud_status_var.set("狀態: 🟢 此倉庫已安裝於本地")
        else:
            ttk.Button(self.cloud_action_frame, text="📥 下載並安裝 (git clone)", style="Launch.TButton", command=lambda: self.install_cloud_repo(repo)).pack(side=tk.LEFT)
            
            def cloud_cb(status):
                if status == "ready":
                    self.after(0, lambda: self.cloud_status_var.set("狀態: 🟢 可下載 (本地環境已相容，下載後可秒開)"))
                elif status == "needs_install":
                    self.after(0, lambda: self.cloud_status_var.set("狀態: 🟡 可下載 (包含新套件，啟動前將自動安裝)"))
                elif status == "no_req":
                    self.after(0, lambda: self.cloud_status_var.set("狀態: 🟢 可下載 (無 requirements.txt 依賴)"))
                else:
                    self.after(0, lambda: self.cloud_status_var.set("狀態: ⚪ 可下載 (無快取或檢查失敗)"))
                    
            self.cloud_status_var.set("狀態: 🔍 正在從雲端分析環境需求...")
            self.env_cache.check_cloud_async(repo, cloud_cb)

    def install_cloud_repo(self, repo):
        target_dir = os.path.join(CLOUD_TOOLS_DIR, repo['name'])
        clone_url = repo['clone_url']
        self.cloud_status_var.set(f"狀態: ⏳ 正在下載...")
        for w in self.cloud_action_frame.winfo_children(): w.state(['disabled'])
        
        def clone_task():
            log_lines = []
            try:
                flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                if os.path.exists(target_dir):
                    try:
                        shutil.rmtree(target_dir, ignore_errors=True)
                    except: pass
                    if os.path.exists(target_dir):
                        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", target_dir], creationflags=flags)
                        
                p = subprocess.Popen(["git", "clone", clone_url, target_dir], creationflags=flags, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
                for line in p.stdout:
                    l = line.strip()
                    log_lines.append(line)
                    if l: self.after(0, lambda text=l[:60]: self.cloud_status_var.set(f"狀態: 📥 下載中... {text}"))
                p.wait()
                
                full_log = "".join(log_lines)
                if p.returncode == 0:
                    self.after(0, lambda: self.auto_register_cloned_repo(repo, target_dir))
                else:
                    log_file_path = os.path.join(APPDATA_DIR, f"git_clone_error_{repo['name']}.log")
                    with open(log_file_path, "w", encoding="utf-8") as f:
                        f.write(full_log)
                    self.after(0, lambda: self.cloud_status_var.set(f"狀態: 🔴 下載失敗 (詳細紀錄已儲存至 log)"))
                    
                    # 📡 自動向 Discord Webhook 發送 Clone 失敗報告
                    report_body = f"""[Git Clone 失敗報告]
專案名稱: {repo['name']}
倉庫網址: {clone_url}
目標路徑: {target_dir}
發生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

-------------------- 完整日誌 --------------------
{full_log.strip()}"""
                    send_discord_report(
                        title=f"📥 Git Clone 失敗：{repo['name']}",
                        log_body=report_body,
                        color=0xE67E22,
                        is_error=True
                    )
                    
                    self.after(0, lambda: messagebox.showerror("下載失敗", f"Git Clone 失敗！\n\n錯誤訊息：\n{full_log[-400:]}\n\n完整日誌已儲存於：\n{log_file_path}"))
            except Exception as e:
                self.after(0, lambda: self.cloud_status_var.set(f"狀態: 🔴 下載失敗 (請確認已安裝 git): {e}"))
                report_body = f"""[Git Clone 例外異常]
專案名稱: {repo['name']}
倉庫網址: {clone_url}
異常訊息: {str(e)}
發生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                send_discord_report(
                    title=f"📥 Git Clone 例外異常：{repo['name']}",
                    log_body=report_body,
                    color=0xE74C3C
                )
                self.after(0, lambda: messagebox.showerror("下載失敗", f"下載過程發生未預期的異常：\n{e}"))
            finally:
                self.after(0, self.refresh_cloud_action_buttons)
        threading.Thread(target=clone_task, daemon=True).start()

    def update_cloud_repo(self, repo):
        target_dir = os.path.join(CLOUD_TOOLS_DIR, repo['name'])
        self.cloud_status_var.set(f"狀態: ⏳ 正在更新...")
        for w in self.cloud_action_frame.winfo_children(): w.state(['disabled'])
        
        def pull_task():
            log_lines = []
            try:
                flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                if not os.path.exists(os.path.join(target_dir, ".git")):
                    self.after(0, lambda: self.install_cloud_repo(repo))
                    return
                p = subprocess.Popen(["git", "pull"], cwd=target_dir, creationflags=flags, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
                for line in p.stdout:
                    l = line.strip()
                    log_lines.append(line)
                    if l: self.after(0, lambda text=l[:60]: self.cloud_status_var.set(f"狀態: 🔄 更新中... {text}"))
                p.wait()
                
                full_log = "".join(log_lines)
                if p.returncode == 0:
                    self.after(0, lambda: self.cloud_status_var.set(f"狀態: 🟢 更新成功"))
                    self.after(0, lambda: self.auto_register_cloned_repo(repo, target_dir))
                else:
                    log_file_path = os.path.join(APPDATA_DIR, f"git_pull_error_{repo['name']}.log")
                    with open(log_file_path, "w", encoding="utf-8") as f:
                        f.write(full_log)
                    self.after(0, lambda: self.cloud_status_var.set(f"狀態: 🔴 更新失敗 (詳細紀錄已儲存至 log)"))
                    
                    # 📡 自動向 Discord Webhook 發送 Pull 失敗報告
                    report_body = f"""[Git Pull 失敗報告]
專案名稱: {repo['name']}
本地路徑: {target_dir}
發生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

-------------------- 完整日誌 --------------------
{full_log.strip()}"""
                    send_discord_report(
                        title=f"🔄 Git Pull 失敗：{repo['name']}",
                        log_body=report_body,
                        color=0xE67E22,
                        is_error=True
                    )
                    
                    self.after(0, lambda: messagebox.showerror("更新失敗", f"Git Pull 失敗！\n\n錯誤訊息：\n{full_log[-400:]}\n\n完整日誌已儲存於：\n{log_file_path}"))
            except Exception as e:
                self.after(0, lambda: self.cloud_status_var.set(f"狀態: 🔴 更新失敗: {e}"))
                report_body = f"""[Git Pull 例外異常]
專案名稱: {repo['name']}
本地路徑: {target_dir}
異常訊息: {str(e)}
發生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                send_discord_report(
                    title=f"🔄 Git Pull 例外異常：{repo['name']}",
                    log_body=report_body,
                    color=0xE74C3C
                )
                self.after(0, lambda: messagebox.showerror("更新失敗", f"更新過程發生未預期的異常：\n{e}"))
            finally:
                self.after(0, self.refresh_cloud_action_buttons)
        threading.Thread(target=pull_task, daemon=True).start()

    def auto_register_cloned_repo(self, repo, target_dir):
        self.cloud_status_var.set("狀態: 🟢 下載完成，正在嘗試自動註冊...")
        
        name = repo['name']
        desc = repo.get('description', '')
        exec_file = None
        
        # 1. 如果有 linkme.bat，優先讀取裡面的設定
        linkme = os.path.join(target_dir, "linkme.bat")
        if os.path.exists(linkme):
            content = None
            try:
                with open(linkme, 'r', encoding='utf-8') as f: content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(linkme, 'r', encoding='big5') as f: content = f.read()
                except:
                    pass
                    
            if content:
                try:
                    name_match = re.search(r'set\s+PROJECT_NAME=(.+)', content)
                    desc_match = re.search(r'set\s+PROJECT_DESC=(.+)', content)
                    exec_match = re.search(r'set\s+EXEC_FILE=%CWD%\\(.+)', content)
                    
                    if name_match and exec_match:
                        name = name_match.group(1).strip()
                        if desc_match and not desc: desc = desc_match.group(1).strip()
                        exec_file = os.path.join(target_dir, exec_match.group(1).strip())
                except: pass
            
        # 2. 如果沒有 linkme.bat 或是讀取失敗，就尋找常見的啟動檔
        if not exec_file:
            exec_file = next((os.path.join(target_dir, c) for c in ["start.bat", "main.py", "app.py"] if os.path.exists(os.path.join(target_dir, c))), None)
            
        if not exec_file:
            messagebox.showinfo("手動註冊", "下載完成！但找不到標準的啟動檔 (如 start.bat 或 main.py)。\n請到「本地專案」分頁手動註冊。")
        else:
            self.registry["tools"] = [t for t in self.registry.get("tools", []) if t.get("name") != name]
            self.registry.setdefault("tools", []).append({
                "name": name, "description": desc, "executable": exec_file, "working_dir": target_dir
            })
            save_registry(self.registry)
            self.refresh_list()
            self.cloud_status_var.set(f"狀態: 🟢 下載並自動註冊成功！")
        self.refresh_cloud_action_buttons()

    # --- Local Tab Methods ---
    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for t in self.registry.get("tools", []): self.listbox.insert(tk.END, t.get("name", "Unknown"))

    def check_project_update_async(self, name, cwd):
        # 只有存放在 CloudTools 目錄下的專案才檢查更新
        cloud_prefix = os.path.abspath(CLOUD_TOOLS_DIR)
        if not os.path.abspath(cwd).startswith(cloud_prefix):
            return
            
        def check():
            git_dir = os.path.join(cwd, ".git")
            if os.path.exists(git_dir):
                try:
                    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                    subprocess.run(["git", "fetch"], cwd=cwd, creationflags=flags, timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    local = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=cwd, creationflags=flags, text=True).strip()
                    remote = subprocess.check_output(["git", "rev-parse", "@{u}"], cwd=cwd, creationflags=flags, text=True).strip()
                    if local and remote and local != remote:
                        self.updates_available[name] = True
                        
                        # Only refresh UI if the user is still looking at this project
                        selection = self.listbox.curselection()
                        if selection and self.registry["tools"][selection[0]]["name"] == name:
                            self.after(0, self.refresh_action_buttons)
                except: pass
        threading.Thread(target=check, daemon=True).start()

    def on_select_local(self, event):
        selection = self.listbox.curselection()
        if not selection: return
        index = selection[0]
        tool = self.registry["tools"][index]
        self.lbl_name.config(text=tool.get("name", ""))
        self.lbl_desc.config(text=tool.get("description", ""))
        
        cwd = tool.get("working_dir", "-")
        
        req_path = os.path.join(cwd, "requirements.txt")
        status, missing = self.env_cache.check_local(req_path)
        
        if status == "ready":
            self.status_var.set("狀態: 🟢 待命 (環境已相容，可秒開)")
        elif status == "needs_install":
            missing_str = ", ".join(missing[:3])
            if len(missing) > 3: missing_str += "..."
            self.status_var.set(f"狀態: ⚪ 待命 (啟動時將自動安裝: {missing_str})")
        elif status == "no_req":
            self.status_var.set("狀態: 🟢 待命 (無 requirements.txt 依賴)")
        else:
            self.status_var.set("狀態: 待命")
            
        self.refresh_action_buttons()
        self.check_project_update_async(tool.get("name"), cwd)
        
    def refresh_action_buttons(self):
        for widget in self.action_frame.winfo_children(): widget.destroy()
        selection = self.listbox.curselection()
        if not selection: return
        name = self.registry["tools"][selection[0]]["name"]
        
        if name in self.running_processes:
            ttk.Button(self.action_frame, text="🛑 關閉專案", style="Stop.TButton", command=lambda: self.stop_tool(name)).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(self.action_frame, text="🔄 重啟專案", style="Restart.TButton", command=lambda: self.restart_tool(name)).pack(side=tk.LEFT)
            if self.status_var.get().startswith("狀態: 待命"): self.status_var.set("狀態: 🟢 執行中")
        else:
            ttk.Button(self.action_frame, text="🚀 啟動此專案", style="Launch.TButton", command=lambda: self.launch_tool(name)).pack(side=tk.LEFT)
            if self.updates_available.get(name):
                ttk.Button(self.action_frame, text="🌟 版本更新", style="Cloud.TButton", command=lambda: self.update_tool(name)).pack(side=tk.LEFT, padx=(10, 0))
                
    def reinstall_tool(self):
        selection = self.listbox.curselection()
        if not selection: return messagebox.showwarning("警告", "請先選擇一個專案")
        index = selection[0]
        tool = self.registry["tools"][index]
        name = tool["name"]
        cwd = tool.get("working_dir")
        
        if not cwd or not os.path.exists(os.path.join(cwd, ".git")):
            return messagebox.showerror("錯誤", "此專案並非由 Git 倉庫下載 (找不到 .git)，無法使用重新安裝功能。")
            
        if not messagebox.askyesno("確認", f"確定要重新安裝 '{name}' 嗎？\n警告：這將會把整個專案資料夾刪除並重新從雲端下載！所有您未提交的修改都會消失！"):
            return
            
        self.stop_tool(name)
        
        def reinstall_task():
            self.after(0, lambda: self.status_var.set(f"狀態: ⏳ 正在取得遠端網址..."))
            try:
                flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                remote_url = subprocess.check_output(["git", "config", "--get", "remote.origin.url"], cwd=cwd, creationflags=flags, text=True).strip()
                if not remote_url:
                    self.after(0, lambda: messagebox.showerror("錯誤", "找不到 git remote url，無法重新安裝！"))
                    self.after(0, lambda: self.status_var.set(f"狀態: 🔴 重新安裝失敗"))
                    return
                    
                self.after(0, lambda: self.status_var.set(f"狀態: 🗑️ 正在刪除舊資料夾..."))
                parent_dir = os.path.dirname(cwd)
                folder_name = os.path.basename(cwd)
                
                # Windows shutil.rmtree ignores read-only files (like git objects), so we use rmdir /s /q
                subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", cwd], creationflags=flags)
                if os.path.exists(cwd):
                    self.after(0, lambda: messagebox.showerror("錯誤", "舊資料夾無法完全刪除，可能檔案正在被佔用。請手動刪除後再試。"))
                    return
                    
                self.after(0, lambda: self.status_var.set(f"狀態: 📥 正在重新下載 (clone)..."))
                p = subprocess.Popen(["git", "clone", remote_url, folder_name], cwd=parent_dir, creationflags=flags, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
                for line in p.stdout:
                    l = line.strip()
                    if l: self.after(0, lambda text=l[:50]: self.status_var.set(f"狀態: 🔄 {text}"))
                p.wait()
                
                if p.returncode == 0:
                    self.after(0, lambda: self.status_var.set("狀態: 🟢 重新安裝完成！可以啟動專案了。"))
                    self.after(0, self.refresh_action_buttons)
                else:
                    self.after(0, lambda: self.status_var.set("狀態: 🔴 重新安裝失敗 (請檢查網路連線)"))
            except Exception as e:
                self.after(0, lambda: self.status_var.set(f"狀態: 🔴 重新安裝錯誤: {e}"))
                
        threading.Thread(target=reinstall_task, daemon=True).start()
            
    def delete_tool(self):
        selection = self.listbox.curselection()
        if not selection: return messagebox.showwarning("警告", "請先選擇一個專案")
        index = selection[0]
        tool = self.registry["tools"][index]
        name = tool["name"]
        
        if messagebox.askyesno("確認", f"確定要徹底刪除 '{name}' 嗎？\n警告：這將會把整個專案資料夾從硬碟中移除！"):
            self.stop_tool(name)
            cwd = tool.get("working_dir")
            
            self.registry["tools"].pop(index)
            save_registry(self.registry)
            self.refresh_list()
            for widget in self.action_frame.winfo_children(): widget.destroy()
            self.lbl_name.config(text="請在左側選擇一個專案來查看細節")
            self.status_var.set("狀態: 待命")
            self.lbl_desc.config(text="")
            
            if cwd and os.path.isdir(cwd):
                try:
                    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", cwd], creationflags=flags)
                except Exception as e:
                    messagebox.showwarning("警告", f"移除檔案時發生錯誤，部分檔案可能仍留存: {e}")

    def launch_tool(self, name):
        tool = next((t for t in self.registry["tools"] if t["name"] == name), None)
        if not tool: return
        exec_path, cwd = tool.get("executable"), tool.get("working_dir")
        if not os.path.exists(exec_path): return messagebox.showerror("錯誤", f"找不到執行檔: {exec_path}")
            
        req_path = os.path.join(cwd, "requirements.txt")
        git_dir = os.path.join(cwd, ".git")
        
        def pre_launch_setup():
            flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
            try:
                status, _ = self.env_cache.check_local(req_path)
                if status == "needs_install":
                    self.after(0, lambda: self.status_var.set("狀態: ⏳ 準備執行 pip install..."))
                    
                    # 強制使用 python.exe 而非 pythonw.exe，否則 pip 的輸出和錯誤碼會被完全吞噬
                    pip_cmd = PYTHON_CMD.lower().replace("pythonw.exe", "python.exe") if "pythonw.exe" in PYTHON_CMD.lower() else "python"
                    
                    pip_log_path = os.path.join(cwd, "pip_install.log")
                    with open(pip_log_path, "w", encoding="utf-8") as log_file:
                        p = subprocess.Popen([pip_cmd, "-m", "pip", "install", "-r", req_path], cwd=cwd, creationflags=flags, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
                        for line in p.stdout:
                            l = line.strip()
                            log_file.write(line)
                            log_file.flush()
                            if l: self.after(0, lambda text=l[:50]: self.status_var.set(f"狀態: 📦 套件安裝中... {text}"))
                        p.wait()
                        
                        # 容錯機制：如果批量安裝失敗，則逐行安裝，確保好的套件不會被牽連
                        if p.returncode != 0:
                            log_file.write("\n[Fallback] 批量安裝失敗，啟動逐行安裝模式...\n")
                            try:
                                with open(req_path, 'r', encoding='utf-8') as f: lines = f.readlines()
                                for req_line in lines:
                                    req_line = req_line.strip()
                                    if not req_line or req_line.startswith('#'): continue
                                    self.after(0, lambda text=req_line: self.status_var.set(f"狀態: 📦 嘗試單獨安裝: {text}"))
                                    p_single = subprocess.Popen([pip_cmd, "-m", "pip", "install", req_line], cwd=cwd, creationflags=flags, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
                                    for l_single in p_single.stdout:
                                        log_file.write(l_single)
                                        log_file.flush()
                                    p_single.wait()
                            except Exception as e:
                                log_file.write(f"\n[Fallback Error] 逐行安裝過程發生錯誤: {e}\n")
                    
                    self.env_manager.refresh()
                    self.after(0, self.update_env_tab)
                    self.env_cache.check_local(req_path)
                    
                    if p.returncode != 0:
                        self.after(0, lambda: self.status_var.set(f"狀態: ⚠️ 部分套件安裝失敗，已盡力補齊 (詳見 pip_install.log)"))
                        
                        # 📡 自動向 Discord Webhook 發送依賴安裝失敗報告
                        try:
                            with open(pip_log_path, 'r', encoding='utf-8', errors='replace') as pf:
                                pip_full_err = pf.read().strip()
                        except:
                            pip_full_err = "無法讀取 pip_install.log"
                            
                        report_body = f"""[依賴套件安裝失敗報告]
專案名稱: {name}
依賴清單: {req_path}
工作目錄: {cwd}
發生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

-------------------- pip 安裝日誌 --------------------
{pip_full_err}"""
                        send_discord_report(
                            title=f"📦 依賴套件安裝異常：{name}",
                            log_body=report_body,
                            color=0xF39C12,
                            is_error=True
                        )
                        
                        self.after(0, lambda: messagebox.showwarning("套件安裝警告", f"部分套件安裝失敗（例如缺少系統依賴）。\n\n已啟動容錯機制，將跳過損壞的套件並強行補齊其他套件。\n若專案無法正常運作，請通知 xiaoan0000 (JiaSai) 對此錯誤進行排查。"))
                
                self.after(0, lambda: self._do_launch(name, exec_path, cwd))
            except Exception as e:
                self.after(0, lambda: self.set_status_message(f"狀態: 🔴 前置作業失敗 (請通知 xiaoan0000 (JiaSai) 進行排查): {e}", color="#FF4D4F"))
                
        threading.Thread(target=pre_launch_setup, daemon=True).start()

    def _do_launch(self, name, exec_path, cwd):
        try:
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
            
            # 強制子進程使用 UTF-8 輸出，避免 Windows 預設 CP950 導致中文字或 Emoji 編碼崩潰亂碼
            sub_env = os.environ.copy()
            sub_env["PYTHONIOENCODING"] = "utf-8"
            sub_env["PYTHONUTF8"] = "1"
            
            log_path = os.path.join(cwd, "launcher_error.log")
            log_file = open(log_path, "w", encoding="utf-8")
            
            if exec_path.endswith('.py') or exec_path.endswith('.pyw'):
                tool_cmd = PYTHON_CMD
                if tool_cmd.lower().endswith("python.exe"):
                    tool_cmd = tool_cmd[:-10] + "pythonw.exe"
                elif tool_cmd.lower() == "python":
                    tool_cmd = "pythonw"
                p = subprocess.Popen([tool_cmd, exec_path], cwd=cwd, env=sub_env, creationflags=flags, stdout=log_file, stderr=subprocess.STDOUT)
            else:
                p = subprocess.Popen([exec_path], cwd=cwd, env=sub_env, creationflags=flags, stdout=log_file, stderr=subprocess.STDOUT)
                
            self.running_processes[name] = p
            self.refresh_action_buttons()
            self.status_var.set(f"狀態: 🟢 已於 {datetime.now().strftime('%H:%M:%S')} 啟動 [{name}]")
            
            def wait_for_exit():
                p.wait()
                try: log_file.close()
                except: pass
                
                if name in self.running_processes and self.running_processes[name] == p:
                    del self.running_processes[name]
                    self.after(0, self.refresh_action_buttons)
                    
                    has_error = False
                    log_text = ""
                    if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
                        try:
                            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                                log_text = f.read().strip()
                                content = log_text.lower()
                                if "traceback" in content or "exception" in content or "error" in content:
                                    has_error = True
                        except: pass
                    
                    if has_error:
                        self.after(0, lambda: self.set_status_message(f"狀態: 🔴 [{name}] 異常關閉 (請通知 xiaoan0000 (JiaSai) 對此錯誤進行排查)", color="#FF4D4F"))
                        
                        # 📡 自動向 Discord Webhook 發送異常崩潰報告 (整合為一鍵複製代碼塊)
                        report_body = f"""[專案崩潰日誌報告]
專案名稱: {name}
執行檔案: {exec_path}
工作目錄: {cwd}
發生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

-------------------- 完整崩潰日誌 (Traceback) --------------------
{log_text}"""
                        send_discord_report(
                            title=f"💥 專案執行崩潰：{name}",
                            log_body=report_body,
                            color=0xE74C3C,
                            is_error=True
                        )
                    else:
                        self.after(0, lambda: self.set_status_message(f"狀態: ⚪ [{name}] 已關閉"))
                    
            threading.Thread(target=wait_for_exit, daemon=True).start()
            
        except Exception as e:
            self.set_status_message(f"狀態: 🔴 啟動失敗 ({e})", color="#FF4D4F")
            
    def stop_tool(self, name):
        if name in self.running_processes:
            p = self.running_processes[name]
            try: subprocess.Popen(['taskkill', '/PID', str(p.pid), '/T', '/F'], creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except: pass
            del self.running_processes[name]
            self.refresh_action_buttons()
            self.status_var.set(f"狀態: ⚪ 已強制關閉 [{name}]")

    def restart_tool(self, name):
        self.stop_tool(name)
        self.after(800, lambda: self.launch_tool(name))

if __name__ == "__main__":
    app = ToolLauncherApp()
    app.mainloop()
