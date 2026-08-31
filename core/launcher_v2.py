import os, sys, json, subprocess, threading, ctypes, re

# Guard for pythonw (sys.stdout/stderr are None in GUI mode)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QFrame, QSizePolicy
)
from qfluentwidgets import (
    MSFluentWindow, NavigationItemPosition, FluentIcon, SearchLineEdit,
    SubtitleLabel, CaptionLabel, InfoBar, InfoBarPosition, setTheme,
    Theme, setThemeColor, CardWidget, BodyLabel, TransparentToolButton,
    StrongBodyLabel, MessageBox, FlowLayout
)

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

VERSION = "2.0.7"


def set_native_topmost(win_id: int, is_topmost: bool):
    """
    使用 Windows 原生 Win32 API 設置視窗置頂
    """
    try:
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040
        flags = SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        target = HWND_TOPMOST if is_topmost else HWND_NOTOPMOST
        ctypes.windll.user32.SetWindowPos(int(win_id), target, 0, 0, 0, 0, flags)
    except Exception:
        pass


def clear_layout(layout):
    """
    徹底清除 Layout 中的所有元件，避免殘留幽靈佈局
    """
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.setParent(None)
            w.deleteLater()


class BoxLobbyInterface(QWidget):
    """
    收納盒大廳主頁面 (同頁雙區塊：上方「已安裝」、下方「未安裝」)
    採用自適應 FlowLayout 流式卡片網格，保證元件永不收縮摺疊
    """
    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self.setObjectName("boxLobbyInterface")
        self.cloud_repos = []
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

        # 重新整理按鈕
        self.btn_refresh = TransparentToolButton(FluentIcon.SYNC, self)
        self.btn_refresh.setToolTip("重新整理列表與雲端庫")
        self.btn_refresh.clicked.connect(self.refresh_all)
        top_bar.addWidget(self.btn_refresh)

        self.layout.addLayout(top_bar)

        # 2. 滾動區域 (包含上下雙區塊)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setContentsMargins(4, 4, 8, 24)
        self.content_layout.setSpacing(18)

        # === 上方區塊: 🟢 已安裝 ===
        self.installed_header = StrongBodyLabel("🟢 已安裝", self.container)
        self.installed_header.setStyleSheet("font-size: 15px; font-weight: bold; color: #6CCB5F;")
        self.content_layout.addWidget(self.installed_header)

        self.installed_flow_widget = QWidget(self.container)
        self.installed_flow_widget.setStyleSheet("background: transparent;")
        self.installed_flow_layout = FlowLayout(self.installed_flow_widget, needAni=False)
        self.installed_flow_layout.setContentsMargins(0, 4, 0, 8)
        self.installed_flow_layout.setSpacing(16)
        self.content_layout.addWidget(self.installed_flow_widget)

        # 分隔線
        self.divider = QFrame(self.container)
        self.divider.setFrameShape(QFrame.HLine)
        self.divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-height: 1px;")
        self.content_layout.addWidget(self.divider)

        # === 下方區塊: ☁️ 雲端庫 / 未安裝 ===
        self.uninstalled_header = StrongBodyLabel("☁️ 雲端庫 / 未安裝", self.container)
        self.uninstalled_header.setStyleSheet("font-size: 15px; font-weight: bold; color: #9A70FF;")
        self.content_layout.addWidget(self.uninstalled_header)

        self.uninstalled_flow_widget = QWidget(self.container)
        self.uninstalled_flow_widget.setStyleSheet("background: transparent;")
        self.uninstalled_flow_layout = FlowLayout(self.uninstalled_flow_widget, needAni=False)
        self.uninstalled_flow_layout.setContentsMargins(0, 4, 0, 8)
        self.uninstalled_flow_layout.setSpacing(16)
        self.content_layout.addWidget(self.uninstalled_flow_widget)

        self.content_layout.addStretch(1)
        self.scroll_area.setWidget(self.container)
        self.layout.addWidget(self.scroll_area)

        # 初始載入
        self.load_and_render_tools()
        self.fetch_cloud_repos_async()

    def refresh_all(self):
        self.parent_window.reload_registry()
        self.fetch_cloud_repos_async()
        self.load_and_render_tools(filter_text=self.search_input.text().strip())
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
            if success:
                self.cloud_repos = data
                self.load_and_render_tools(filter_text=self.search_input.text().strip())

        fetch_github_repos(_callback)

    def load_and_render_tools(self, filter_text: str = ""):
        # 1. 清除舊有元件
        clear_layout(self.installed_flow_layout)
        clear_layout(self.uninstalled_flow_layout)

        installed_tools = self.parent_window.load_tools()
        icon_size = self.parent_window.settings.get("icon_size", 56)

        # 2. 渲染已安裝區塊 (上方)
        matched_installed = []
        for t in installed_tools:
            name = t.get("name", "")
            desc = t.get("description", "")
            if filter_text:
                if filter_text.lower() not in name.lower() and filter_text.lower() not in desc.lower():
                    continue
            matched_installed.append(t)

        self.installed_header.setText(f"🟢 已安裝 ({len(matched_installed)})")

        if matched_installed:
            for tool in matched_installed:
                card = ToolCardWidget(tool, is_installed=True, icon_size=icon_size, parent=self.installed_flow_widget)
                card.toolClicked.connect(lambda d, inst: self.parent_window.launch_tool(d))
                card.reinstallRequested.connect(self.parent_window.reinstall_tool)
                card.uninstallRequested.connect(self.parent_window.uninstall_tool)
                self.installed_flow_layout.addWidget(card)
        else:
            empty_msg = CaptionLabel("（無符合條件的已安裝小工具）", self.installed_flow_widget)
            empty_msg.setStyleSheet("color: #888888; padding: 10px;")
            self.installed_flow_layout.addWidget(empty_msg)

        # 3. 渲染未安裝區塊 (下方)
        installed_names = [t.get("name", "").lower() for t in installed_tools]
        installed_wdirs = [os.path.basename(t.get("working_dir", "")).lower() for t in installed_tools]

        matched_uninstalled = []
        for repo in self.cloud_repos:
            rname = repo.get("name", "")
            rdesc = repo.get("description") or ""
            if rname.lower() in installed_names or rname.lower() in installed_wdirs:
                continue

            if filter_text:
                if filter_text.lower() not in rname.lower() and filter_text.lower() not in rdesc.lower():
                    continue
            matched_uninstalled.append(repo)

        self.uninstalled_header.setText(f"☁️ 雲端庫 / 未安裝 ({len(matched_uninstalled)})")

        if matched_uninstalled:
            for repo in matched_uninstalled:
                card = ToolCardWidget(repo, is_installed=False, icon_size=icon_size, parent=self.uninstalled_flow_widget)
                card.toolClicked.connect(lambda d, inst: self.parent_window.install_cloud_tool(d))
                card.installRequested.connect(self.parent_window.install_cloud_tool)
                self.uninstalled_flow_layout.addWidget(card)
        else:
            empty_text = "（所有雲端小工具皆已安裝完畢）" if self.cloud_repos else "（正在向 GitHub 查詢雲端庫...）"
            empty_msg = CaptionLabel(empty_text, self.uninstalled_flow_widget)
            empty_msg.setStyleSheet("color: #888888; padding: 10px;")
            self.uninstalled_flow_layout.addWidget(empty_msg)

    def on_search_changed(self, text: str):
        self.load_and_render_tools(filter_text=text.strip())

    def update_icon_size(self, size: int):
        for i in range(self.installed_flow_layout.count()):
            item = self.installed_flow_layout.itemAt(i)
            w = item.widget() if item else None
            if isinstance(w, ToolCardWidget):
                w.set_icon_size(size)

        for i in range(self.uninstalled_flow_layout.count()):
            item = self.uninstalled_flow_layout.itemAt(i)
            w = item.widget() if item else None
            if isinstance(w, ToolCardWidget):
                w.set_icon_size(size)


