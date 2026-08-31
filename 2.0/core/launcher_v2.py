import os, sys, json, subprocess, threading
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QFrame
)
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon, SearchLineEdit,
    SubtitleLabel, CaptionLabel, InfoBar, InfoBarPosition, setTheme,
    Theme, setThemeColor, CardWidget
)

# Relative imports
try:
    from core.settings_panel import SettingsPanel
    from core.tool_box_widget import CategoryBoxWidget, ToolCardWidget
    from core.identity_manager import get_client_identity, send_identity_webhook, get_webhook_url
except ModuleNotFoundError:
    from settings_panel import SettingsPanel
    from tool_box_widget import CategoryBoxWidget, ToolCardWidget
    from identity_manager import get_client_identity, send_identity_webhook, get_webhook_url

VERSION = "2.0.1"


class BoxLobbyInterface(QWidget):
    """
    收納盒大廳主頁面 (Box Lobby Page)
    展示頂部搜尋欄與所有分類收納盒子
    """
    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self.setObjectName("boxLobbyInterface")
        self.box_widgets = []
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 20, 24, 20)
        self.layout.setSpacing(16)

        # 1. Top Header & Search Bar
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        self.title_label = SubtitleLabel("📦 AI 軟體收納盒 (AI Tool Box)", self)
        self.sub_label = CaptionLabel("點擊或雙擊任意工具即可啟動，支援右鍵選單與分類收納", self)
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.sub_label)
        top_bar.addLayout(title_box)
        top_bar.addStretch(1)

        self.search_input = SearchLineEdit(self)
        self.search_input.setPlaceholderText("🔍 搜尋工具名稱或描述...")
        self.search_input.setFixedWidth(260)
        self.search_input.textChanged.connect(self.on_search_changed)
        top_bar.addWidget(self.search_input)

        self.layout.addLayout(top_bar)

        # 2. Scroll Area for Category Boxes
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.box_layout = QVBoxLayout(self.container)
        self.box_layout.setContentsMargins(0, 0, 8, 0)
        self.box_layout.setSpacing(16)

        self.scroll_area.setWidget(self.container)
        self.layout.addWidget(self.scroll_area)

        self.load_and_render_tools()

    def load_and_render_tools(self, filter_text: str = ""):
        for b in self.box_widgets:
            b.deleteLater()
        self.box_widgets.clear()

        tools = self.parent_window.load_tools()
        icon_size = self.parent_window.settings.get("icon_size", 52)

        categories = {}
        for t in tools:
            name = t.get("name", "")
            desc = t.get("description", "")
            
            if filter_text:
                if filter_text.lower() not in name.lower() and filter_text.lower() not in desc.lower():
                    continue

            cat = "☁️ 雲端工具箱"
            if "本地" in name or "開發" in name or "SteamManifestUpdater\\src" in t.get("executable", ""):
                cat = "🛠️ 本地開發工具"
            elif "專屬" in name or "計畫書" in name:
                cat = "✨ 專屬私人工具"
            elif "PTT" in name or "控制器" in name:
                cat = "🎙️ 系統與音訊工具"

            if cat not in categories:
                categories[cat] = []
            categories[cat].append(t)

        if not categories:
            empty_card = CardWidget(self.container)
            elayout = QVBoxLayout(empty_card)
            elayout.setContentsMargins(20, 30, 20, 30)
            msg = SubtitleLabel("🔍 未找到符合條件的小工具", empty_card)
            msg.setAlignment(Qt.AlignCenter)
            elayout.addWidget(msg)
            self.box_layout.addWidget(empty_card)
            self.box_widgets.append(empty_card)
        else:
            for cat_name, cat_tools in categories.items():
                box = CategoryBoxWidget(cat_name, cat_tools, icon_size=icon_size, parent=self.container)
                box.toolLaunchRequested.connect(self.parent_window.launch_tool)
                self.box_layout.addWidget(box)
                self.box_widgets.append(box)

        self.box_layout.addStretch(1)

    def on_search_changed(self, text: str):
        self.load_and_render_tools(filter_text=text.strip())

    def update_icon_size(self, size: int):
        for b in self.box_widgets:
            if isinstance(b, CategoryBoxWidget):
                b.update_icon_size(size)


class AIToolLauncherV2(FluentWindow):
    """
    AIToolLauncher 2.0 主視窗 (Acrylic 收納盒大廳)
    """
    def __init__(self):
        super().__init__()
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "config")
        self.registry_file = os.path.join(self.config_dir, "registry.json")
        self.settings_file = os.path.join(self.config_dir, "v2_settings.json")

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

        self.resize(980, 680)
        self.setMinimumSize(780, 520)

        self.apply_live_settings(self.settings)

    def init_navigation(self):
        # 1. 收納盒大廳
        self.box_lobby = BoxLobbyInterface(self, self)
        self.addSubInterface(self.box_lobby, FluentIcon.FOLDER, "收納盒大廳", NavigationItemPosition.TOP)

        # 2. 個性化設定
        self.addSubInterface(self.settings_panel, FluentIcon.SETTING, "個性化設置", NavigationItemPosition.BOTTOM)

    def load_tools(self) -> list:
        # Check local registry or fallback to 1.0 registry
        paths = [
            self.registry_file,
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "1.0", "resources", "config", "registry.json")
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data.get("tools", [])
                except Exception:
                    pass
        return []

    def apply_live_settings(self, s: dict):
        self.settings = s

        opacity = s.get("window_opacity", 95) / 100.0
        self.setWindowOpacity(opacity)

        icon_size = s.get("icon_size", 52)
        if hasattr(self, "box_lobby"):
            self.box_lobby.update_icon_size(icon_size)

        always_top = s.get("always_on_top", False)
        flags = self.windowFlags()
        if always_top:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()

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


def main():
    app = QApplication(sys.argv)
    setTheme(Theme.AUTO)
    setThemeColor("#9A70FF")
    
    window = AIToolLauncherV2()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
