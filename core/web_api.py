# -*- coding: utf-8 -*-
"""
Web API Bridge for AIToolLauncher Next-Gen Modern Chromium (WebView2) GUI
完美橋接前端 HTML/CSS/JS 介面與後端強大的本機小工具管理、雲端商店、Git 版本更新與 Win32 原生無邊框控制。
"""

import os
import sys
import re
import json
import time
import shutil
import base64
import ctypes
from ctypes import wintypes
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

# 導入現有業務模組
_core_dir = Path(__file__).resolve().parent
_root_dir = _core_dir.parent
if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))
if str(_core_dir) not in sys.path:
    sys.path.insert(0, str(_core_dir))

try:
    from cloud_manager import (
        fetch_github_repos, install_cloud_repo_async, reinstall_tool_async,
        uninstall_tool as cm_uninstall_tool, parse_linkme, check_requirements_satisfied,
        get_silent_flags_and_startupinfo
    )
    from identity_manager import (
        get_client_identity, send_identity_webhook, get_webhook_url
    )
except ImportError:
    from core.cloud_manager import (
        fetch_github_repos, install_cloud_repo_async, reinstall_tool_async,
        uninstall_tool as cm_uninstall_tool, parse_linkme, check_requirements_satisfied,
        get_silent_flags_and_startupinfo
    )
    from core.identity_manager import (
        get_client_identity, send_identity_webhook, get_webhook_url
    )

VERSION = "2.1.0"


def format_card_title(raw_name: str) -> str:
    """
    智慧專案名稱排版與語義換行算法：
    1. 移除不自然的中間橫線（例如 'Steam Manifest - 本地開發版' -> 'Steam Manifest\\n本地開發版'）
    2. 智慧分離英文主名稱與中文功能/角色後綴
    3. 智慧分離括號後綴
    """
    if not raw_name:
        return "未命名"
    if "\n" in raw_name:
        return raw_name

    name = raw_name.strip()

    for sep in [" - ", " – ", " — ", "：", ": "]:
        if sep in name:
            parts = name.split(sep, 1)
            if parts[0].strip() and parts[1].strip():
                return f"{parts[0].strip()}\n{parts[1].strip()}"

    paren_match = re.match(r"^(.+?)\s*([（\(].+?[）\)])$", name)
    if paren_match:
        p1, p2 = paren_match.group(1).strip(), paren_match.group(2).strip()
        if p1 and p2:
            return f"{p1}\n{p2}"

    eng_chn_match = re.match(r"^([a-zA-Z0-9\s\.\-_]+?)\s+([\u4e00-\u9fa5]+.*)$", name)
    if eng_chn_match:
        p1, p2 = eng_chn_match.group(1).strip(), eng_chn_match.group(2).strip()
        if p1 and p2:
            return f"{p1}\n{p2}"

    chn_eng_match = re.match(r"^([\u4e00-\u9fa5\s]+?)\s+([a-zA-Z0-9\.\-_]+.*)$", name)
    if chn_eng_match:
        p1, p2 = chn_eng_match.group(1).strip(), chn_eng_match.group(2).strip()
        if p1 and p2:
            return f"{p1}\n{p2}"

    return name


def get_real_python_exe(prefer_gui: bool = True) -> str:
    """精準取得真實 Python 解譯器路徑，防止打包工具誤判"""
    env_exe = os.environ.get("TRUE_PYTHON_EXE", "")
    if env_exe and os.path.exists(env_exe) and not env_exe.lower().endswith("aitoollauncher.exe"):
        if prefer_gui and "python.exe" in env_exe.lower():
            cand = env_exe.lower().replace("python.exe", "pythonw.exe")
            if os.path.exists(cand):
                return cand
        elif not prefer_gui and "pythonw.exe" in env_exe.lower():
            cand = env_exe.lower().replace("pythonw.exe", "python.exe")
            if os.path.exists(cand):
                return cand
        return env_exe

    env_dir = os.environ.get("TRUE_PYTHON_DIR", "")
    if env_dir and os.path.isdir(env_dir):
        order = ["pythonw.exe", "python.exe"] if prefer_gui else ["python.exe", "pythonw.exe"]
        for cand in order:
            p = os.path.join(env_dir, cand)
            if os.path.exists(p):
                return p

    if sys.executable and not sys.executable.lower().endswith("aitoollauncher.exe"):
        exe = sys.executable
        if prefer_gui and "python.exe" in exe.lower():
            cand = exe.lower().replace("python.exe", "pythonw.exe")
            if os.path.exists(cand):
                return cand
        elif not prefer_gui and "pythonw.exe" in exe.lower():
            cand = exe.lower().replace("pythonw.exe", "python.exe")
            if os.path.exists(cand):
                return cand
        return exe

    order = ["pythonw", "python"] if prefer_gui else ["python", "pythonw"]
    for cand in order:
        p = shutil.which(cand)
        if p and not p.lower().endswith("aitoollauncher.exe"):
            return p

    return "pythonw" if prefer_gui else "python"


