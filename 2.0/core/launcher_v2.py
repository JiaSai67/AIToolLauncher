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
    Theme, setThemeColor, CardWidget, BodyLabel
)

# Relative imports
try:
    from core.settings_panel import SettingsPanel
    from core.tool_box_widget import ToolCardWidget
    from core.identity_manager import get_client_identity, send_identity_webhook, get_webhook_url, install_global_exception_hook
except ModuleNotFoundError:
    from settings_panel import SettingsPanel
    from tool_box_widget import ToolCardWidget
    from identity_manager import get_client_identity, send_identity_webhook, get_webhook_url, install_global_exception_hook

# 立即安裝全域崩潰與異常攔截器 (含加密 Webhook 推播)
install_global_exception_hook()

VERSION = "2.0.2"


def set_native_topmost(win_id: int, is_topmost: bool):
    """
    使用 Windows 原生 Win32 API 設置視窗置頂，絕不觸發 Qt 重建視窗
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
    收納盒大廳主頁面 (全圖示平鋪網格)
    """
    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self.setObjectName("boxLobbyInterface")
        self.card_widgets = []
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(28, 24, 28, 24)
        self.layout.setSpacing(18)

        # 1. Top Header & Search Bar
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        self.title_label = SubtitleLabel("📦 軟體收納盒 (Tool Box)", self)
        self.sub_label = CaptionLabel("點擊或雙擊圖示即可啟動小工具，支援右鍵快捷選單", self)
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.sub_label)
        top_bar.addLayout(title_box)
        top_bar.addStretch(1)

        self.search_input = SearchLineEdit(self)
        self.search_input.setPlaceholderText("🔍 搜尋小工具...")
        self.search_input.setFixedWidth(240)
        self.search_input.textChanged.connect(self.on_search_changed)
        top_bar.addWidget(self.search_input)

        self.layout.addLayout(top_bar)

        # 2. Scroll Area for Tool Grid
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setContentsMargins(4, 8, 8, 8)
        self.grid_layout.setSpacing(18)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll_area.setWidget(self.container)
        self.layout.addWidget(self.scroll_area)

        self.load_and_render_tools()

    def load_and_render_tools(self, filter_text: str = ""):
        for c in self.card_widgets:
            c.deleteLater()
        self.card_widgets.clear()

        tools = self.parent_window.load_tools()
        icon_size = self.parent_window.settings.get("icon_size", 56)

        matched_tools = []
        for t in tools:
            name = t.get("name", "")
            desc = t.get("description", "")
            if filter_text:
                if filter_text.lower() not in name.lower() and filter_text.lower() not in desc.lower():
                    continue
            matched_tools.append(t)

        if not matched_tools:
            empty_card = CardWidget(self.container)
            elayout = QVBoxLayout(empty_card)
            elayout.setContentsMargins(30, 40, 30, 40)
            msg = SubtitleLabel("🔍 未找到符合條件的小工具", empty_card)
            msg.setAlignment(Qt.AlignCenter)
            elayout.addWidget(msg)
            self.grid_layout.addWidget(empty_card, 0, 0, 1, 4)
            self.card_widgets.append(empty_card)
            return

        cols = 5
        for idx, tool in enumerate(matched_tools):
            row = idx // cols
            col = idx % cols
            card = ToolCardWidget(tool, icon_size=icon_size, parent=self.container)
            card.toolClicked.connect(self.parent_window.launch_tool)
            self.grid_layout.addWidget(card, row, col)
            self.card_widgets.append(card)

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
        self.registry_file = os.path.join(self.config_dir, "registry.json")
        self.settings_file = os.path.join(self.config_dir, "v2_settings.json")

        self.init_settings()
        self.init_window()
        self.init_navigation()

        threading.Thread(target=lambda: send_identity_webhook("🚀 啟動 AIToolLauncher 2.0 (圓角收納盒模式)", "使用者已成功開啟 AIToolLauncher 2.0 大廳。"), daemon=True).start()

    def init_settings(self):
        self.settings_panel = SettingsPanel(self.settings_file, self)
        self.settings = self.settings_panel.settings
        self.settings_panel.settingsChanged.connect(self.apply_live_settings)

    def init_window(self):
        self.setWindowTitle(f"AI Tool Launcher 2.0 [收納盒模式] v{VERSION}")
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(920, 620)
        self.setMinimumSize(720, 480)

        self.apply_live_settings(self.settings)

    def init_navigation(self):
        # 1. 收納盒大廳
        self.box_lobby = BoxLobbyInterface(self, self)
        self.addSubInterface(self.box_lobby, FluentIcon.FOLDER, "收納盒大廳", position=NavigationItemPosition.TOP)

        # 2. 個性化設定
        self.addSubInterface(self.settings_panel, FluentIcon.SETTING, "個性化設置", position=NavigationItemPosition.BOTTOM)

    def load_tools(self) -> list:
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("tools", [])
            except Exception:
                pass
        return []

    def apply_live_settings(self, s: dict):
        self.settings = s

        # 1. 窗口透明度
        opacity = s.get("window_opacity", 95) / 100.0
        self.setWindowOpacity(opacity)

        # 2. 圖標大小
        icon_size = s.get("icon_size", 56)
        if hasattr(self, "box_lobby"):
            self.box_lobby.update_icon_size(icon_size)

        # 3. 視窗置頂 (使用 Win32 API 原生即時生效)
        always_top = s.get("always_on_top", False)
        set_native_topmost(self.winId(), always_top)

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