class AIToolLauncherV2(MSFluentWindow):
    """
    AIToolLauncher 2.0 主視窗 (原生 Acrylic 壓克力圓角收納盒大廳)
    """
    def __init__(self):
        super().__init__()
        base_root = os.path.dirname(os.path.dirname(__file__))
        self.config_dir = os.path.join(base_root, "resources", "config")
        self.cloud_tools_dir = os.path.join(base_root, "CloudTools")
        self.registry_file = os.path.join(self.config_dir, "registry.json")
        self.settings_file = os.path.join(self.config_dir, "v2_settings.json")
        self.registry = self.load_registry()

        self.init_settings()
        self.init_window()
        self.init_navigation()

        threading.Thread(target=lambda: send_identity_webhook("🚀 啟動 AIToolLauncher 2.0 (收納盒模式)", "使用者已成功開啟 AIToolLauncher 2.0 大廳。"), daemon=True).start()

    def init_settings(self):
        self.settings_panel = SettingsPanel(self.settings_file, self)
        self.settings = self.settings_panel.settings
        self.settings_panel.settingsChanged.connect(self.apply_live_settings)

    def init_window(self):
        self.setWindowTitle(f"AI Tool Launcher 2.0 [收納盒模式] v{VERSION}")
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(960, 680)
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

    def toggle_pin_topmost(self):
        self.is_topmost = not self.is_topmost
        self.settings["always_on_top"] = self.is_topmost
        self.settings_panel.save_settings()
        self.update_pin_button_state()
        set_native_topmost(self.winId(), self.is_topmost)

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
                            # 自適應路徑修復 (支援 2.0\CloudTools 與 根目錄 CloudTools 互轉)
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
                    if modified:
                        self.save_registry()
                    return data
            except Exception:
                pass
        return {"tools": []}

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

        # 2. 圖標大小
        icon_size = s.get("icon_size", 56)
        if hasattr(self, "box_lobby"):
            self.box_lobby.update_icon_size(icon_size)

        # 3. 視窗置頂
        set_native_topmost(self.winId(), self.is_topmost)

    def launch_tool(self, tool_data: dict):
        name = tool_data.get("name", "小工具")
        exe = tool_data.get("executable", "")
        wdir = tool_data.get("working_dir", "")

        # 自適應修復路徑
        if not os.path.exists(exe):
            if "2.0\\CloudTools" in exe and os.path.exists(exe.replace("2.0\\CloudTools", "CloudTools")):
                exe = exe.replace("2.0\\CloudTools", "CloudTools")
                wdir = wdir.replace("2.0\\CloudTools", "CloudTools")
            elif "\\CloudTools" in exe and os.path.exists(exe.replace("\\CloudTools", "\\2.0\\CloudTools")):
                exe = exe.replace("\\CloudTools", "\\2.0\\CloudTools")
                wdir = wdir.replace("\\CloudTools", "\\2.0\\CloudTools")

        if not os.path.exists(exe):
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

        InfoBar.success(
            title="🚀 工具已啟動",
            content=f"正在獨立背景進程執行 【{name}】...",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

        def _run():
            try:
                # 0x00000008 (DETACHED_PROCESS) | 0x00000200 (CREATE_NEW_PROCESS_GROUP)
                # 徹底獨立的 Windows Process，不依附啟動器，Launcher 關閉也不會影響小工具
                detached_flags = 0x00000008 | 0x00000200

                if exe.endswith(".py"):
                    python_exe = sys.executable
                    if "python.exe" in python_exe.lower():
                        cand = python_exe.lower().replace("python.exe", "pythonw.exe")
                        if os.path.exists(cand):
                            python_exe = cand

                    safe_app_id = re.sub(r'[^a-zA-Z0-9_]', '_', name)

                    # 搜尋工具的最佳圖示
                    icon_file = ""
                    for cand in [
                        "assets/icon.png", "assets/icon.ico", "resources/icon.png", 
                        "resources/icon.ico", "icon.png", "icon/mic.png", "app.ico"
                    ]:
                        cand_path = os.path.join(wdir, cand)
                        if os.path.exists(cand_path):
                            icon_file = cand_path
                            break

                    # 注入獨立 AppUserModelID 與全自動 Qt setWindowIcon 攔截器
                    boot_code = f"""import ctypes, sys, os
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(r'AITool.{safe_app_id}')
except Exception:
    pass

sys.path.insert(0, r'{wdir}')
os.chdir(r'{wdir}')

icon_path = r'{icon_file}'
if icon_path and os.path.exists(icon_path):
    for qt in ['PySide6', 'PyQt6', 'PySide2', 'PyQt5']:
        try:
            import importlib
            mod = importlib.import_module(f'{{qt}}.QtWidgets')
            gui = importlib.import_module(f'{{qt}}.QtGui')
            orig_init = mod.QApplication.__init__
            def make_patched_init(old_init, ic_path, gui_module):
                def _init(self, *args, **kwargs):
                    old_init(self, *args, **kwargs)
                    try:
                        self.setWindowIcon(gui_module.QIcon(ic_path))
                    except Exception:
                        pass
                return _init
            mod.QApplication.__init__ = make_patched_init(orig_init, icon_path, gui)
        except Exception:
            pass

sys.argv = [r'{exe}']
globs = {{'__name__': '__main__', '__file__': r'{exe}'}}
with open(r'{exe}', 'rb') as f:
    exec(compile(f.read(), r'{exe}', 'exec'), globs)
"""
                    subprocess.Popen(
                        [python_exe, "-c", boot_code],
                        cwd=wdir,
                        creationflags=detached_flags,
                        close_fds=True,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                elif exe.endswith((".bat", ".cmd")):
                    subprocess.Popen(
                        ["cmd.exe", "/c", exe],
                        cwd=wdir,
                        creationflags=detached_flags,
                        close_fds=True,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                else:
                    subprocess.Popen(
                        [exe],
                        cwd=wdir,
                        creationflags=detached_flags,
                        close_fds=True,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
            except Exception as e:
                send_identity_webhook(f"💥 工具異常: {name}", f"啟動失敗: {str(e)}")

        threading.Thread(target=_run, daemon=True).start()

    def install_cloud_tool(self, repo_data: dict):
        repo_name = repo_data.get("name", "小工具")
        InfoBar.info(
            title="📥 正在下載安裝",
            content=f"開始從 GitHub 下載 【{repo_name}】...",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3500,
            parent=self
        )

        def on_status(msg):
            pass

        def on_finished(success, msg, tool_entry):
            if success and tool_entry:
                self.registry["tools"] = [t for t in self.registry.get("tools", []) if t.get("name") != tool_entry["name"]]
                self.registry.setdefault("tools", []).append(tool_entry)
                self.save_registry()

                InfoBar.success(
                    title="🎉 安裝完成",
                    content=msg,
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=4000,
                    parent=self
                )
                self.box_lobby.refresh_all()
            else:
                InfoBar.error(
                    title="❌ 安裝失敗",
                    content=msg,
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=5000,
                    parent=self
                )

        install_cloud_repo_async(repo_data, self.cloud_tools_dir, sys.executable, on_status, on_finished)

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

        def on_status(msg):
            pass

        def on_finished(success, msg, updated_tool):
            if success:
                self.save_registry()
                InfoBar.success(
                    title="🟢 更新完成",
                    content=msg,
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3500,
                    parent=self
                )
                self.box_lobby.refresh_all()
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

        reinstall_tool_async(tool_data, sys.executable, on_status, on_finished)

    def uninstall_tool(self, tool_data: dict):
        name = tool_data.get("name", "小工具")
        
        w = MessageBox(
            f"🗑️ 確認移除 【{name}】",
            f"您確定要將 【{name}】 從收納盒中解除安裝嗎？\n\n若是雲端專案，將同時清除其本機資料夾，並重置為「未安裝」狀態。",
            self
        )
        if not w.exec():
            return

        # 1. 刪除資料夾 (若在 CloudTools)
        uninstall_tool(tool_data, self.cloud_tools_dir)

        # 2. 從 registry 移除
        self.registry["tools"] = [t for t in self.registry.get("tools", []) if t.get("name") != name]
        self.save_registry()

        InfoBar.success(
            title="🗑️ 已移除小工具",
            content=f"已成功將 【{name}】 從收納盒移除。",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        self.box_lobby.refresh_all()


def main():
    try:
        app = QApplication(sys.argv)
        setTheme(Theme.AUTO)
        setThemeColor("#9A70FF")
        
        window = AIToolLauncherV2()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "launcher_error.log")
        with open(log_path, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)

if __name__ == "__main__":
    main()