def is_pid_alive(pid: int) -> bool:
    """精準檢測 Windows 系統中 PID 是否處於活動狀態"""
    if not pid or pid <= 0:
        return False
    try:
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            exit_code = ctypes.c_ulong()
            success = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            ctypes.windll.kernel32.CloseHandle(handle)
            return bool(success and exit_code.value == STILL_ACTIVE)
    except Exception:
        pass
    return False


def bring_window_to_foreground(pid: int = None, title_hint: str = None) -> bool:
    """呼叫指定 PID 或標題的 Windows 視窗置頂"""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    found_hwnds = []

    def enum_cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True

        if pid:
            win_pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(win_pid))
            if win_pid.value == pid:
                found_hwnds.append(hwnd)
                return False

        if title_hint:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            clean_hint = re.sub(r'[^\w]', '', title_hint).lower()
            clean_title = re.sub(r'[^\w]', '', buff.value).lower()
            if clean_hint and clean_hint in clean_title:
                found_hwnds.append(hwnd)
                return False

        return True

    cb_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    user32.EnumWindows(cb_type(enum_cb), 0)

    if found_hwnds:
        hwnd = found_hwnds[0]
        cur_thread = kernel32.GetCurrentThreadId()
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)
        try:
            user32.AttachThreadInput(cur_thread, target_thread, True)
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
        finally:
            user32.AttachThreadInput(cur_thread, target_thread, False)
        return True
    return False


def is_local_tool_data(data: dict) -> bool:
    """精準判定專案是否為本地獨立專案"""
    if not data or not isinstance(data, dict):
        return False
    if data.get("is_local") is True:
        return True
    name = str(data.get("name", "")).strip()
    if "本地開發版" in name or "本地版" in name:
        return True
    wdir = str(data.get("working_dir", "")).strip()
    exe = str(data.get("executable", "")).strip()
    if wdir:
        if "cloudtools" not in os.path.normpath(wdir).lower():
            return True
    elif exe:
        if "cloudtools" not in os.path.normpath(exe).lower():
            return True
    return False


def file_to_base64_data_url(file_path: str) -> str:
    """讀取本地圖檔轉換為 base64 data URL"""
    if not file_path or not os.path.exists(file_path):
        return ""
    try:
        ext = os.path.splitext(file_path)[1].lower().strip(".")
        mime = "image/png"
        if ext in ["jpg", "jpeg"]:
            mime = "image/jpeg"
        elif ext == "gif":
            mime = "image/gif"
        elif ext == "webp":
            mime = "image/webp"
        elif ext in ["ico", "icon"]:
            mime = "image/x-icon"
        elif ext == "svg":
            mime = "image/svg+xml"

        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
            return f"data:{mime};base64,{encoded}"
    except Exception as e:
        print(f"[WebApi] file_to_base64_data_url error: {e}")
        return ""


