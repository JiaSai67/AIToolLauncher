import os, sys, subprocess, webbrowser
from PySide6.QtCore import Qt, Signal, QRectF, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy
)
from qfluentwidgets import (
    CardWidget, StrongBodyLabel, CaptionLabel,
    FluentIcon, RoundMenu, Action, ToolTipFilter, ToolTipPosition
)

try:
    from core.cloud_manager import get_cloud_icon_async
except ModuleNotFoundError:
    from cloud_manager import get_cloud_icon_async


def get_rounded_pixmap(src_pixmap: QPixmap, size: int, radius_ratio: float = 0.22) -> QPixmap:
    """
    將任意圖示裁切並繪製為最高解析度、鮮明原色的平滑圓角圖示
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
    支援狀態：
    1. 未開啟 (IDLE)       - 原色鮮明、精緻半透明磨砂卡片，圖標置中
    2. 已開啟 (RUNNING)    - 翡翠綠 (邊框與標籤)，再次點選直接呼叫軟體置頂
    3. 錯誤   (ERROR)      - 緋紅 (邊框與標籤)
    4. 安裝中 (INSTALLING) - 藍色虛線邊框與進度文字
    5. 收藏功能 (FAVORITE) - 右鍵新增/取消收藏，右上角點綴金色星標
    """
    toolClicked = Signal(dict, bool)           # (tool_data, is_installed)
    installRequested = Signal(dict)            # (repo_data)
    reinstallRequested = Signal(dict)          # (tool_data)
    uninstallRequested = Signal(dict)          # (tool_data)
    toggleFavoriteRequested = Signal(dict)     # (tool_data)
    cloudIconLoaded = Signal(str)              # (cached_icon_path)

    STATE_IDLE = "idle"
    STATE_RUNNING = "running"
    STATE_ERROR = "error"
    STATE_INSTALLING = "installing"

    def __init__(self, data: dict, is_installed: bool = True, is_favorite: bool = False, icon_size: int = 56, parent=None):
        super().__init__(parent)
        self.data = data
        self.is_installed = is_installed
        self.is_favorite = is_favorite
        self.icon_size = icon_size
        self.current_state = self.STATE_IDLE
        self.install_progress = 0

        self.setCursor(Qt.PointingHandCursor)
        self.cloudIconLoaded.connect(self.on_cloud_icon_ready)
        self.init_ui()

    def init_ui(self):
        card_w = max(112, self.icon_size + 48)
        card_h = max(120, self.icon_size + 56)
        self.setFixedSize(card_w, card_h)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(6)
        self.layout.setAlignment(Qt.AlignCenter)

        # 1. 圓角圖標 (絕對置中)
        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(self.icon_size, self.icon_size)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        self.update_icon()
        self.layout.addWidget(self.icon_label, 0, Qt.AlignCenter)

        # 非同步預載入 GitHub 雲端真實圖示
        repo_name = self.data.get("repo_name") or self.data.get("name", "")
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "cache", "icons")
        get_cloud_icon_async(repo_name, cache_dir, lambda p: self.cloudIconLoaded.emit(p))

        # 2. 名稱 (置中)
        name = self.data.get("name", "未命名工具")
        self.title_label = StrongBodyLabel(name, self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 12px; line-height: 1.2;")
        self.layout.addWidget(self.title_label, 0, Qt.AlignCenter)

        # 3. 狀態標籤 (置中)
        self.badge_label = CaptionLabel("", self)
        self.badge_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.badge_label, 0, Qt.AlignCenter)

        # 初始狀態樣式
        self.apply_state(self.STATE_IDLE)

        # 4. ToolTip
        desc = self.data.get("description") or "GitHub 雲端工具"
        fav_hint = "【⭐ 已收藏】\n" if self.is_favorite else ""
        if self.is_installed:
            exe_path = self.data.get("executable", "")
            self.setToolTip(f"{fav_hint}【{name}】 (已安裝)\n{desc}\n路徑: {exe_path}")
        else:
            url = self.data.get("html_url") or self.data.get("clone_url", "")
            self.setToolTip(f"{fav_hint}【{name}】 (未安裝 - 雲端專案)\n{desc}\n倉庫: {url}")

        self.installEventFilter(ToolTipFilter(self, showDelay=250, position=ToolTipPosition.BOTTOM))

    def set_favorite(self, is_favorite: bool):
        self.is_favorite = is_favorite
        self.update_icon()

    def apply_state(self, state: str):
        """
        切換並套用卡片外觀
        """
        self.current_state = state

        if state == self.STATE_INSTALLING:
            # 📥 安裝中 (偏黑卡片 + 藍色虛線框 + 進度標籤)
            self.setStyleSheet("""
                ToolCardWidget {
                    background-color: rgba(18, 18, 20, 0.75);
                    border: 1.5px dashed rgba(96, 205, 255, 0.6);
                    border-radius: 8px;
                }
            """)
            self.badge_label.setText(f"📥 安裝中 {self.install_progress}%")
            self.badge_label.setStyleSheet("color: #60CDFF; font-size: 10px; font-weight: bold;")
            self.badge_label.show()

        elif state == self.STATE_RUNNING:
            # 🟢 已開啟 (翡翠綠 + 運行中標籤)
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
            # ⚪ 未開啟 (鮮明原色、預設精緻半透明磨砂卡片)
            self.setStyleSheet("""
                ToolCardWidget {
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                }
                ToolCardWidget:hover {
                    background-color: rgba(255, 255, 255, 0.11);
                    border: 1px solid rgba(255, 255, 255, 0.18);
                }
            """)
            if not self.is_installed:
                self.badge_label.setText("☁️ 點擊安裝")
                self.badge_label.setStyleSheet("color: #9A70FF; font-size: 10px; font-weight: bold;")
                self.badge_label.show()
            else:
                self.badge_label.hide()

        self.update_icon()

    def set_install_progress(self, progress: int, status_text: str = ""):
        """
        更新安裝進度文字
        """
        self.install_progress = max(0, min(100, progress))
        if self.current_state != self.STATE_INSTALLING:
            self.current_state = self.STATE_INSTALLING
            self.apply_state(self.STATE_INSTALLING)

        text = status_text or f"📥 安裝中 {self.install_progress}%"
        self.badge_label.setText(text)

    def on_cloud_icon_ready(self, icon_path: str):
        if os.path.exists(icon_path):
            self.update_icon()

    def update_icon(self):
        raw_pixmap = self.get_tool_raw_pixmap()
        rounded_pixmap = get_rounded_pixmap(raw_pixmap, self.icon_size)

        if self.is_favorite:
            # 在右上角繪製小巧亮眼的金色星標
            fav_pixmap = QPixmap(rounded_pixmap)
            painter = QPainter(fav_pixmap)
            painter.setRenderHint(QPainter.Antialiasing, True)
            star_size = max(14, int(self.icon_size * 0.32))

            # 深色半透明小圓底
            painter.setBrush(QColor(18, 18, 22, 210))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self.icon_size - star_size - 1, 1, star_size, star_size)

            # 金色星星
            painter.setPen(QColor(255, 215, 0))
            font = painter.font()
            font.setPixelSize(int(star_size * 0.75))
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QRectF(self.icon_size - star_size - 1, 1, star_size, star_size), Qt.AlignCenter, "★")
            painter.end()
            self.icon_label.setPixmap(fav_pixmap)
        else:
            self.icon_label.setPixmap(rounded_pixmap)

    def get_tool_raw_pixmap(self) -> QPixmap:
        default_icon = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icon.png")
        repo_name = self.data.get("repo_name") or self.data.get("name", "")

        # 1. 優先檢查本地快取的專案專屬圖示 (resources/cache/icons/{repo_name}.png)
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "cache", "icons")
        for cand in [repo_name, repo_name.replace(" ", ""), self.data.get("name", "")]:
            if cand:
                cached_file = os.path.join(cache_dir, f"{cand}.png")
                if os.path.exists(cached_file) and os.path.getsize(cached_file) > 0:
                    return QPixmap(cached_file)

        # 2. 檢查工作目錄內的圖示
        working_dir = self.data.get("working_dir", "")
        if working_dir and os.path.exists(working_dir):
            candidate_paths = [
                os.path.join(working_dir, "assets", "icon.png"),
                os.path.join(working_dir, "icon", "mic.png"),
                os.path.join(working_dir, "resources", "icon.png"),
                os.path.join(working_dir, "assets", "icon.ico"),
                os.path.join(working_dir, "icon.png"),
                os.path.join(working_dir, "app.ico")
            ]
            for p in candidate_paths:
                if os.path.exists(p):
                    return QPixmap(p)

        return QPixmap(default_icon)

    def set_icon_size(self, size: int):
        self.icon_size = size
        card_w = max(112, self.icon_size + 48)
        card_h = max(120, self.icon_size + 56)
        self.setFixedSize(card_w, card_h)
        self.icon_label.setFixedSize(self.icon_size, self.icon_size)
        self.update_icon()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.current_state != self.STATE_INSTALLING:
                self.toolClicked.emit(self.data, self.is_installed)
        elif event.button() == Qt.RightButton:
            if self.current_state != self.STATE_INSTALLING:
                self.show_context_menu(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def show_context_menu(self, pos):
        menu = RoundMenu(parent=self)

        # 收藏/取消收藏動作
        if self.is_favorite:
            act_fav = Action(FluentIcon.STAR, "⭐ 取消收藏 (Remove Favorite)", triggered=lambda: self.toggleFavoriteRequested.emit(self.data))
        else:
            act_fav = Action(FluentIcon.FAVORITE, "⭐ 加入收藏 (Add to Favorite)", triggered=lambda: self.toggleFavoriteRequested.emit(self.data))

        if self.is_installed:
            # === 已安裝小工具選單 ===
            act_launch = Action(FluentIcon.PLAY, "啟動工具 (Launch)", triggered=lambda: self.toolClicked.emit(self.data, True))
            act_reinstall = Action(FluentIcon.SYNC, "重新拉取與安裝 (Reinstall / Git Pull)", triggered=lambda: self.reinstallRequested.emit(self.data))
            act_open_dir = Action(FluentIcon.FOLDER, "開啟所在資料夾 (Open Folder)", triggered=self.open_tool_folder)
            act_copy_path = Action(FluentIcon.COPY, "複製執行檔路徑 (Copy Path)", triggered=self.copy_executable_path)
            act_uninstall = Action(FluentIcon.DELETE, "移除小工具 (Uninstall)", triggered=lambda: self.uninstallRequested.emit(self.data))

            menu.addAction(act_launch)
            menu.addAction(act_fav)
            menu.addSeparator()
            menu.addAction(act_reinstall)
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
            menu.addAction(act_fav)
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
