import os, sys, json, subprocess, threading, ctypes, re, time

# 註冊專屬 Windows AppUserModelID (解除 IDLE 綁定並在工作列顯示專屬圖標)
if sys.platform == "win32":
    try:
        myappid = "jiasai.aitoollauncher.v2.desktop"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

# Guard for pythonw (sys.stdout/stderr are None in GUI mode)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from PySide6.QtCore import Qt, QSize, Signal, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QMovie
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QFrame, QSizePolicy, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsBlurEffect
)
from qfluentwidgets import (
    MSFluentWindow, NavigationItemPosition, FluentIcon, SearchLineEdit,
    SubtitleLabel, CaptionLabel, InfoBar, InfoBarPosition, setTheme,
    Theme, setThemeColor, CardWidget, BodyLabel, TransparentToolButton,
    StrongBodyLabel, MessageBox, FlowLayout
)

def apply_frosted_blur(src_pixmap: QPixmap, blur_radius: int) -> QPixmap:
    """
    極速混合高斯毛玻璃模糊算法 (Hybrid Fast Gaussian Blur)
    耗時僅 ~3-5ms，產生頂級柔和磨砂模糊
    """
    if src_pixmap.isNull() or blur_radius <= 0:
        return src_pixmap

    scale_factor = 3 if blur_radius >= 10 else 2
    w = max(16, src_pixmap.width() // scale_factor)
    h = max(16, src_pixmap.height() // scale_factor)
    small_pix = src_pixmap.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(small_pix)
    blur_effect = QGraphicsBlurEffect()
    blur_effect.setBlurRadius(blur_radius / scale_factor)
    blur_effect.setBlurHints(QGraphicsBlurEffect.QualityHint)
    item.setGraphicsEffect(blur_effect)
    scene.addItem(item)

    out_small = QPixmap(small_pix.size())
    out_small.fill(Qt.transparent)
    painter = QPainter(out_small)
    scene.render(painter)
    painter.end()

    return out_small.scaled(src_pixmap.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

# Relative imports
try:
    from core.settings_panel import SettingsPanel
    from core.tool_box_widget import ToolCardWidget
    from core.cloud_manager import (
        fetch_github_repos, install_cloud_repo_async, reinstall_tool_async,
        uninstall_tool, parse_linkme
    )
    from core.identity_manager import (
        get_client_identity, send_identity_webhook, get_webhook_url,
        install_global_exception_hook
    )
except ModuleNotFoundError:
    from settings_panel import SettingsPanel
    from tool_box_widget import ToolCardWidget
    from cloud_manager import (
        fetch_github_repos, install_cloud_repo_async, reinstall_tool_async,
        uninstall_tool, parse_linkme
    )
    from identity_manager import (
        get_client_identity, send_identity_webhook, get_webhook_url,
        install_global_exception_hook
    )

# 立即安裝全域崩潰與異常攔截器
install_global_exception_hook()

VERSION = "2.0.9"


def set_native_topmost(window_obj, is_topmost: bool):
    """
    使用 Windows 原生 Win32 API (64 位元 HWND 嚴格簽名) 設置視窗絕對置頂
    """
    try:
        if sys.platform == "win32":
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            SetWindowPos = user32.SetWindowPos
            SetWindowPos.argtypes = [
                wintypes.HWND,
                wintypes.HWND,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                wintypes.UINT
            ]
            SetWindowPos.restype = wintypes.BOOL
            
            HWND_TOPMOST = wintypes.HWND(-1)
            HWND_NOTOPMOST = wintypes.HWND(-2)
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            SWP_SHOWWINDOW = 0x0040
            flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            
            hwnd_val = int(window_obj.winId()) if hasattr(window_obj, 'winId') else int(window_obj)
            hwnd = wintypes.HWND(hwnd_val)
            target = HWND_TOPMOST if is_topmost else HWND_NOTOPMOST
            SetWindowPos(hwnd, target, 0, 0, 0, 0, flags)
    except Exception:
        pass


def get_real_python_exe(prefer_gui: bool = True) -> str:
    """
    精準取得真實的 Python 解譯器路徑 (徹底防止 C# 包裝器 AIToolLauncher.exe 被誤當作 python.exe)
    """
    # 1. 優先檢查環境變數 TRUE_PYTHON_EXE / TRUE_PYTHON_DIR
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

    # 2. 檢查 sys.executable (排除 AIToolLauncher.exe)
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

    # 3. 檢查本地 runtime/python
    base_dir = os.path.dirname(os.path.dirname(__file__))
    portable_order = ["pythonw.exe", "python.exe"] if prefer_gui else ["python.exe", "pythonw.exe"]
    for cand in portable_order:
        portable = os.path.join(base_dir, "runtime", "python", cand)
        if os.path.exists(portable):
            return portable

    # 4. 尋找系統 PATH 中的 python
    import shutil
    order = ["pythonw", "python"] if prefer_gui else ["python", "pythonw"]
    for cand in order:
        p = shutil.which(cand)
        if p and not p.lower().endswith("aitoollauncher.exe"):
            return p

    return "pythonw" if prefer_gui else "python"


def bring_window_to_foreground(pid: int = None, title_hint: str = None) -> bool:
    """
    將指定 PID 或標題的 Windows 視窗呼叫並置於最上層
    """
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    found_hwnds = []

    def enum_cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        
        # 1. 依 PID 匹配
        if pid:
            win_pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(win_pid))
            if win_pid.value == pid:
                found_hwnds.append(hwnd)
                return False

        # 2. 依視窗標題模糊匹配
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
            SW_RESTORE = 9
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
        finally:
            user32.AttachThreadInput(cur_thread, target_thread, False)
        return True
    return False


def clear_layout(layout):
    """
    徹底清除 Layout 中的所有元件，避免殘留幽靈佈局
    """
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            break
        w = item if isinstance(item, QWidget) else getattr(item, 'widget', lambda: None)()
        if w:
            w.setParent(None)
            w.deleteLater()


class BoxLobbyInterface(QWidget):
    """
    收納盒大廳主頁面 (同頁雙區塊：上方「已安裝」、下方「未安裝」)
    採用自適應 FlowLayout 流式卡片網格，圖標置中，版面美觀
    """
    cloudReposFetched = Signal(list)

    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self.setObjectName("boxLobbyInterface")
        self.cloud_repos = []
        self.all_items_cache = []
        self.cloudReposFetched.connect(self.on_cloud_repos_fetched)
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(28, 20, 28, 20)
        self.layout.setSpacing(14)

        # 1. 頂部工具列 (標題 + 搜尋框 + 重新整理)
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        self.title_label = SubtitleLabel("📦 軟體收納盒 (Tool Box)", self)
        self.sub_label = CaptionLabel("點擊啟動工具，支援右鍵選單重新拉取、解除安裝與雲端下載", self)
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.sub_label)
        top_bar.addLayout(title_box)
        top_bar.addStretch(1)

        # 搜尋框
        self.search_input = SearchLineEdit(self)
        self.search_input.setPlaceholderText("🔍 搜尋小工具...")
        self.search_input.setFixedWidth(220)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.on_search_changed)
        top_bar.addWidget(self.search_input)

        # 新增本地小工具按鈕
        self.btn_add_local = TransparentToolButton(FluentIcon.ADD, self)
        self.btn_add_local.setToolTip("📁 新增 / 匯入本地小工具 (Add Local Tool)")
        self.btn_add_local.clicked.connect(self.parent_window.add_local_tool_dialog)
        top_bar.addWidget(self.btn_add_local)

        # 重新整理按鈕
        self.btn_refresh = TransparentToolButton(FluentIcon.SYNC, self)
        self.btn_refresh.setToolTip("重新整理列表與雲端庫")
        self.btn_refresh.clicked.connect(lambda: self.refresh_all(show_prompt=True))
        top_bar.addWidget(self.btn_refresh)

        self.layout.addLayout(top_bar)

        # 2. 滾動區域 (包含上下雙區塊: ⭐ 我的收藏 / 📦 全部專案)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setContentsMargins(4, 4, 8, 24)
        self.content_layout.setSpacing(18)

        # === 上方區塊: ⭐ 我的收藏 ===
        self.favorites_header = StrongBodyLabel("⭐ 我的收藏", self.container)
        self.favorites_header.setStyleSheet("font-size: 15px; font-weight: bold; color: #F59E0B;")
        self.content_layout.addWidget(self.favorites_header)

        self.favorites_flow_widget = QWidget(self.container)
        self.favorites_flow_widget.setStyleSheet("background: transparent;")
        self.favorites_flow_layout = FlowLayout(self.favorites_flow_widget, needAni=False)
        self.favorites_flow_layout.setContentsMargins(0, 4, 0, 8)
        self.favorites_flow_layout.setSpacing(16)
        self.content_layout.addWidget(self.favorites_flow_widget)

        # 分隔線
        self.divider = QFrame(self.container)
        self.divider.setFrameShape(QFrame.HLine)
        self.divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-height: 1px;")
        self.content_layout.addWidget(self.divider)

        # === 下方區塊: 📦 全部專案 ===
        self.all_header = StrongBodyLabel("📦 全部專案", self.container)
        self.all_header.setStyleSheet("font-size: 15px; font-weight: bold; color: #9A70FF;")
        self.content_layout.addWidget(self.all_header)

        self.all_flow_widget = QWidget(self.container)
        self.all_flow_widget.setStyleSheet("background: transparent;")
        self.all_flow_layout = FlowLayout(self.all_flow_widget, needAni=False)
        self.all_flow_layout.setContentsMargins(0, 4, 0, 8)
        self.all_flow_layout.setSpacing(16)
        self.content_layout.addWidget(self.all_flow_widget)

        self.content_layout.addStretch(1)
        self.scroll_area.setWidget(self.container)
        self.layout.addWidget(self.scroll_area)

        # 初始載入
        self.load_and_render_tools()
        self.fetch_cloud_repos_async()

    def refresh_all(self, show_prompt: bool = False):
        self.parent_window.reload_registry()
        self.fetch_cloud_repos_async()
        self.load_and_render_tools(filter_text=self.search_input.text().strip())
        if show_prompt:
            InfoBar.info(
                title="🔄 已重新整理",
                content="小工具列表與雲端狀態已同步！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def fetch_cloud_repos_async(self):
        def _callback(success, data):
            if success and isinstance(data, list):
                self.cloudReposFetched.emit(data)
            else:
                self.cloudReposFetched.emit([])

        fetch_github_repos(_callback)

    def on_cloud_repos_fetched(self, repos: list):
        self.cloud_repos = repos
        self.load_and_render_tools(filter_text=self.search_input.text().strip())

    def _create_card(self, data: dict, is_inst: bool, is_fav: bool, icon_size: int, parent_widget: QWidget) -> ToolCardWidget:
        name = data.get("name", "")
        repo_name = data.get("repo_name", "")
        card = ToolCardWidget(data, is_installed=is_inst, is_favorite=is_fav, icon_size=icon_size, parent=parent_widget)

        if is_inst:
            # 若該工具目前正運行中，初始化即同步顯示為綠色運行中
            if name in self.parent_window.running_processes or (repo_name and repo_name in self.parent_window.running_processes):
                card.apply_state(ToolCardWidget.STATE_RUNNING)

            card.toolClicked.connect(lambda d, inst, c=card: self.parent_window.launch_tool(d, card=c))
            card.reinstallRequested.connect(self.parent_window.reinstall_tool)
            card.uninstallRequested.connect(self.parent_window.uninstall_tool)
        else:
            card.toolClicked.connect(lambda d, inst: self.parent_window.install_cloud_tool(d))
            card.installRequested.connect(self.parent_window.install_cloud_tool)

        card.toggleFavoriteRequested.connect(self.parent_window.toggle_favorite)
        return card

    def load_and_render_tools(self, filter_text: str = ""):
        # 1. 清除舊有元件與頂層懸浮標籤
        clear_layout(self.favorites_flow_layout)
        clear_layout(self.all_flow_layout)
        for container in [self.favorites_flow_widget, self.all_flow_widget]:
            for child in container.findChildren(CaptionLabel):
                child.deleteLater()

        installed_tools = self.parent_window.load_tools()
        favorites_list = self.parent_window.registry.get("favorites", [])
        icon_size = self.parent_window.settings.get("icon_size", 56)

        cloud_installed_names = [
            os.path.basename(t.get("working_dir", "")).lower()
            for t in installed_tools
            if "cloudtools" in t.get("working_dir", "").lower()
        ] + [
            t.get("repo_name", "").lower()
            for t in installed_tools
            if "cloudtools" in t.get("working_dir", "").lower() and t.get("repo_name")
        ]

        # 整理所有專案清單 (已安裝 + 雲端未安裝，支援本地開發版與雲端版獨立共存)
        all_items = []
        for t in installed_tools:
            all_items.append((t, True))

        for repo in self.cloud_repos:
            rname = repo.get("name", "")
            if rname.lower() in cloud_installed_names:
                continue
            all_items.append((repo, False))

        self.all_items_cache = all_items

        # 篩選與分類
        matched_all = []
        matched_favorites = []

        for data, is_inst in all_items:
            name = data.get("name", "")
            repo_name = data.get("repo_name", "")
            desc = data.get("description") or ""
            is_fav = (name in favorites_list or (repo_name and repo_name in favorites_list))

            if filter_text:
                if filter_text.lower() not in name.lower() and filter_text.lower() not in desc.lower():
                    continue

            matched_all.append((data, is_inst, is_fav))
            if is_fav:
                matched_favorites.append((data, is_inst, is_fav))

        # === 渲染 1: ⭐ 我的收藏 ===
        self.favorites_header.setText(f"⭐ 我的收藏 ({len(matched_favorites)})")
        if matched_favorites:
            for data, is_inst, is_fav in matched_favorites:
                card = self._create_card(data, is_inst, is_fav, icon_size, self.favorites_flow_widget)
                self.favorites_flow_layout.addWidget(card)
        else:
            empty_text = "（右鍵點擊專案小卡可「加入收藏」）" if not filter_text else "（無符合收藏的專案）"
            empty_msg = CaptionLabel(empty_text, self.favorites_flow_widget)
            empty_msg.setStyleSheet("color: #888888; padding: 10px;")
            self.favorites_flow_layout.addWidget(empty_msg)

        # === 渲染 2: 📦 全部專案 ===
        self.all_header.setText(f"📦 全部專案 ({len(matched_all)})")
        if matched_all:
            for data, is_inst, is_fav in matched_all:
                card = self._create_card(data, is_inst, is_fav, icon_size, self.all_flow_widget)
                self.all_flow_layout.addWidget(card)
        else:
            empty_msg = CaptionLabel("（無符合條件的專案）", self.all_flow_widget)
            empty_msg.setStyleSheet("color: #888888; padding: 10px;")
            self.all_flow_layout.addWidget(empty_msg)

    def render_favorites_only(self, filter_text: str = ""):
        """
        局部極速重繪「我的收藏」區塊，耗時 < 15ms，不破壞或重製「全部專案」區塊
        """
        clear_layout(self.favorites_flow_layout)
        favorites_list = self.parent_window.registry.get("favorites", [])
        icon_size = self.parent_window.settings.get("icon_size", 56)

        matched_favorites = []
        for data, is_inst in self.all_items_cache:
            name = data.get("name", "")
            repo_name = data.get("repo_name", "")
            desc = data.get("description") or ""
            is_fav = (name in favorites_list or (repo_name and repo_name in favorites_list))
            if not is_fav:
                continue

            if filter_text:
                if filter_text.lower() not in name.lower() and filter_text.lower() not in desc.lower():
                    continue

            matched_favorites.append((data, is_inst, True))

        self.favorites_header.setText(f"⭐ 我的收藏 ({len(matched_favorites)})")
        if matched_favorites:
            for data, is_inst, is_fav in matched_favorites:
                card = self._create_card(data, is_inst, is_fav, icon_size, self.favorites_flow_widget)
                self.favorites_flow_layout.addWidget(card)
        else:
            empty_text = "（右鍵點擊專案小卡可「加入收藏」）" if not filter_text else "（無符合收藏的專案）"
            empty_msg = CaptionLabel(empty_text, self.favorites_flow_widget)
            empty_msg.setStyleSheet("color: #888888; padding: 10px;")
            self.favorites_flow_layout.addWidget(empty_msg)

    def on_search_changed(self, text: str):
        self.load_and_render_tools(filter_text=text.strip())

    def update_icon_size(self, size: int):
        for layout in [self.favorites_flow_layout, self.all_flow_layout]:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                w = item.widget() if item else None
                if isinstance(w, ToolCardWidget):
                    w.set_icon_size(size)


class AIToolLauncherV2(MSFluentWindow):
    """
    AIToolLauncher 2.0 主視窗 (原生 Acrylic 壓克力圓角收納盒大廳)
    """
    installProgressSignal = Signal(str, int, str)            # (repo_name, pct, status_text)
    installFinished = Signal(bool, str, dict, str)           # (success, msg, tool_entry, repo_name)
    reinstallFinished = Signal(bool, str, dict)
    toolLaunchedSignal = Signal(str, int, object)            # (name, pid, proc)
    toolLaunchFailedSignal = Signal(str)                     # (name)

    def __init__(self):
        super().__init__()
        base_root = os.path.dirname(os.path.dirname(__file__))
        self.config_dir = os.path.join(base_root, "resources", "config")
        self.cloud_tools_dir = os.path.join(base_root, "CloudTools")
        self.registry_file = os.path.join(self.config_dir, "registry.json")
        self.settings_file = os.path.join(self.config_dir, "v2_settings.json")
        self.registry = self.load_registry()

        # 運行中進程管理表: {tool_name: {"proc": proc, "pid": pid, "card": card, "exe": exe}}
        self.running_processes = {}
        # 安裝中卡片管理表: {repo_name: card}
        self.installing_cards = {}
        # 背景桌布、動態 GIF 與高斯磨砂壓克力管理 (比照 desk_tidy)
        self.bg_movie = None
        self.raw_background_pixmap = None
        self.blurred_background_pixmap = None
        self.background_opacity = 0.8
        self.background_blur_radius = 15
        self.bg_cached_path = ""

        self.installProgressSignal.connect(self.on_install_progress_slot)
        self.installFinished.connect(self.on_install_finished_slot)
        self.reinstallFinished.connect(self.on_reinstall_finished_slot)
        self.toolLaunchedSignal.connect(self.on_tool_launched_success)
        self.toolLaunchFailedSignal.connect(self.on_tool_launched_failed)

        # 即時進程狀態監控定時器 (每秒檢測程式是否關閉，自動重置卡片為未開啟)
        self.proc_monitor_timer = QTimer(self)
        self.proc_monitor_timer.setInterval(1000)
        self.proc_monitor_timer.timeout.connect(self.poll_running_processes)
        self.proc_monitor_timer.start()

        self.init_settings()
        self.init_window()
        self.init_navigation()

        threading.Thread(target=lambda: send_identity_webhook("🚀 啟動 AIToolLauncher 2.0 (收納盒模式)", "使用者已成功開啟 AIToolLauncher 2.0 大廳。"), daemon=True).start()

    def on_movie_frame_changed(self):
        """
        GIF 動畫幀變更即時渲染槽
        """
        if self.bg_movie and self.bg_movie.isValid():
            frame = self.bg_movie.currentPixmap()
            if not frame.isNull():
                if self.background_blur_radius > 0:
                    self.blurred_background_pixmap = apply_frosted_blur(frame, self.background_blur_radius)
                else:
                    self.blurred_background_pixmap = frame
                self.update()

    def update_blurred_background(self):
        """
        將靜態背景圖片依據當前模糊半徑計算高斯磨砂毛玻璃效果
        """
        if self.raw_background_pixmap and not self.raw_background_pixmap.isNull():
            if self.background_blur_radius > 0:
                self.blurred_background_pixmap = apply_frosted_blur(self.raw_background_pixmap, self.background_blur_radius)
            else:
                self.blurred_background_pixmap = self.raw_background_pixmap
        else:
            self.blurred_background_pixmap = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        if self.blurred_background_pixmap and not self.blurred_background_pixmap.isNull():
            w, h = self.width(), self.height()
            scaled = self.blurred_background_pixmap.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            sx = (w - scaled.width()) // 2
            sy = (h - scaled.height()) // 2

            # 1. 繪製深色/淺色底色基底 (避免自訂圖片透明通道透出桌面)
            is_dark = (self.settings.get("theme_mode", "Auto") != "Light")
            base_bg = QColor(18, 18, 22) if is_dark else QColor(240, 240, 245)
            painter.fillRect(self.rect(), base_bg)

            # 2. 繪製真實高斯磨砂桌布 / GIF 動畫幀 (依照 background_opacity 顯色濃度)
            painter.setOpacity(self.background_opacity)
            painter.drawPixmap(sx, sy, scaled)

            # 3. 疊加現代感磨砂壓克力透光層 (Dark: 15% 黑, Light: 15% 白，維持文字與卡片清晰度)
            painter.setOpacity(0.15)
            tint = QColor(10, 10, 14) if is_dark else QColor(255, 255, 255)
            painter.fillRect(self.rect(), tint)
        else:
            # 未自訂背景圖片時，使用 Fluent 預設原生背景
            painter.fillRect(self.rect(), self.backgroundColor)

        painter.end()

    def init_settings(self):
        self.settings_panel = SettingsPanel(self.settings_file, self)
        self.settings = self.settings_panel.settings
        self.settings_panel.settingsChanged.connect(self.apply_live_settings)

    def init_window(self):
        self.setWindowTitle(f"AI Tool Launcher 2.0 [收納盒模式] v{VERSION}")
        icon_ico = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icon.ico")
        icon_png = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icon.png")
        icon_file = icon_ico if os.path.exists(icon_ico) else icon_png
        if os.path.exists(icon_file):
            app_icon = QIcon(icon_file)
            self.setWindowIcon(app_icon)
            if hasattr(self, 'titleBar') and self.titleBar:
                self.titleBar.setIcon(app_icon)

        # 讀取並還原上一次記憶的拉伸大小與最大化狀態
        saved_w = self.settings.get("window_width", 960)
        saved_h = self.settings.get("window_height", 680)
        w = max(740, int(saved_w))
        h = max(520, int(saved_h))
        self.resize(w, h)
        self.setMinimumSize(740, 520)

        # 建立右上角置頂圖釘按鈕 (位於最小化按鈕左側)
        self.is_topmost = self.settings.get("always_on_top", False)
        self.pin_btn = TransparentToolButton(FluentIcon.PIN, self.titleBar)
        self.pin_btn.setFixedSize(38, 32)
        self.pin_btn.setIconSize(QSize(15, 15))
        self.pin_btn.clicked.connect(self.toggle_pin_topmost)
        self.titleBar.buttonLayout.insertWidget(0, self.pin_btn)
        self.update_pin_button_state()

        self.apply_live_settings(self.settings)

        if self.settings.get("window_is_maximized", False):
            self.showMaximized()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "settings") and self.settings is not None and hasattr(self, "settings_panel"):
            if not self.isMaximized() and not self.isMinimized():
                self.settings["window_width"] = self.width()
                self.settings["window_height"] = self.height()
                self.settings["window_is_maximized"] = False
                if not hasattr(self, "_save_size_timer"):
                    self._save_size_timer = QTimer(self)
                    self._save_size_timer.setSingleShot(True)
                    self._save_size_timer.setInterval(600)
                    self._save_size_timer.timeout.connect(self.settings_panel.save_settings)
                self._save_size_timer.start()

    def changeEvent(self, event):
        super().changeEvent(event)
        if hasattr(self, "settings") and self.settings is not None and hasattr(self, "settings_panel"):
            if event.type() == event.Type.WindowStateChange:
                if self.isMaximized():
                    self.settings["window_is_maximized"] = True
                    self.settings_panel.save_settings()
                elif not self.isMinimized():
                    self.settings["window_is_maximized"] = False
                    self.settings["window_width"] = self.width()
                    self.settings["window_height"] = self.height()
                    self.settings_panel.save_settings()

    def closeEvent(self, event):
        if hasattr(self, "settings") and self.settings is not None and hasattr(self, "settings_panel"):
            if self.isMaximized():
                self.settings["window_is_maximized"] = True
            elif not self.isMinimized():
                self.settings["window_is_maximized"] = False
                self.settings["window_width"] = self.width()
                self.settings["window_height"] = self.height()
            self.settings_panel.save_settings()
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                icon_ico = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icon.ico")
                if os.path.exists(icon_ico):
                    LR_LOADFROMFILE = 0x0010
                    IMAGE_ICON = 1
                    WM_SETICON = 0x0080
                    ICON_SMALL = 0
                    ICON_BIG = 1
                    hicon_big = ctypes.windll.user32.LoadImageW(0, icon_ico, IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
                    hicon_small = ctypes.windll.user32.LoadImageW(0, icon_ico, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                    if hicon_big:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small or hicon_big)
            except Exception:
                pass

        if self.is_topmost:
            set_native_topmost(self, True)

    def toggle_pin_topmost(self):
        self.is_topmost = not self.is_topmost
        self.settings["always_on_top"] = self.is_topmost
        self.settings_panel.save_settings()
        self.update_pin_button_state()
        set_native_topmost(self, self.is_topmost)

        if self.is_topmost:
            InfoBar.success(
                title="📌 視窗已置頂",
                content="收納盒已鎖定在螢幕最上層！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        else:
            InfoBar.info(
                title="📌 已取消置頂",
                content="收納盒已恢復正常視窗層級。",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def update_pin_button_state(self):
        if self.is_topmost:
            self.pin_btn.setStyleSheet("""
                TransparentToolButton {
                    background-color: rgba(154, 112, 255, 0.28);
                    border: 1px solid rgba(154, 112, 255, 0.5);
                    border-radius: 4px;
                }
                TransparentToolButton:hover {
                    background-color: rgba(154, 112, 255, 0.42);
                }
            """)
            self.pin_btn.setToolTip("📌 視窗已置頂 (點擊取消置頂)")
        else:
            self.pin_btn.setStyleSheet("""
                TransparentToolButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 4px;
                }
                TransparentToolButton:hover {
                    background-color: rgba(255, 255, 255, 0.12);
                }
            """)
            self.pin_btn.setToolTip("📌 視窗置頂 (點擊固定在最上層)")

    def init_navigation(self):
        # 1. 收納盒大廳
        self.box_lobby = BoxLobbyInterface(self, self)
        self.addSubInterface(self.box_lobby, FluentIcon.FOLDER, "收納盒大廳", position=NavigationItemPosition.TOP)

        # 2. 個性化設定
        self.addSubInterface(self.settings_panel, FluentIcon.SETTING, "個性化設置", position=NavigationItemPosition.BOTTOM)

        # 3. 確保 StackedWidget 與 NavigationInterface 在自訂背景模式下完全透明
        self.stackedWidget.setProperty("isTransparent", True)
        self.stackedWidget.setStyleSheet("StackedWidget, QWidget#stackedWidget { background-color: transparent; border: none; }")
        self.navigationInterface.setStyleSheet("NavigationBar, QWidget#navigationInterface { background-color: transparent; }")

    def load_registry(self) -> dict:
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tools = data.get("tools", [])
                    modified = False
                    for t in tools:
                        exe = t.get("executable", "")
                        wdir = t.get("working_dir", "")
                        if not os.path.exists(exe):
                            if "2.0\\CloudTools" in exe:
                                fixed_exe = exe.replace("2.0\\CloudTools", "CloudTools")
                                fixed_wdir = wdir.replace("2.0\\CloudTools", "CloudTools")
                                if os.path.exists(fixed_exe):
                                    t["executable"] = fixed_exe
                                    t["working_dir"] = fixed_wdir
                                    modified = True
                            elif "\\CloudTools" in exe and "2.0\\CloudTools" not in exe:
                                fixed_exe = exe.replace("\\CloudTools", "\\2.0\\CloudTools")
                                fixed_wdir = wdir.replace("\\CloudTools", "\\2.0\\CloudTools")
                                if os.path.exists(fixed_exe):
                                    t["executable"] = fixed_exe
                                    t["working_dir"] = fixed_wdir
                                    modified = True
                    # 自動保障本機核心開發專案 (若本地原始碼存在且未在清單中，自動登記防遺失)
                    local_dev_manifest = r"G:\python\SteamManifestUpdater\src\main.py"
                    if os.path.exists(local_dev_manifest):
                        registered_exes = [os.path.normpath(t.get("executable", "")) for t in tools]
                        if os.path.normpath(local_dev_manifest) not in registered_exes:
                            tools.insert(0, {
                                "name": "Steam Manifest - 本地開發版",
                                "description": "本地原始碼開發版本 (支援快速熱重載與除錯)",
                                "executable": local_dev_manifest,
                                "working_dir": r"G:\python\SteamManifestUpdater"
                            })
                            favs = data.setdefault("favorites", [])
                            if "Steam Manifest - 本地開發版" not in favs:
                                favs.insert(0, "Steam Manifest - 本地開發版")
                            modified = True

                    if modified:
                        self.save_registry()
                    return data
            except Exception:
                pass
        
        # 預設註冊表
        init_tools = []
        local_dev_manifest = r"G:\python\SteamManifestUpdater\src\main.py"
        if os.path.exists(local_dev_manifest):
            init_tools.append({
                "name": "Steam Manifest - 本地開發版",
                "description": "本地原始碼開發版本 (支援快速熱重載與除錯)",
                "executable": local_dev_manifest,
                "working_dir": r"G:\python\SteamManifestUpdater"
            })
        return {"tools": init_tools, "favorites": ["Steam Manifest - 本地開發版"] if init_tools else []}

    def save_registry(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(self.registry, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def reload_registry(self):
        self.registry = self.load_registry()

    def load_tools(self) -> list:
        return self.registry.get("tools", [])

    def apply_live_settings(self, s: dict):
        self.settings = s

        # 1. 窗口透明度
        opacity = s.get("window_opacity", 95) / 100.0
        self.setWindowOpacity(opacity)

        # 2. 自訂背景圖片 / GIF 動畫 ＆ 磨砂模糊半徑
        bg_path = s.get("background_image_path", "")
        self.background_opacity = s.get("background_opacity", 80) / 100.0
        self.background_blur_radius = s.get("background_blur", 15)

        if bg_path and os.path.exists(bg_path):
            is_gif = bg_path.lower().endswith(".gif")
            if is_gif:
                if self.bg_movie is None or self.bg_cached_path != bg_path:
                    if self.bg_movie:
                        self.bg_movie.stop()
                    self.bg_movie = QMovie(bg_path)
                    self.bg_movie.frameChanged.connect(self.on_movie_frame_changed)
                    self.bg_movie.start()
                    self.bg_cached_path = bg_path
                self.on_movie_frame_changed()
            else:
                if self.bg_movie:
                    self.bg_movie.stop()
                    self.bg_movie = None
                if self.bg_cached_path != bg_path or self.raw_background_pixmap is None:
                    self.bg_cached_path = bg_path
                    self.raw_background_pixmap = QPixmap(bg_path)
                self.update_blurred_background()
        else:
            if self.bg_movie:
                self.bg_movie.stop()
                self.bg_movie = None
            self.bg_cached_path = ""
            self.raw_background_pixmap = None
            self.blurred_background_pixmap = None

        # 3. 圖標大小
        icon_size = s.get("icon_size", 56)
        if hasattr(self, "box_lobby"):
            self.box_lobby.update_icon_size(icon_size)

        # 4. 視窗置頂
        self.is_topmost = s.get("always_on_top", False)
        self.update_pin_button_state()
        set_native_topmost(self, self.is_topmost)

        self.update()

    def launch_tool(self, tool_data: dict, card: ToolCardWidget = None):
        name = tool_data.get("name", "小工具")
        exe = tool_data.get("executable", "")
        wdir = tool_data.get("working_dir", "")

        # 防連點 / 重複觸發保護 (1.2 秒內同一工具僅允許觸發一次啟動)
        now = time.time()
        if not hasattr(self, "_launch_cooldowns"):
            self._launch_cooldowns = {}
        if now - self._launch_cooldowns.get(name, 0) < 1.2:
            return
        self._launch_cooldowns[name] = now

        # 1. 若該軟體已在運行中，直接呼叫至最上層 (已開啟 = 綠色，再次點選直接置頂)
        if name in self.running_processes:
            info = self.running_processes[name]
            proc = info.get("proc")
            if proc and proc.poll() is None:
                pid = info.get("pid")
                bring_window_to_foreground(pid=pid, title_hint=name)
                InfoBar.info(
                    title="🪟 視窗已呼叫",
                    content=f"【{name}】已為您切換至最上層！",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            else:
                self.running_processes.pop(name, None)

        # 自適應修復路徑
        if not os.path.exists(exe):
            if "2.0\\CloudTools" in exe and os.path.exists(exe.replace("2.0\\CloudTools", "CloudTools")):
                exe = exe.replace("2.0\\CloudTools", "CloudTools")
                wdir = wdir.replace("2.0\\CloudTools", "CloudTools")
            elif "\\CloudTools" in exe and os.path.exists(exe.replace("\\CloudTools", "\\2.0\\CloudTools")):
                exe = exe.replace("\\CloudTools", "\\2.0\\CloudTools")
                wdir = wdir.replace("\\CloudTools", "\\2.0\\CloudTools")

        if not os.path.exists(exe):
            send_identity_webhook(f"💥 啟動異常: {name}", f"找不到執行檔：{exe}\n工作目錄：{wdir}", color=0xFF0033)
            self.set_all_cards_state(name, ToolCardWidget.STATE_ERROR)
            InfoBar.error(
                title="❌ 啟動失敗",
                content=f"找不到執行檔：{exe}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self
            )
            return

        def _run():
            try:
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
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                elif exe.endswith((".bat", ".cmd")):
                    proc = subprocess.Popen(
                        ["cmd.exe", "/c", exe],
                        cwd=wdir,
                        creationflags=detached_flags,
                        close_fds=True,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                else:
                    proc = subprocess.Popen(
                        [exe],
                        cwd=wdir,
                        creationflags=detached_flags,
                        close_fds=True,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

                if proc:
                    self.toolLaunchedSignal.emit(name, proc.pid, proc)
            except Exception as e:
                send_identity_webhook(f"💥 工具異常: {name}", f"啟動失敗: {str(e)}\n執行檔: {exe}\n工作目錄: {wdir}", color=0xFF0033)
                self.toolLaunchFailedSignal.emit(name)

        threading.Thread(target=_run, daemon=True).start()

    def set_all_cards_state(self, tool_name: str, state: str, progress: int = 0, status_text: str = ""):
        """
        同步更新所有分類區塊 (我的收藏 / 全部專案) 中該專案小卡的運行/安裝狀態
        """
        if not hasattr(self, "box_lobby") or not self.box_lobby:
            return

        for layout in [self.box_lobby.favorites_flow_layout, self.box_lobby.all_flow_layout]:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                w = item.widget() if item else None
                if isinstance(w, ToolCardWidget):
                    w_name = w.data.get("name", "")
                    w_repo = w.data.get("repo_name", "")
                    if tool_name in (w_name, w_repo) or (w_name and w_name == tool_name) or (w_repo and w_repo == tool_name):
                        if state == ToolCardWidget.STATE_INSTALLING:
                            w.set_install_progress(progress, status_text)
                        else:
                            w.apply_state(state)

    def on_tool_launched_success(self, name: str, pid: int, proc: object):
        self.running_processes[name] = {
            "proc": proc,
            "pid": pid
        }
        self.set_all_cards_state(name, ToolCardWidget.STATE_RUNNING)

    def on_tool_launched_failed(self, name: str):
        self.set_all_cards_state(name, ToolCardWidget.STATE_ERROR)

    def poll_running_processes(self):
        """
        每秒定期檢測運行中的小工具，若程式關閉則同步將所有分類的卡片復原為未開啟 (IDLE)
        """
        stopped_tools = []
        for name, info in list(self.running_processes.items()):
            proc = info.get("proc")
            if proc:
                ret = proc.poll()
                if ret is not None:
                    stopped_tools.append(name)
                    # 程式正常結束或手動關閉，均將所有分類的卡片同步復原為未開啟 (IDLE)
                    self.set_all_cards_state(name, ToolCardWidget.STATE_IDLE)
        for name in stopped_tools:
            self.running_processes.pop(name, None)

    def toggle_favorite(self, tool_data: dict):
        """
        切換收藏狀態 (新增 / 取消收藏) - 極速秒級響應 (< 15ms)
        """
        name = tool_data.get("name") or tool_data.get("repo_name", "")
        repo_name = tool_data.get("repo_name", "")
        favs = self.registry.setdefault("favorites", [])

        is_fav = False
        if name in favs:
            favs.remove(name)
        elif repo_name and repo_name in favs:
            favs.remove(repo_name)
        else:
            favs.append(name)
            is_fav = True

        self.save_registry()

        # 1. 秒速就地更新「全部專案」區塊中對應卡片的星標與 Tooltip
        for i in range(self.box_lobby.all_flow_layout.count()):
            item = self.box_lobby.all_flow_layout.itemAt(i)
            w = item.widget() if item else None
            if isinstance(w, ToolCardWidget) and (w.data.get("name") == name or w.data.get("repo_name") == repo_name):
                w.set_favorite(is_fav)

        # 2. 僅局部重繪「我的收藏」區塊 (不重建全部專案)
        self.box_lobby.render_favorites_only(filter_text=self.box_lobby.search_input.text().strip())

    def install_cloud_tool(self, repo_data: dict):
        repo_name = repo_data.get("name", "小工具")
        
        # 標記正在安裝中的小卡
        for layout in [self.box_lobby.favorites_flow_layout, self.box_lobby.all_flow_layout]:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                w = item.widget() if item else None
                if isinstance(w, ToolCardWidget) and (w.data.get("name") == repo_name or w.data.get("repo_name") == repo_name):
                    w.apply_state(ToolCardWidget.STATE_INSTALLING)
                    w.set_install_progress(5, "正在連線...")

        def _on_progress(pct, msg):
            self.installProgressSignal.emit(repo_name, pct, msg)

        def _on_finished(success, msg, tool_entry):
            self.installFinished.emit(success, msg, tool_entry or {}, repo_name)

        py_cli = get_real_python_exe(prefer_gui=False)
        install_cloud_repo_async(repo_data, self.cloud_tools_dir, py_cli, _on_finished, _on_progress)

    def on_install_progress_slot(self, repo_name: str, pct: int, status_text: str):
        for layout in [self.box_lobby.favorites_flow_layout, self.box_lobby.all_flow_layout]:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                w = item.widget() if item else None
                if isinstance(w, ToolCardWidget) and (w.data.get("name") == repo_name or w.data.get("repo_name") == repo_name):
                    w.set_install_progress(pct, status_text)

    def on_install_finished_slot(self, success: bool, msg: str, tool_entry: dict, repo_name: str):
        if success and tool_entry:
            t_name = tool_entry.get("name", repo_name)
            self.registry["tools"] = [
                t for t in self.registry.get("tools", [])
                if t.get("name") not in (t_name, repo_name)
                and t.get("repo_name", "") not in (t_name, repo_name)
            ]
            self.registry.setdefault("tools", []).append(tool_entry)
            self.save_registry()

            # 立即就地重新渲染 (0ms，極速無卡頓，不觸發多餘網路請求)
            self.box_lobby.load_and_render_tools(filter_text=self.box_lobby.search_input.text().strip())

            InfoBar.success(
                title="🎉 安裝成功",
                content=f"【{t_name}】已成功安裝並加入收納盒！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3500,
                parent=self
            )
        else:
            self.set_all_cards_state(repo_name, ToolCardWidget.STATE_ERROR)
            InfoBar.error(
                title="❌ 安裝失敗",
                content=msg,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )

    def reinstall_tool(self, tool_data: dict):
        name = tool_data.get("name", "小工具")
        InfoBar.info(
            title="🔄 正在重新拉取",
            content=f"正在同步 【{name}】 最新程式碼與套件...",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3500,
            parent=self
        )

        def _on_finished(success, msg, updated_tool):
            self.reinstallFinished.emit(success, msg, updated_tool or {})

        py_cli = get_real_python_exe(prefer_gui=False)
        reinstall_tool_async(tool_data, py_cli, _on_finished)

    def on_reinstall_finished_slot(self, success: bool, msg: str, updated_tool: dict):
        if success:
            self.save_registry()
            self.box_lobby.load_and_render_tools(filter_text=self.box_lobby.search_input.text().strip())
            InfoBar.success(
                title="🎉 更新成功",
                content=f"【{updated_tool.get('name', '小工具')}】已完成同步更新！",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        else:
            InfoBar.error(
                title="❌ 更新失敗",
                content=msg,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4500,
                parent=self
            )

    def add_local_tool_dialog(self):
        """
        手動新增 / 匯入本地小工具檔案 (.py, .bat, .exe)
        """
        from PySide6.QtWidgets import QFileDialog, QInputDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "📁 選擇本地小工具啟動檔",
            r"G:\python",
            "可執行檔 (*.py *.bat *.cmd *.exe);;Python 腳本 (*.py);;批次檔 (*.bat *.cmd);;執行檔 (*.exe);;所有檔案 (*.*)"
        )
        if not file_path or not os.path.exists(file_path):
            return

        file_path = os.path.normpath(file_path)
        wdir = os.path.dirname(file_path)
        
        # 若為子目錄，自動往上一層偵測 linkme.bat
        if os.path.exists(os.path.join(os.path.dirname(wdir), "linkme.bat")):
            wdir = os.path.dirname(wdir)
        
        if os.path.exists(os.path.join(wdir, "linkme.bat")):
            info = parse_linkme(wdir)
            if info:
                tool_name = info.get("name") or os.path.basename(wdir)
                tool_desc = info.get("description") or "本地專案"
                self.registry.setdefault("tools", []).append({
                    "name": tool_name,
                    "description": tool_desc,
                    "executable": info.get("executable") or file_path,
                    "working_dir": wdir
                })
                self.save_registry()
                self.box_lobby.load_and_render_tools(filter_text=self.box_lobby.search_input.text().strip())
                InfoBar.success(title="🎉 新增成功", content=f"已成功添加本地專案 【{tool_name}】", duration=3000, parent=self)
                return

        default_name = os.path.basename(wdir) if os.path.basename(file_path).lower() in ("main.py", "start.bat", "run.py", "app.py") else os.path.splitext(os.path.basename(file_path))[0]
        name, ok = QInputDialog.getText(self, "✨ 設定小工具名稱", "請輸入顯示名稱：", text=default_name)
        if not ok or not name.strip():
            return
        name = name.strip()

        desc, ok = QInputDialog.getText(self, "📝 設定小工具描述", "請輸入功能簡述 (選填)：", text="本地小工具")
        if not ok:
            desc = ""

        self.registry["tools"] = [t for t in self.registry.get("tools", []) if t.get("name") != name]
        self.registry.setdefault("tools", []).append({
            "name": name,
            "description": desc.strip(),
            "executable": file_path,
            "working_dir": wdir
        })
        self.save_registry()
        self.box_lobby.load_and_render_tools(filter_text=self.box_lobby.search_input.text().strip())
        InfoBar.success(title="🎉 新增成功", content=f"已成功添加本地小工具 【{name}】", duration=3000, parent=self)

    def uninstall_tool(self, tool_data: dict):
        name = tool_data.get("name", "")
        repo_name = tool_data.get("repo_name", "")
        wdir = tool_data.get("working_dir", "")
        
        display_name = name or repo_name or "小工具"
        is_cloud = "cloudtools" in wdir.lower()

        if is_cloud:
            dlg_title = f"🗑️ 確認解除安裝 【{display_name}】"
            dlg_msg = f"您確定要解除安裝雲端工具 【{display_name}】 嗎？\n\n這將重置其為「未安裝」狀態並清理 CloudTools 下載資料夾。"
        else:
            dlg_title = f"❌ 從清單移除 【{display_name}】"
            dlg_msg = f"您確定要將 【{display_name}】 從收納盒清單中移除嗎？\n\n【重要提示】此操作僅從啟動器移除捷徑，您的本地專案原始碼、開發數據與檔案將 100% 完整保留，絕不會被刪除。"

        w = MessageBox(dlg_title, dlg_msg, self)
        if not w.exec():
            return

        # 1. 主線程立即同步更新記憶體註冊表 (0ms 無延遲，無競爭條件)
        self.registry["tools"] = [
            t for t in self.registry.get("tools", [])
            if t.get("name") not in (name, repo_name)
            and t.get("repo_name", "") not in (name, repo_name)
            and (not wdir or t.get("working_dir") != wdir)
        ]
        favs = self.registry.setdefault("favorites", [])
        if name in favs:
            favs.remove(name)
        if repo_name and repo_name in favs:
            favs.remove(repo_name)

        self.save_registry()

        # 2. 立即就地重新渲染小卡清單 (0ms，極速無卡頓，不觸發多餘網路請求)
        self.box_lobby.load_and_render_tools(filter_text=self.box_lobby.search_input.text().strip())

        # 3. 若為雲端專案，在背景線程靜默清理本機檔案資料夾 (本地開發專案絕對不碰！)
        if is_cloud and wdir and os.path.exists(wdir) and os.path.abspath(wdir).startswith(os.path.abspath(self.cloud_tools_dir)):
            threading.Thread(target=lambda: force_remove_directory(wdir), daemon=True).start()

        InfoBar.success(
            title="🗑️ 已移除雲端小工具" if is_cloud else "❌ 已從清單移除",
            content=f"已成功解除安裝 【{display_name}】" if is_cloud else f"已將 【{display_name}】 從收納盒清單移除（本地檔案完整保留）",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2500,
            parent=self
        )


def main():
    try:
        if sys.platform == "win32":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("jiasai.aitoollauncher.v2.desktop")
            except Exception:
                pass

        app = QApplication(sys.argv)
        app.setApplicationName("AIToolLauncher")
        app.setApplicationDisplayName("AI Tool Launcher 2.0")

        icon_ico = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icon.ico")
        icon_png = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icon.png")
        icon_file = icon_ico if os.path.exists(icon_ico) else icon_png
        if os.path.exists(icon_file):
            app.setWindowIcon(QIcon(icon_file))

        setTheme(Theme.AUTO)
        setThemeColor("#9A70FF")
        
        window = AIToolLauncherV2()
        if os.path.exists(icon_file):
            window.setWindowIcon(QIcon(icon_file))
            
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "launcher_error.log")
        with open(log_path, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)

if __name__ == "__main__":
    main()