class WebApi:
    """
    AIToolLauncher 前端與 Python 後端橋接 API 核心類別。
    包含 Win32 原生無邊框拖曳、進程管理、小工具啟動/終止、設定同步、雲端商店與更新。
    """
    def __init__(self, window=None):
        self._window = window
        self._root_dir = Path(__file__).resolve().parent.parent
        self._config_dir = self._root_dir / "resources" / "config"
        self._cloud_tools_dir = self._root_dir / "CloudTools"
        self._registry_file = self._config_dir / "registry.json"
        self._settings_file = self._config_dir / "v2_settings.json"
        self._logs_dir = self._root_dir / "resources" / "logs"
        self._logs_dir.mkdir(parents=True, exist_ok=True)

        # 運行中進程管理表: {tool_name: {"proc": proc, "pid": pid, "exe": exe, "log_path": log_path, "start_time": float}}
        self.running_processes: Dict[str, Dict[str, Any]] = {}
        # 啟動冷卻防連點字典
        self._launch_cooldowns: Dict[str, float] = {}
        # 快取視窗控制代碼
        self._cached_hwnd = 0

        # 背景動態更新檢測結果
        self.updates_cache: Dict[str, Dict[str, str]] = {}

    def set_window(self, window):
        self._window = window

    # ═══════════════════════════════════════════════════════
    # 1. 視窗控制與 Win32 原生硬體加速拖曳
    # ═══════════════════════════════════════════════════════
    def _get_hwnd(self) -> int:
        """取得主視窗 HWND 句柄 (支援快取與多層容錯探測)"""
        if self._cached_hwnd:
            try:
                if ctypes.windll.user32.IsWindow(self._cached_hwnd):
                    return self._cached_hwnd
            except Exception:
                pass

        hwnd = 0
        try:
            if self._window:
                native = getattr(self._window, "native", None) or getattr(self._window, "gui", None)
                if native and hasattr(native, "Handle"):
                    hwnd = int(native.Handle.ToInt64() if hasattr(native.Handle, "ToInt64") else native.Handle)
        except Exception:
            hwnd = 0

        if not hwnd:
            try:
                user32 = ctypes.windll.user32
                if self._window and getattr(self._window, "title", None):
                    hwnd = user32.FindWindowW(None, self._window.title)

                if not hwnd:
                    pid = os.getpid()
                    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                    def enum_cb(h, lp):
                        nonlocal hwnd
                        p = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(h, ctypes.byref(p))
                        if p.value == pid and user32.IsWindowVisible(h):
                            hwnd = h
                            return False
                        return True
                    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
            except Exception as e:
                print(f"[WebApi] _get_hwnd error: {e}")

        if hwnd:
            self._cached_hwnd = hwnd
        return hwnd

    def drag_window(self) -> bool:
        """觸發作業系統原生視窗拖曳 (Win32 SC_DRAGMOVE)，達到 0 延遲 144Hz+ 流暢拖曳"""
        try:
            user32 = ctypes.windll.user32
            hwnd = self._get_hwnd()
            if hwnd:
                user32.ReleaseCapture()
                # 0x0112 = WM_SYSCOMMAND, 0xF012 = SC_DRAGMOVE (SC_MOVE + HTCAPTION)
                user32.SendMessageW(hwnd, 0x0112, 0xF012, 0)
                return True
        except Exception as e:
            print(f"[WebApi] drag_window error: {e}")
        return False

    def start_resize(self, side: str) -> bool:
        """觸發作業系統原生無邊框視窗 8 方向邊緣縮放 (Win32 SC_SIZE)"""
        side_map = {
            "left": 0xF001,
            "right": 0xF002,
            "top": 0xF003,
            "top-left": 0xF004,
            "top-right": 0xF005,
            "bottom": 0xF006,
            "bottom-left": 0xF007,
            "bottom-right": 0xF008,
        }
        cmd = side_map.get(side)
        if not cmd:
            return False
        try:
            user32 = ctypes.windll.user32
            hwnd = self._get_hwnd()
            if hwnd:
                user32.ReleaseCapture()
                user32.SendMessageW(hwnd, 0x0112, cmd, 0)
                return True
        except Exception as e:
            print(f"[WebApi] start_resize error: {e}")
        return False

    def minimize_window(self) -> bool:
        """最小化視窗"""
        try:
            hwnd = self._get_hwnd()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
                return True
        except Exception:
            pass
        if self._window:
            self._window.minimize()
            return True
        return False

    def maximize_window(self) -> bool:
        """切換最大化 / 還原視窗"""
        try:
            hwnd = self._get_hwnd()
            if hwnd:
                user32 = ctypes.windll.user32
                if user32.IsZoomed(hwnd):
                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                else:
                    user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
                return True
        except Exception:
            pass
        if self._window:
            self._window.toggle_fullscreen()
            return True
        return False

    def is_maximized(self) -> bool:
        """檢查視窗是否處於最大化狀態"""
        try:
            hwnd = self._get_hwnd()
            if hwnd:
                return bool(ctypes.windll.user32.IsZoomed(hwnd))
        except Exception:
            pass
        return False

    def close_window(self) -> bool:
        """儲存尺寸並關閉主程式"""
        try:
            # 關閉前記錄視窗大小
            hwnd = self._get_hwnd()
            if hwnd:
                user32 = ctypes.windll.user32
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                is_max = bool(user32.IsZoomed(hwnd))
                cfg = self.get_settings()
                if not is_max and w > 400 and h > 300:
                    cfg["window_width"] = w
                    cfg["window_height"] = h
                cfg["window_is_maximized"] = is_max
                self.save_settings(cfg)
        except Exception as e:
            print(f"[WebApi] close_window save config warning: {e}")

        if self._window:
            self._window.destroy()
            return True
        sys.exit(0)
        return True

    def toggle_pin(self) -> bool:
        """切換視窗置頂狀態"""
        cfg = self.get_settings()
        is_top = not cfg.get("always_on_top", False)
        cfg["always_on_top"] = is_top
        self.save_settings(cfg)
        self.set_topmost(is_top)
        return is_top

    def set_topmost(self, is_top: bool) -> bool:
        """Win32 原生設置置頂"""
        try:
            hwnd = self._get_hwnd()
            if hwnd:
                HWND_TOPMOST = -1
                HWND_NOTOPMOST = -2
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOACTIVATE = 0x0010
                flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                ctypes.windll.user32.SetWindowPos(
                    hwnd,
                    HWND_TOPMOST if is_top else HWND_NOTOPMOST,
                    0, 0, 0, 0,
                    flags
                )
                return True
        except Exception as e:
            print(f"[WebApi] set_topmost error: {e}")
        return False

    # ═══════════════════════════════════════════════════════
    # 2. 設定管理 (Settings & Background)
    # ═══════════════════════════════════════════════════════
    def get_settings(self) -> Dict[str, Any]:
        """讀取 v2_settings.json 設定"""
        defaults = {
            "window_width": 1180,
            "window_height": 760,
            "window_is_maximized": False,
            "window_opacity": 96,
            "background_image_path": str(self._config_dir / "background.gif"),
            "background_opacity": 88,
            "background_blur": 20,
            "icon_size": 56,
            "theme_mode": "Auto",
            "always_on_top": False
        }
        if self._settings_file.exists():
            try:
                with open(self._settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    defaults.update(data)
            except Exception as e:
                print(f"[WebApi] load settings error: {e}")
        return defaults

    def save_settings(self, new_settings: Dict[str, Any]) -> bool:
        """寫入 v2_settings.json 設定"""
        try:
            current = self.get_settings()
            current.update(new_settings)
            self._config_dir.mkdir(parents=True, exist_ok=True)
            with open(self._settings_file, "w", encoding="utf-8") as f:
                json.dump(current, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"[WebApi] save settings error: {e}")
            return False

    def get_background_data_url(self) -> str:
        """回傳目前設定的背景圖片/GIF base64 data URL"""
        cfg = self.get_settings()
        bg_path = cfg.get("background_image_path", "")
        if not bg_path or not os.path.exists(bg_path):
            default_gif = str(self._config_dir / "background.gif")
            if os.path.exists(default_gif):
                bg_path = default_gif
            else:
                return ""
        return file_to_base64_data_url(bg_path)

    def select_background_file(self) -> Dict[str, Any]:
        """呼叫 Windows 原生檔案選擇對話框挑選自訂桌布/GIF"""
        try:
            import webview
            file_types = ("圖片檔案 (*.gif;*.png;*.jpg;*.jpeg;*.webp)", "所有檔案 (*.*)")
            if self._window:
                res = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
                if res and len(res) > 0:
                    chosen = res[0]
                    cfg = self.get_settings()
                    cfg["background_image_path"] = chosen
                    self.save_settings(cfg)
                    data_url = file_to_base64_data_url(chosen)
                    return {"success": True, "path": chosen, "data_url": data_url}
        except Exception as e:
            print(f"[WebApi] select_background_file error: {e}")
        return {"success": False, "msg": "未選擇檔案或取消"}

    # ═══════════════════════════════════════════════════════
    # 3. 工具清單與註冊表管理 (Registry)
    # ═══════════════════════════════════════════════════════
    def _load_registry_raw(self) -> Dict[str, Any]:
        """讀取 registry.json 原始內容"""
        if self._registry_file.exists():
            try:
                with open(self._registry_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WebApi] load registry error: {e}")
        return {"tools": [], "favorites": []}

    def _save_registry_raw(self, data: Dict[str, Any]) -> bool:
        """儲存 registry.json 原始內容"""
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            with open(self._registry_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"[WebApi] save registry error: {e}")
            return False

    def _resolve_tool_icon(self, tool_data: dict) -> str:
        """尋找小工具的最佳圖標並轉為 base64 data URL"""
        repo_name = tool_data.get("repo_name") or tool_data.get("name", "")
        cache_dir = self._root_dir / "resources" / "cache" / "icons"

        # 1. 優先快取圖標
        for cand in [repo_name, repo_name.replace(" ", ""), tool_data.get("name", "")]:
            if cand:
                cached_file = cache_dir / f"{cand}.png"
                if cached_file.exists() and cached_file.stat().st_size > 0:
                    return file_to_base64_data_url(str(cached_file))

        # 2. 檢查工作目錄內圖標
        wdir = tool_data.get("working_dir", "")
        if wdir and os.path.exists(wdir):
            candidates = [
                os.path.join(wdir, "resources", "icon.png"),
                os.path.join(wdir, "resources", "icon.ico"),
                os.path.join(wdir, "icon.png"),
                os.path.join(wdir, "icon.ico"),
                os.path.join(wdir, "src", "gui", "icon.png"),
                os.path.join(wdir, "src", "icon.png"),
                os.path.join(wdir, "assets", "icon.png"),
            ]
            for p in candidates:
                if os.path.exists(p) and os.path.getsize(p) > 0:
                    return file_to_base64_data_url(p)

        # 3. 預設啟動器圖標
        default_icon = self._root_dir / "resources" / "icon.png"
        if default_icon.exists():
            return file_to_base64_data_url(str(default_icon))
        return ""

    def get_tools(self) -> Dict[str, Any]:
        """
        取得所有工具完整列表 (包含安裝狀態、運行狀態、格式化標題、圖標 data URL 與更新資訊)
        """
        reg = self._load_registry_raw()
        raw_tools = reg.get("tools", [])
        favorites = set(reg.get("favorites", []))

        # 自動防遺失：若本地 SteamManifestUpdater 存在但未在 registry，自動補登
        local_steam = Path(r"G:\python\SteamManifestUpdater\src\main.py")
        if local_steam.exists():
            exes = [os.path.normpath(t.get("executable", "")).lower() for t in raw_tools]
            if str(local_steam).lower() not in exes:
                raw_tools.insert(0, {
                    "name": "Steam Manifest - 本地開發版",
                    "description": "本地原始碼開發版本 (支援快速熱重載與除錯)",
                    "executable": str(local_steam),
                    "working_dir": str(local_steam.parent.parent),
                    "is_local": True
                })
                reg["tools"] = raw_tools
                self._save_registry_raw(reg)

        processed_tools = []
        for t in raw_tools:
            name = t.get("name", "未命名小工具")
            exe = t.get("executable", "")
            wdir = t.get("working_dir", "")
            is_local = is_local_tool_data(t)

            # 自適應路徑修復 (例如 2.0\CloudTools 與 CloudTools 互轉)
            if not os.path.exists(exe):
                if "2.0\\CloudTools" in exe and os.path.exists(exe.replace("2.0\\CloudTools", "CloudTools")):
                    exe = exe.replace("2.0\\CloudTools", "CloudTools")
                    wdir = wdir.replace("2.0\\CloudTools", "CloudTools")
                    t["executable"] = exe
                    t["working_dir"] = wdir
                elif "\\CloudTools" in exe and os.path.exists(exe.replace("\\CloudTools", "\\2.0\\CloudTools")):
                    exe = exe.replace("\\CloudTools", "\\2.0\\CloudTools")
                    wdir = wdir.replace("\\CloudTools", "\\2.0\\CloudTools")
                    t["executable"] = exe
                    t["working_dir"] = wdir

            is_installed = bool(exe and os.path.exists(exe))
            is_fav = name in favorites

            # 運行中狀態判定
            is_running = False
            pid = 0
            if name in self.running_processes:
                pinfo = self.running_processes[name]
                proc = pinfo.get("proc")
                pid = pinfo.get("pid", 0)
                if proc and proc.poll() is None:
                    is_running = True
                elif pid and is_pid_alive(pid):
                    is_running = True
                else:
                    self.running_processes.pop(name, None)

            # 檢查更新資訊
            update_info = self.updates_cache.get(name)

            processed_tools.append({
                "name": name,
                "display_name": format_card_title(name),
                "description": t.get("description", ""),
                "executable": exe,
                "working_dir": wdir,
                "repo_name": t.get("repo_name", ""),
                "is_local": is_local,
                "is_installed": is_installed,
                "is_favorite": is_fav,
                "is_running": is_running,
                "pid": pid,
                "icon": self._resolve_tool_icon(t),
                "has_update": bool(update_info),
                "update_info": update_info or {}
            })

        app_icon = file_to_base64_data_url(str(self._root_dir / "resources" / "icon.png"))
        return {
            "tools": processed_tools,
            "favorites": list(favorites),
            "version": VERSION,
            "app_icon": app_icon
        }

    def toggle_favorite(self, name: str) -> bool:
        """切換小工具我的最愛狀態"""
        reg = self._load_registry_raw()
        favs = set(reg.get("favorites", []))
        is_fav = False
        if name in favs:
            favs.remove(name)
            is_fav = False
        else:
            favs.add(name)
            is_fav = True
        reg["favorites"] = list(favs)
        self._save_registry_raw(reg)
        return is_fav

    # ═══════════════════════════════════════════════════════
    # 4. 工具生命週期控制 (Launch & Process Control)
    # ═══════════════════════════════════════════════════════
    def launch_tool(self, name: str) -> Dict[str, Any]:
        """
        啟動小工具：
        1. 若軟體已在運行中：嘗試喚醒視窗置頂；若視窗已關閉但進程殘留，自動清理後重新打開。
        2. 獨立日誌記錄 stdout/stderr，完全避免黑窗。
        3. 2.5 秒健康觀察線程，秒級偵測語法或模組崩潰。
        """
        now = time.time()
        if now - self._launch_cooldowns.get(name, 0) < 1.0:
            return {"success": False, "msg": "啟動中，請稍候..."}
        self._launch_cooldowns[name] = now

        reg = self._load_registry_raw()
        tools = reg.get("tools", [])
        tool_data = None
        for t in tools:
            if t.get("name") == name:
                tool_data = t
                break

        if not tool_data:
            return {"success": False, "msg": f"找不到工具設定：{name}"}

        exe = tool_data.get("executable", "")
        wdir = tool_data.get("working_dir", "")

        # 1. 若該工具在運行列表中
        if name in self.running_processes:
            pinfo = self.running_processes[name]
            proc = pinfo.get("proc")
            pid = pinfo.get("pid", 0)

            alive = False
            if proc and proc.poll() is None:
                alive = True
            elif pid and is_pid_alive(pid):
                alive = True

            if alive:
                brought = bring_window_to_foreground(pid=pid, title_hint=name)
                if brought:
                    return {"success": True, "already_running": True, "msg": f"【{name}】已呼叫至最上層！", "pid": pid}
                else:
                    # 殘留進程釋放並重啟
                    try:
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                                       creationflags=0x08000000, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
                    self.running_processes.pop(name, None)
            else:
                self.running_processes.pop(name, None)

        if not os.path.exists(exe):
            return {"success": False, "msg": f"找不到執行檔：{exe}"}

        try:
            # 準備獨立日誌
            safe_name = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5-]', '_', name).strip('_') or "tool"
            log_path = self._logs_dir / f"{safe_name}.log"
            from datetime import datetime
            with open(log_path, "a", encoding="utf-8", errors="replace") as lf:
                lf.write(f"\n{'='*55}\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 啟動專案: {name}\n執行檔: {exe}\n工作目錄: {wdir}\n{'='*55}\n")

            log_file = open(log_path, "a", encoding="utf-8", errors="replace")

            # 0x00000008 (DETACHED_PROCESS) | 0x00000200 (CREATE_NEW_PROCESS_GROUP)
            detached_flags = 0x00000008 | 0x00000200
            proc = None

            if exe.endswith(".py"):
                python_exe = get_real_python_exe(prefer_gui=True)
                proc = subprocess.Popen(
                    [python_exe, exe],
                    cwd=wdir,
                    creationflags=detached_flags,
                    close_fds=True,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=log_file
                )
            elif exe.endswith((".bat", ".cmd")):
                proc = subprocess.Popen(
                    ["cmd.exe", "/c", exe],
                    cwd=wdir,
                    creationflags=detached_flags,
                    close_fds=True,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=log_file
                )
            else:
                proc = subprocess.Popen(
                    [exe],
                    cwd=wdir,
                    creationflags=detached_flags,
                    close_fds=True,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=log_file
                )

            try:
                log_file.close()
            except Exception:
                pass

            if proc:
                self.running_processes[name] = {
                    "proc": proc,
                    "pid": proc.pid,
                    "exe": exe,
                    "log_path": str(log_path),
                    "start_time": time.time()
                }

                # 啟動 2.5 秒崩潰守護監測
                def _watch_crash():
                    st = time.time()
                    while time.time() - st < 2.5:
                        ret = proc.poll()
                        if ret is not None:
                            if ret != 0:
                                self.running_processes.pop(name, None)
                                # 讀取 log 尾部
                                tail = ""
                                try:
                                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                                        tail = "".join(f.readlines()[-20:]).strip()
                                except Exception:
                                    pass
                                send_identity_webhook(f"💥 程式異常退出: {name}", f"Exit Code: {ret}\n{tail}", color=0xFF0033)
                            break
                        time.sleep(0.3)

                threading.Thread(target=_watch_crash, daemon=True).start()
                return {"success": True, "pid": proc.pid, "msg": f"【{name}】已成功啟動！"}

        except Exception as e:
            err = traceback_msg = str(e)
            return {"success": False, "msg": f"啟動失敗: {err}"}

        return {"success": False, "msg": "未知錯誤"}

    def stop_tool(self, name: str) -> Dict[str, Any]:
        """終止指定小工具進程樹"""
        if name not in self.running_processes:
            return {"success": False, "msg": "該工具目前未在運行中"}

        pinfo = self.running_processes.pop(name)
        pid = pinfo.get("pid")
        proc = pinfo.get("proc")

        try:
            if pid:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                               creationflags=0x08000000, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif proc:
                proc.terminate()
            return {"success": True, "msg": f"【{name}】已安全停止"}
        except Exception as e:
            return {"success": False, "msg": f"停止失敗: {e}"}

    def get_running_tools(self) -> List[str]:
        """定時心跳：取得當前處於活躍狀態的小工具名稱清單"""
        active = []
        for name, pinfo in list(self.running_processes.items()):
            proc = pinfo.get("proc")
            pid = pinfo.get("pid")
            if proc and proc.poll() is None:
                active.append(name)
            elif pid and is_pid_alive(pid):
                active.append(name)
            else:
                self.running_processes.pop(name, None)
        return active

    def open_tool_dir(self, name: str) -> bool:
        """在 Windows 檔案總管中打開工具目錄"""
        reg = self._load_registry_raw()
        for t in reg.get("tools", []):
            if t.get("name") == name:
                wdir = t.get("working_dir") or os.path.dirname(t.get("executable", ""))
                if wdir and os.path.exists(wdir):
                    subprocess.Popen(["explorer.exe", wdir])
                    return True
        return False

    def open_tool_log(self, name: str) -> bool:
        """打開工具日誌檔"""
        safe_name = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5-]', '_', name).strip('_') or "tool"
        log_path = self._logs_dir / f"{safe_name}.log"
        if log_path.exists():
            subprocess.Popen(["notepad.exe", str(log_path)])
            return True
        return False

    def uninstall_tool(self, name: str) -> Dict[str, Any]:
        """解除安裝雲端小工具"""
        reg = self._load_registry_raw()
        tools = reg.get("tools", [])
        target = None
        for t in tools:
            if t.get("name") == name:
                target = t
                break

        if not target:
            return {"success": False, "msg": "找不到目標工具"}

        if is_local_tool_data(target):
            return {"success": False, "msg": "本地開發版工具禁止透過收納盒解除安裝！"}

        # 若在運行中，先終止
        self.stop_tool(name)

        # 執行解除安裝與目錄刪除
        wdir = target.get("working_dir", "")
        if wdir and "CloudTools" in wdir and os.path.exists(wdir):
            try:
                cm_uninstall_tool(target)
            except Exception as e:
                print(f"[WebApi] cm_uninstall_tool warning: {e}")

        # 從 registry 清除
        tools = [t for t in tools if t.get("name") != name]
        reg["tools"] = tools
        if name in reg.get("favorites", []):
            reg["favorites"].remove(name)
        self._save_registry_raw(reg)

        return {"success": True, "msg": f"【{name}】已成功解除安裝！"}

    # ═══════════════════════════════════════════════════════
    # 5. 雲端商店與 Git 版本更新 (Market & Updates)
    # ═══════════════════════════════════════════════════════
    def fetch_cloud_market(self) -> Dict[str, Any]:
        """拉取 GitHub 雲端小工具商店列表並標記安裝狀態"""
        try:
            repos = fetch_github_repos()
            reg = self._load_registry_raw()
            installed_repos = set()
            for t in reg.get("tools", []):
                rn = t.get("repo_name")
                if rn:
                    installed_repos.add(rn.lower())
                else:
                    folder = os.path.basename(t.get("working_dir", "")).lower()
                    if folder:
                        installed_repos.add(folder)

            results = []
            for r in repos:
                rn = r.get("name", "")
                is_inst = rn.lower() in installed_repos
                results.append({
                    "name": r.get("display_name") or r.get("name"),
                    "repo_name": rn,
                    "description": r.get("description", "暫無描述"),
                    "version": r.get("version", "v1.0.0"),
                    "is_installed": is_inst,
                    "stars": r.get("stargazers_count", 0),
                    "updated_at": r.get("updated_at", "")[:10]
                })
            return {"success": True, "items": results}
        except Exception as e:
            return {"success": False, "msg": f"拉取雲端商店失敗: {e}", "items": []}

    def install_cloud_tool_sync(self, repo_name: str) -> Dict[str, Any]:
        """安裝或下載指定雲端工具"""
        res_box = {}
        done_event = threading.Event()

        def _prog(r_name, pct, status):
            pass

        def _done(success, msg, tool_entry, r_name):
            res_box["success"] = success
            res_box["msg"] = msg
            res_box["tool"] = tool_entry
            done_event.set()

        try:
            install_cloud_repo_async(repo_name, self._cloud_tools_dir, self._config_dir,
                                     progress_cb=_prog, finished_cb=_done)
            done_event.wait(timeout=300)
            return res_box or {"success": False, "msg": "安裝逾時"}
        except Exception as e:
            return {"success": False, "msg": f"安裝異常: {e}"}

    def check_all_updates(self) -> Dict[str, Any]:
        """檢查所有小工具的 Git 版本是否有更新"""
        flags, startupinfo = get_silent_flags_and_startupinfo()
        reg = self._load_registry_raw()
        updates = {}

        for t in reg.get("tools", []):
            name = t.get("name", "")
            if is_local_tool_data(t):
                continue
            wdir = t.get("working_dir", "")
            if not wdir or not os.path.exists(os.path.join(wdir, ".git")):
                continue

            try:
                # 執行快速 git fetch
                subprocess.run(["git", "fetch", "origin", "main"], cwd=wdir,
                               creationflags=flags, startupinfo=startupinfo,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=6)
                local_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=wdir,
                                                     creationflags=flags, startupinfo=startupinfo, text=True, encoding="utf-8", errors="replace", timeout=3).strip()
                remote_hash = subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=wdir,
                                                      creationflags=flags, startupinfo=startupinfo, text=True, encoding="utf-8", errors="replace", timeout=3).strip()
                if local_hash != remote_hash:
                    updates[name] = {
                        "local_ver": local_hash[:7],
                        "remote_ver": remote_hash[:7]
                    }
            except Exception:
                pass

        self.updates_cache = updates
        return {"success": True, "updates": updates}

    def update_tool_sync(self, name: str) -> Dict[str, Any]:
        """一鍵更新特定小工具 (git pull + pip requirements)"""
        flags, startupinfo = get_silent_flags_and_startupinfo()
        reg = self._load_registry_raw()
        target = None
        for t in reg.get("tools", []):
            if t.get("name") == name:
                target = t
                break

        if not target:
            return {"success": False, "msg": "找不到目標工具"}

        wdir = target.get("working_dir", "")
        if not wdir or not os.path.exists(wdir):
            return {"success": False, "msg": "工作目錄不存在"}

        try:
            # 1. git pull
            pull_out = subprocess.check_output(["git", "pull", "origin", "main"], cwd=wdir,
                                               creationflags=flags, startupinfo=startupinfo, text=True, encoding="utf-8", errors="replace", timeout=25)
            # 2. requirements.txt 檢查
            req = os.path.join(wdir, "requirements.txt")
            if os.path.exists(req):
                python_exe = get_real_python_exe(prefer_gui=False)
                subprocess.run([python_exe, "-m", "pip", "install", "-r", "requirements.txt"],
                               cwd=wdir, creationflags=flags, startupinfo=startupinfo, timeout=90)

            self.updates_cache.pop(name, None)
            return {"success": True, "msg": f"【{name}】已順利更新至最新版本！"}
        except Exception as e:
            return {"success": False, "msg": f"更新失敗: {e}"}

    def open_url(self, url: str) -> bool:
        """開啟外部網址"""
        try:
            import webbrowser
            webbrowser.open(url)
            return True
        except Exception:
            return False

    def get_client_id_info(self) -> Dict[str, str]:
        """取得客戶端授權與機器 ID"""
        try:
            return {"client_id": get_client_identity(), "version": VERSION}
        except Exception:
            return {"client_id": "DEFAULT-CLIENT", "version": VERSION}
