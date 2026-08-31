import os, sys, json, subprocess, threading, ctypes

# Guard for pythonw (sys.stdout/stderr are None in GUI mode)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QScrollArea, QFrame, QSizePolicy
)
from qfluentwidgets import (
    MSFluentWindow, NavigationItemPosition, FluentIcon, SearchLineEdit,
    SubtitleLabel, CaptionLabel, InfoBar, InfoBarPosition, setTheme,
    Theme, setThemeColor, CardWidget, BodyLabel, TransparentToolButton,
    SegmentedWidget, MessageBox
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

VERSION = "2.0.3"


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


class BoxLobbyInterface(QWidget):
    """
    收納盒大廳主頁面 (支援「已安裝」與「未安裝/雲端」分頁切換)
    """
    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self.setObjectName("boxLobbyInterface")
        self.current_category = "installed"
        self.card_widgets = []
        self.cloud_repos = []
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(28, 20, 28, 20)
        self.layout.setSpacing(14)

        # 1. 頂部工具列 (標題 + 分段切換 + 搜尋框 + 重新整理)
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        self.title_label = SubtitleLabel("📦 軟體收納盒 (Tool Box)", self)
        self.sub_label = CaptionLabel("點擊啟動工具，支援右鍵選單重新拉取、解除安裝與雲端下載", self)
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.sub_label)
        top_bar.addLayout(title_box)
        top_bar.addStretch(1)

        # 分段切換器 (已安裝 / 未安裝)
        self.pivot = SegmentedWidget(self)
        self.pivot.addItem("installed", "🟢 已安裝", onClick=lambda: self.switch_category("installed"))
        self.pivot.addItem("uninstalled", "☁️ 未安裝", onClick=lambda: self.switch_category("uninstalled"))
        self.pivot.setCurrentItem("installed")
        top_bar.addWidget(self.pivot)

        top_bar.addSpacing(16)

        # 搜尋框
        self.search_input = SearchLineEdit(self)
        self.search_input.setPlaceholderText("🔍 搜尋小工具...")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self.on_search_changed)
        top_bar.addWidget(self.search_input)

        # 重新整理按鈕
        self.btn_refresh = TransparentToolButton(FluentIcon.SYNC, self)
        self.btn_refresh.setToolTip("重新整理列表與雲端庫")
        self.btn_refresh.clicked.connect(self.refresh_all)
        top_bar.addWidget(self.btn_refresh)

        self.layout.addLayout(top_bar)

        # 2. 工具卡片平鋪網格
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setContentsMargins(4, 6, 8, 6)
        self.grid_layout.setSpacing(18)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll_area.setWidget(self.container)
        self.layout.addWidget(self.scroll_area)

        # 初始載入
        self.load_and_render_tools()
        self.fetch_cloud_repos_async()

    def switch_category(self, cat: str):
        self.current_category = cat
        self.load_and_render_tools(filter_text=self.search_input.text().strip())

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
                # 更新分頁標籤計數
                self.update_tab_counts()
                if self.current_category == "uninstalled":
                    self.load_and_render_tools(filter_text=self.search_input.text().strip())

        fetch_github_repos(_callback)

    def update_tab_counts(self):
        installed_tools = self.parent_window.load_tools()
        installed_count = len(installed_tools)
        installed_names = [t.get("name", "").lower() for t in installed_tools]
        
        uninstalled_count = 0
        for r in self.cloud_repos:
            rname = r.get("name", "").lower()
            if rname not in installed_names:
                uninstalled_count += 1

        # 更新 SegmentedWidget 文字
        try:
            self.pivot.items['installed'].setText(f"🟢 已安裝 ({installed_count})")
            if uninstalled_count > 0:
                self.pivot.items['uninstalled'].setText(f"☁️ 未安裝 ({uninstalled_count})")
        except Exception:
            pass

    def load_and_render_tools(self, filter_text: str = ""):
        for c in self.card_widgets:
            c.deleteLater()
        self.card_widgets.clear()

        installed_tools = self.parent_window.load_tools()
        icon_size = self.parent_window.settings.get("icon_size", 56)
        matched_items = []

        if self.current_category == "installed":
            # === 已安裝清單 ===
            for t in installed_tools:
                name = t.get("name", "")
                desc = t.get("description", "")
                if filter_text:
                    if filter_text.lower() not in name.lower() and filter_text.lower() not in desc.lower():
                        continue
                matched_items.append((t, True))
        else:
            # === 未安裝 / 雲端清單 ===
            installed_names = [t.get("name", "").lower() for t in installed_tools]
            installed_wdirs = [os.path.basename(t.get("working_dir", "")).lower() for t in installed_tools]

            for repo in self.cloud_repos:
                rname = repo.get("name", "")
                rdesc = repo.get("description") or ""
                # 若已安裝則跳過
                if rname.lower() in installed_names or rname.lower() in installed_wdirs:
                    continue

                if filter_text:
                    if filter_text.lower() not in rname.lower() and filter_text.lower() not in rdesc.lower():
                        continue
                matched_items.append((repo, False))

        if not matched_items:
            empty_card = CardWidget(self.container)
            elayout = QVBoxLayout(empty_card)
            elayout.setContentsMargins(30, 40, 30, 40)
            msg_text = "🔍 未找到已安裝的小工具" if self.current_category == "installed" else "☁️ 雲端小工具皆已安裝完畢"
            msg = SubtitleLabel(msg_text, empty_card)
            msg.setAlignment(Qt.AlignCenter)
            elayout.addWidget(msg)
            self.grid_layout.addWidget(empty_card, 0, 0, 1, 4)
            self.card_widgets.append(empty_card)
            return

        cols = 5
        for idx, (data, is_inst) in enumerate(matched_items):
            row = idx // cols
            col = idx % cols
            card = ToolCardWidget(data, is_installed=is_inst, icon_size=icon_size, parent=self.container)
            
            # Connect Signals
            card.toolClicked.connect(self.on_tool_clicked)
            card.installRequested.connect(self.parent_window.install_cloud_tool)
            card.reinstallRequested.connect(self.parent_window.reinstall_tool)
            card.uninstallRequested.connect(self.parent_window.uninstall_tool)

            self.grid_layout.addWidget(card, row, col)
            self.card_widgets.append(card)

    def on_tool_clicked(self, data: dict, is_installed: bool):
        if is_installed:
            self.parent_window.launch_tool(data)
        else:
            self.parent_window.install_cloud_tool(data)

    def on_search_changed(self, text: str):
        self.load_and_render_tools(filter_text=text.strip())

    def update_icon_size(self, size: int):
        for card in self.card_widgets:
            if isinstance(card, ToolCardWidget):
                card.set_icon_size(size)


class AIToolLauncherV2(MSFluentWindow):
    """
    AIToolLauncher 2.0 主視窗 (原生 Acrylic 壓克力圓角收納盒大廳)
    """
    def __init__(self):
        super().__init__()
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "config")
        self.cloud_tools_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "CloudTools")
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

        self.resize(960, 640)
        self.setMinimumSize(740, 500)

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
                    return json.load(f)
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
            content=f"正在背景執行 【{name}】...",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

        def _run():
            try:
                if exe.endswith(".py"):
                    subprocess.Popen([sys.executable, exe], cwd=wdir)
                else:
                    subprocess.Popen([exe], cwd=wdir)
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
                # 註冊進 registry
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
