import os, sys, subprocess, webbrowser
from PySide6.QtCore import Qt, Signal, QRectF, QSize, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy
)
from qfluentwidgets import (
    CardWidget, SimpleCardWidget, StrongBodyLabel, CaptionLabel,
    FluentIcon, RoundMenu, Action, ToolTipFilter, ToolTipPosition,
    ProgressRing
)

try:
    from core.cloud_manager import get_cloud_icon_async
except ModuleNotFoundError:
    from cloud_manager import get_cloud_icon_async

def get_rounded_pixmap(src_pixmap: QPixmap, size: int, radius_ratio: float = 0.22) -> QPixmap:
    """
    將任意圖示裁切並繪製為平滑圓角圖示
    """
    if src_pixmap.isNull():
        return src_pixmap

    scaled = src_pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    radius = max(6, int(size * radius_ratio))

    dest = QPixmap(size, size)
    dest.fill(Qt.transparent)

    painter = QPainter(dest)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    painter.setClipPath(path)

    x = (size - scaled.width()) // 2
    y = (size - scaled.height()) // 2
    painter.drawPixmap(x, y, scaled)
    painter.end()

    return dest


class ToolCardWidget(CardWidget):
    """
    小工具磁貼卡片
    支援 4 種啟動狀態之顏色與特效變化：
    1. 未開啟 (IDLE)       - 預設半透明壓克力卡片
    2. 已開啟 (RUNNING)    - 翡翠綠 (邊框與光暈)，再次點擊直接呼叫視窗置頂
    3. 錯誤   (ERROR)      - 緋紅 (邊框與光暈)
    4. 正在開啟中 (STARTING)- 科技藍，圖標替換為 0~100% 圓形進度環特效
    """
    toolClicked = Signal(dict, bool)         # (tool_data, is_installed)
    installRequested = Signal(dict)          # (repo_data)
    reinstallRequested = Signal(dict)        # (tool_data)
    uninstallRequested = Signal(dict)        # (tool_data)
    cloudIconLoaded = Signal(str)            # (cached_icon_path)

    STATE_IDLE = "idle"
    STATE_RUNNING = "running"
    STATE_ERROR = "error"
    STATE_STARTING = "starting"

    def __init__(self, data: dict, is_installed: bool = True, icon_size: int = 56, parent=None):
        super().__init__(parent)
        self.data = data
        self.is_installed = is_installed
        self.icon_size = icon_size
        self.current_state = self.STATE_IDLE
        self.setCursor(Qt.PointingHandCursor)
        self.cloudIconLoaded.connect(self.on_cloud_icon_ready)

        # 啟動進度條計時器 (提前初始化)
        self.progress_val = 0
        self.start_timer = QTimer(self)
        self.start_timer.setInterval(30)
        self.start_timer.timeout.connect(self._on_progress_step)

        self.init_ui()

    def init_ui(self):
        card_w = max(116, self.icon_size + 48)
        card_h = max(130, self.icon_size + 66)
        self.setFixedSize(card_w, card_h)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 10, 8, 8)
        self.layout.setSpacing(5)
        self.layout.setAlignment(Qt.AlignCenter)

        # 1. 圖標 / 進度條 容器
        self.icon_container = QWidget(self)
        self.icon_container.setFixedSize(self.icon_size, self.icon_size)
        self.icon_container.setStyleSheet("background: transparent;")
        self.icon_container_layout = QVBoxLayout(self.icon_container)
        self.icon_container_layout.setContentsMargins(0, 0, 0, 0)
        self.icon_container_layout.setAlignment(Qt.AlignCenter)

        # (A) 圓角靜態圖示
        self.icon_label = QLabel(self.icon_container)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        self.icon_container_layout.addWidget(self.icon_label)

        # (B) 啟動中 0~100% 圓形進度環
        self.progress_ring = ProgressRing(self.icon_container)
        self.progress_ring.setFixedSize(self.icon_size, self.icon_size)
        self.progress_ring.setTextVisible(True)
        self.progress_ring.setCustomBarColor("#0078D4", "#60CDFF")
        self.progress_ring.hide()
        self.icon_container_layout.addWidget(self.progress_ring)

        self.update_icon()
        self.layout.addWidget(self.icon_container)

        # 若為未安裝的雲端專案，非同步嘗試載入 GitHub 上的真實圖示
        if not self.is_installed:
            repo_name = self.data.get("name", "")
            cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "cache", "icons")
            get_cloud_icon_async(repo_name, cache_dir, lambda p: self.cloudIconLoaded.emit(p))

        # 2. 名稱
        name = self.data.get("name", "未命名工具")
        self.title_label = StrongBodyLabel(name, self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 12px; line-height: 1.2;")
        self.layout.addWidget(self.title_label)

        # 3. 狀態標籤
        self.badge_label = CaptionLabel("", self)
        self.badge_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.badge_label)

        # 初始狀態樣式
        self.apply_state(self.STATE_IDLE)

        # 5. ToolTip
        desc = self.data.get("description") or "GitHub 雲端工具"
        if self.is_installed:
            exe_path = self.data.get("executable", "")
            self.setToolTip(f"【{name}】 (已安裝)\n{desc}\n路徑: {exe_path}")
        else:
            url = self.data.get("html_url") or self.data.get("clone_url", "")
            self.setToolTip(f"【{name}】 (未安裝 - 雲端專案)\n{desc}\n倉庫: {url}")

        self.installEventFilter(ToolTipFilter(self, showDelay=250, position=ToolTipPosition.BOTTOM))

    def _safe_stop_timer(self):
        try:
            if hasattr(self, 'start_timer') and self.start_timer:
                self.start_timer.stop()
        except Exception:
            pass

    def _safe_start_timer(self):
        try:
            if hasattr(self, 'start_timer') and self.start_timer:
                self.start_timer.start()
        except Exception:
            pass

    def _show_progress_mode(self):
        try:
            if hasattr(self, 'icon_label') and self.icon_label:
                self.icon_label.hide()
        except Exception:
            pass
        try:
            if hasattr(self, 'progress_ring') and self.progress_ring:
                self.progress_ring.show()
        except Exception:
            pass

    def _show_icon_mode(self):
        try:
            if hasattr(self, 'progress_ring') and self.progress_ring:
                self.progress_ring.hide()
        except Exception:
            pass
        try:
            if hasattr(self, 'icon_label') and self.icon_label:
                self.icon_label.show()
        except Exception:
            pass

    def apply_state(self, state: str):
        """
        切換並套用卡片的 4 種狀態外觀
        """
        self.current_state = state

        if state == self.STATE_STARTING:
            # 🔵 正在開啟中 (科技藍 + 0~100% 圓形進度環)
            self._show_progress_mode()
            self.progress_val = 0
            try:
                if hasattr(self, 'progress_ring') and self.progress_ring:
                    self.progress_ring.setValue(0)
            except Exception:
                pass
            self._safe_start_timer()

            self.setStyleSheet("""
                ToolCardWidget {
                    background-color: rgba(0, 120, 212, 0.14);
                    border: 2px solid #0078D4;
                    border-radius: 8px;
                }
                ToolCardWidget:hover {
                    background-color: rgba(0, 120, 212, 0.22);
                    border: 2px solid #60CDFF;
                }
            """)
            self.badge_label.setText("🔵 正在啟動...")
            self.badge_label.setStyleSheet("color: #60CDFF; font-size: 10px; font-weight: bold;")
            self.badge_label.show()

        elif state == self.STATE_RUNNING:
            # 🟢 已開啟 (翡翠綠 + 運行中標籤)
            self._safe_stop_timer()
            self._show_icon_mode()

            self.setStyleSheet("""
                ToolCardWidget {
                    background-color: rgba(16, 185, 129, 0.14);
                    border: 2px solid #10B981;
                    border-radius: 8px;
                }
                ToolCardWidget:hover {
                    background-color: rgba(16, 185, 129, 0.22);
                    border: 2px solid #34D399;
                }
            """)
            self.badge_label.setText("🟢 運行中")
            self.badge_label.setStyleSheet("color: #34D399; font-size: 10px; font-weight: bold;")
            self.badge_label.show()

        elif state == self.STATE_ERROR:
            # 🔴 錯誤 (緋紅 + 錯誤標籤)
            self._safe_stop_timer()
            self._show_icon_mode()

            self.setStyleSheet("""
                ToolCardWidget {
                    background-color: rgba(239, 68, 68, 0.14);
                    border: 2px solid #EF4444;
                    border-radius: 8px;
                }
                ToolCardWidget:hover {
                    background-color: rgba(239, 68, 68, 0.22);
                    border: 2px solid #F87171;
                }
            """)
            self.badge_label.setText("🔴 啟動錯誤")
            self.badge_label.setStyleSheet("color: #F87171; font-size: 10px; font-weight: bold;")
            self.badge_label.show()

        else:
            # ⚪ 未開啟 (預設半透明壓克力卡片)
            self._safe_stop_timer()
            self._show_icon_mode()

            self.setStyleSheet("""
                ToolCardWidget {
                    background-color: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                }
                ToolCardWidget:hover {
                    background-color: rgba(255, 255, 255, 0.09);
                    border: 1px solid rgba(255, 255, 255, 0.16);
                }
            """)
            if not self.is_installed:
                self.badge_label.setText("☁️ 點擊安裝")
                self.badge_label.setStyleSheet("color: #9A70FF; font-size: 10px; font-weight: bold;")
                self.badge_label.show()
            else:
                self.badge_label.hide()

    def _on_progress_step(self):
        try:
            if self.progress_val < 95:
                self.progress_val += 5
                if hasattr(self, 'progress_ring') and self.progress_ring:
                    self.progress_ring.setValue(self.progress_val)
            else:
                if hasattr(self, 'progress_ring') and self.progress_ring:
                    self.progress_ring.setValue(99)
        except Exception:
            pass

    def complete_launch_success(self):
        """啟動完成並切換至綠色運行中"""
        try:
            if hasattr(self, 'progress_ring') and self.progress_ring:
                self.progress_ring.setValue(100)
        except Exception:
            pass
        self.apply_state(self.STATE_RUNNING)

    def complete_launch_failed(self):
        """啟動失敗並切換至紅色錯誤"""
        self.apply_state(self.STATE_ERROR)

    def on_cloud_icon_ready(self, icon_path: str):
        if os.path.exists(icon_path):
            raw_pixmap = QPixmap(icon_path)
            rounded = get_rounded_pixmap(raw_pixmap, self.icon_size)
            self.icon_label.setPixmap(rounded)

    def update_icon(self):
        raw_pixmap = self.get_tool_raw_pixmap()
        rounded_pixmap = get_rounded_pixmap(raw_pixmap, self.icon_size)
        self.icon_label.setPixmap(rounded_pixmap)

    def get_tool_raw_pixmap(self) -> QPixmap:
        default_icon = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icon.png")
        if self.is_installed:
            working_dir = self.data.get("working_dir", "")
            candidate_paths = [
                os.path.join(working_dir, "assets", "icon.png"),
                os.path.join(working_dir, "icon", "mic.png"),
                os.path.join(working_dir, "resources", "icon.png"),
                os.path.join(working_dir, "assets", "icon.ico"),
                os.path.join(working_dir, "icon.png"),
                os.path.join(working_dir, "app.ico"),
                default_icon
            ]
            for p in candidate_paths:
                if os.path.exists(p):
                    return QPixmap(p)
        else:
            repo_name = self.data.get("name", "")
            cached_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "cache", "icons", f"{repo_name}.png")
            if os.path.exists(cached_file):
                return QPixmap(cached_file)

        return QPixmap(default_icon)

    def set_icon_size(self, size: int):
        self.icon_size = size
        card_w = max(116, self.icon_size + 48)
        card_h = max(130, self.icon_size + 66)
        self.setFixedSize(card_w, card_h)
        self.icon_container.setFixedSize(self.icon_size, self.icon_size)
        self.progress_ring.setFixedSize(self.icon_size, self.icon_size)
        self.update_icon()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toolClicked.emit(self.data, self.is_installed)
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def show_context_menu(self, pos):
        menu = RoundMenu(parent=self)

        if self.is_installed:
            # === 已安裝小工具選單 ===
            act_launch = Action(FluentIcon.PLAY, "啟動工具 (Launch)", triggered=lambda: self.toolClicked.emit(self.data, True))
            act_reinstall = Action(FluentIcon.SYNC, "重新拉取與安裝 (Reinstall / Git Pull)", triggered=lambda: self.reinstallRequested.emit(self.data))
            act_open_dir = Action(FluentIcon.FOLDER, "開啟所在資料夾 (Open Folder)", triggered=self.open_tool_folder)
            act_copy_path = Action(FluentIcon.COPY, "複製執行檔路徑 (Copy Path)", triggered=self.copy_executable_path)
            act_uninstall = Action(FluentIcon.DELETE, "移除小工具 (Uninstall)", triggered=lambda: self.uninstallRequested.emit(self.data))

            menu.addAction(act_launch)
            menu.addAction(act_reinstall)
            menu.addSeparator()
            menu.addAction(act_open_dir)
            menu.addAction(act_copy_path)
            menu.addSeparator()
            menu.addAction(act_uninstall)
        else:
            # === 未安裝雲端小工具選單 ===
            act_install = Action(FluentIcon.DOWNLOAD, "下載並安裝此工具 (Install)", triggered=lambda: self.installRequested.emit(self.data))
            act_github = Action(FluentIcon.GLOBE, "在 GitHub 上查看 (View on GitHub)", triggered=self.open_github_page)
            act_copy_url = Action(FluentIcon.COPY, "複製倉庫網址 (Copy Git URL)", triggered=self.copy_git_url)

            menu.addAction(act_install)
            menu.addSeparator()
            menu.addAction(act_github)
            menu.addAction(act_copy_url)

        menu.exec(pos)

    def open_tool_folder(self):
        working_dir = self.data.get("working_dir", "")
        if os.path.exists(working_dir):
            os.startfile(working_dir)

    def copy_executable_path(self):
        from PySide6.QtWidgets import QApplication
        exe_path = self.data.get("executable", "")
        QApplication.clipboard().setText(exe_path)

    def open_github_page(self):
        url = self.data.get("html_url") or f"https://github.com/{self.data.get('full_name', '')}"
        if url:
            webbrowser.open(url)

    def copy_git_url(self):
        from PySide6.QtWidgets import QApplication
        url = self.data.get("clone_url") or self.data.get("html_url", "")
        QApplication.clipboard().setText(url)
