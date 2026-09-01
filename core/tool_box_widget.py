import os, sys, subprocess, webbrowser
from PySide6.QtCore import Qt, Signal, QRectF, QSize, QPoint
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor, QFont, QPen, QContextMenuEvent
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


class InnerCard(CardWidget):
    """
    純淨內部小卡，僅包含圖示與標題，零預留空白
    """
    def __init__(self, parent_wrapper):
        super().__init__(parent_wrapper)
        self.wrapper = parent_wrapper
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.wrapper.current_state != self.wrapper.STATE_INSTALLING:
                self.wrapper.toolClicked.emit(self.wrapper.data, self.wrapper.is_installed)
            event.accept()
            return
        elif event.button() == Qt.RightButton:
            if self.wrapper.current_state != self.wrapper.STATE_INSTALLING:
                self.wrapper.show_context_menu(event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent):
        if self.wrapper.current_state != self.wrapper.STATE_INSTALLING:
            self.wrapper.show_context_menu(event.globalPos())
        event.accept()


class ToolCardWidget(QWidget):
    """
    小工具磁貼卡片
    特點：
    1. 卡片佈局零預留高度 (Zero Height Reserved)，尺寸緊湊純粹。
    2. 狀態膠囊以獨立圖層 (Topmost Overlay Layer) 懸浮於卡片底緣，完整顯示絕不被裁切 (No Clipping)，零排版推擠。
    3. 全域響應右鍵選單與極速秒級收藏切換。
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
        self.parent_flow_widget = parent

        self.cloudIconLoaded.connect(self.on_cloud_icon_ready)
        self.init_ui()

        # 當小卡被銷毀時，連帶銷毀懸浮於父層圖層的狀態標籤
        self.destroyed.connect(self._on_destroyed)

    def _on_destroyed(self):
        if hasattr(self, "status_badge") and self.status_badge:
            try:
                self.status_badge.deleteLater()
            except Exception:
                pass

    def init_ui(self):
        card_w = max(112, self.icon_size + 48)
        card_h = max(104, self.icon_size + 48)

        # 鎖定 Widget 緊湊尺寸 (零多餘預留空間)
        self.setFixedSize(card_w, card_h)

        # 1. 內部卡片本體 (填滿整個區域，比例完美)
        self.card = InnerCard(self)
        self.card.setGeometry(0, 0, card_w, card_h)

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(4, 8, 4, 6)
        self.card_layout.setSpacing(4)
        self.card_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # 圓角圖標
        self.icon_label = QLabel(self.card)
        self.icon_label.setFixedSize(self.icon_size, self.icon_size)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        self.update_icon()
        self.card_layout.addWidget(self.icon_label, 0, Qt.AlignCenter)

        # 非同步預載入 GitHub 雲端真實圖示
        repo_name = self.data.get("repo_name") or self.data.get("name", "")
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "cache", "icons")
        get_cloud_icon_async(repo_name, cache_dir, lambda p: self.cloudIconLoaded.emit(p))

        # 名稱 (高度 34px，支援 2 行換行)
        name = self.data.get("name", "未命名工具")
        self.title_label = StrongBodyLabel(name, self.card)
        self.title_label.setFixedSize(card_w - 8, 34)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.title_label.setStyleSheet("font-size: 12px; line-height: 1.2;")
        self.card_layout.addWidget(self.title_label, 0, Qt.AlignCenter)

        # 2. 獨立圖層狀態膠囊 (依附於父容器最上層，絕不受限於卡片邊界裁剪)
        badge_parent = self.parent_flow_widget if self.parent_flow_widget else self
        self.status_badge = CaptionLabel("", badge_parent)
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.status_badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.status_badge.hide()

        # 初始狀態樣式
        self.apply_state(self.STATE_IDLE)

        # 3. ToolTip
        self.update_tooltip()
        self.card.installEventFilter(ToolTipFilter(self.card, showDelay=250, position=ToolTipPosition.BOTTOM))

    def moveEvent(self, event):
        super().moveEvent(event)
        self.update_badge_pos()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_badge_pos()

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, "status_badge") and self.status_badge:
            self.status_badge.hide()

    def showEvent(self, event):
        super().showEvent(event)
        if self.current_state != self.STATE_IDLE or not self.is_installed:
            self.status_badge.show()
            self.update_badge_pos()

    def update_badge_pos(self):
        """
        圖層懸浮定位：精確懸浮於卡片底緣（跨越卡片邊框與間距），在父容器圖層頂層完整繪製，絕不被切齊！
        """
        if not hasattr(self, "status_badge") or self.status_badge is None:
            return
        if not self.isVisible() or self.status_badge.isHidden():
            return

        self.status_badge.adjustSize()
        bw = max(68, self.status_badge.sizeHint().width() + 14)
        bh = 18

        if self.status_badge.parent() == self:
            bx = (self.width() - bw) // 2
            by = self.height() - 10
        else:
            bx = self.x() + (self.width() - bw) // 2
            by = self.y() + self.height() - 10

        self.status_badge.setGeometry(bx, by, bw, bh)
        self.status_badge.raise_()

    def update_tooltip(self):
        name = self.data.get("name", "未命名工具")
        desc = self.data.get("description") or "GitHub 雲端工具"
        fav_hint = "【⭐ 已收藏】\n" if self.is_favorite else ""
        if self.is_installed:
            exe_path = self.data.get("executable", "")
            self.card.setToolTip(f"{fav_hint}【{name}】 (已安裝)\n{desc}\n路徑: {exe_path}")
        else:
            url = self.data.get("html_url") or self.data.get("clone_url", "")
            self.card.setToolTip(f"{fav_hint}【{name}】 (未安裝 - 雲端專案)\n{desc}\n倉庫: {url}")

    def set_favorite(self, is_favorite: bool):
        self.is_favorite = is_favorite
        self.update_icon()
        self.update_tooltip()

    def apply_state(self, state: str):
        """
        切換並套用卡片與頂層懸浮狀態標籤外觀 (頂層圖層渲染，零裁切，零推擠)
        """
        self.current_state = state

        if state == self.STATE_INSTALLING:
            # 📥 安裝中 (偏黑卡片 + 藍色虛線框 + 頂層浮動進度膠囊)
            self.card.setStyleSheet("""
                CardWidget {
                    background-color: rgba(18, 18, 20, 0.85);
                    border: 1.5px dashed rgba(96, 205, 255, 0.8);
                    border-radius: 8px;
                }
            """)
            self.status_badge.setText(f"📥 安裝中 {self.install_progress}%")
            self.status_badge.setStyleSheet("""
                color: #60CDFF;
                font-size: 10px;
                font-weight: bold;
                background: rgba(18, 32, 54, 0.95);
                border: 1px solid #60CDFF;
                border-radius: 9px;
                padding: 1px 6px;
            """)
            self.status_badge.show()
            self.update_badge_pos()

        elif state == self.STATE_RUNNING:
            # 🟢 已開啟 (翡翠綠邊框 + 頂層浮動運行中膠囊標籤)
            self.card.setStyleSheet("""
                CardWidget {
                    background-color: rgba(16, 185, 129, 0.15);
                    border: 2px solid #10B981;
                    border-radius: 8px;
                }
                CardWidget:hover {
                    background-color: rgba(16, 185, 129, 0.24);
                    border: 2px solid #34D399;
                }
            """)
            self.status_badge.setText("🟢 運行中")
            self.status_badge.setStyleSheet("""
                color: #34D399;
                font-size: 10px;
                font-weight: bold;
                background: rgba(10, 36, 24, 0.95);
                border: 1px solid #10B981;
                border-radius: 9px;
                padding: 1px 6px;
            """)
            self.status_badge.show()
            self.update_badge_pos()

        elif state == self.STATE_ERROR:
            # 🔴 錯誤 (緋紅邊框 + 頂層浮動錯誤膠囊)
            self.card.setStyleSheet("""
                CardWidget {
                    background-color: rgba(239, 68, 68, 0.15);
                    border: 2px solid #EF4444;
                    border-radius: 8px;
                }
                CardWidget:hover {
                    background-color: rgba(239, 68, 68, 0.24);
                    border: 2px solid #F87171;
                }
            """)
            self.status_badge.setText("🔴 啟動錯誤")
            self.status_badge.setStyleSheet("""
                color: #F87171;
                font-size: 10px;
                font-weight: bold;
                background: rgba(45, 15, 15, 0.95);
                border: 1px solid #EF4444;
                border-radius: 9px;
                padding: 1px 6px;
            """)
            self.status_badge.show()
            self.update_badge_pos()

        else:
            # ⚪ 未開啟 (鮮明原色、預設精緻半透明磨砂卡片)
            self.card.setStyleSheet("""
                CardWidget {
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                }
                CardWidget:hover {
                    background-color: rgba(255, 255, 255, 0.11);
                    border: 1px solid rgba(255, 255, 255, 0.18);
                }
            """)
            if not self.is_installed:
                self.status_badge.setText("☁️ 點擊安裝")
                self.status_badge.setStyleSheet("""
                    color: #D8B4FE;
                    font-size: 10px;
                    font-weight: bold;
                    background: rgba(35, 18, 50, 0.95);
                    border: 1px solid #9A70FF;
                    border-radius: 9px;
                    padding: 1px 6px;
                """)
                self.status_badge.show()
                self.update_badge_pos()
            else:
                self.status_badge.setText("")
                self.status_badge.hide()

        self.update_icon()

    def set_install_progress(self, progress: int, status_text: str = ""):
        """
        更新安裝進度文字 (頂層圖層懸浮顯示，零裁切，零推擠)
        """
        self.install_progress = max(0, min(100, progress))
        if self.current_state != self.STATE_INSTALLING:
            self.current_state = self.STATE_INSTALLING
            self.apply_state(self.STATE_INSTALLING)

        text = status_text or f"📥 安裝中 {self.install_progress}%"
        self.status_badge.setText(text)
        self.status_badge.show()
        self.update_badge_pos()

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
        card_h = max(104, self.icon_size + 48)
        self.setFixedSize(card_w, card_h)
        self.card.setGeometry(0, 0, card_w, card_h)
        self.icon_label.setFixedSize(self.icon_size, self.icon_size)
        self.title_label.setFixedSize(card_w - 8, 34)
        self.update_badge_pos()
        self.update_icon()

    def show_context_menu(self, pos: QPoint):
        menu = RoundMenu(parent=self)

        # 收藏/取消收藏動作
        if self.is_favorite:
            act_fav = Action(FluentIcon.UNPIN, "⭐ 取消收藏 (Remove Favorite)", triggered=lambda: self.toggleFavoriteRequested.emit(self.data))
        else:
            act_fav = Action(FluentIcon.HEART, "⭐ 加入收藏 (Add to Favorite)", triggered=lambda: self.toggleFavoriteRequested.emit(self.data))

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
