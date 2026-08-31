import os, sys, subprocess
from PySide6.QtCore import Qt, Signal, QRectF, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy
)
from qfluentwidgets import (
    CardWidget, SimpleCardWidget, StrongBodyLabel, CaptionLabel,
    FluentIcon, RoundMenu, Action, ToolTipFilter, ToolTipPosition
)

def get_rounded_pixmap(src_pixmap: QPixmap, size: int, radius_ratio: float = 0.22) -> QPixmap:
    """
    將任意圖示裁切並繪製為圓角平滑圖示（iOS / macOS 現代風格）
    """
    if src_pixmap.isNull():
        return src_pixmap

    # 確保等比例縮放
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

    # 居中繪製
    x = (size - scaled.width()) // 2
    y = (size - scaled.height()) // 2
    painter.drawPixmap(x, y, scaled)
    painter.end()

    return dest


class ToolCardWidget(CardWidget):
    """
    單一小工具磁貼卡片 (無銳角、圓角圖示、懸浮微動效)
    """
    toolClicked = Signal(dict)

    def __init__(self, tool_data: dict, icon_size: int = 56, parent=None):
        super().__init__(parent)
        self.tool_data = tool_data
        self.icon_size = icon_size
        self.setCursor(Qt.PointingHandCursor)
        self.init_ui()

    def init_ui(self):
        # 依據圖示大小動態設置卡片寬高
        card_w = max(110, self.icon_size + 44)
        card_h = max(118, self.icon_size + 58)
        self.setFixedSize(card_w, card_h)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 10, 8, 8)
        self.layout.setSpacing(6)
        self.layout.setAlignment(Qt.AlignCenter)

        # 1. 圓角 App Icon
        self.icon_label = QLabel(self)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        self.update_icon()
        self.layout.addWidget(self.icon_label)

        # 2. Tool Title
        self.title_label = StrongBodyLabel(self.tool_data.get("name", "未命名工具"), self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 12px; line-height: 1.2;")
        self.layout.addWidget(self.title_label)

        # 3. ToolTip
        desc = self.tool_data.get("description", "無附加說明")
        exe_path = self.tool_data.get("executable", "")
        self.setToolTip(f"【{self.tool_data.get('name')}】\n{desc}\n路徑: {exe_path}")
        self.installEventFilter(ToolTipFilter(self, showDelay=250, position=ToolTipPosition.BOTTOM))

    def update_icon(self):
        raw_pixmap = self.get_tool_raw_pixmap()
        rounded_pixmap = get_rounded_pixmap(raw_pixmap, self.icon_size)
        self.icon_label.setPixmap(rounded_pixmap)

    def get_tool_raw_pixmap(self) -> QPixmap:
        working_dir = self.tool_data.get("working_dir", "")
        candidate_paths = [
            os.path.join(working_dir, "resources", "icon.png"),
            os.path.join(working_dir, "assets", "icon.png"),
            os.path.join(working_dir, "icon.png"),
            os.path.join(working_dir, "app.ico"),
            os.path.join(os.path.dirname(__file__), "..", "resources", "icon.png")
        ]
        for p in candidate_paths:
            if os.path.exists(p):
                return QPixmap(p)
        return QPixmap(os.path.join(os.path.dirname(__file__), "..", "resources", "icon.png"))

    def set_icon_size(self, size: int):
        self.icon_size = size
        card_w = max(110, self.icon_size + 44)
        card_h = max(118, self.icon_size + 58)
        self.setFixedSize(card_w, card_h)
        self.update_icon()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toolClicked.emit(self.tool_data)
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def show_context_menu(self, pos):
        menu = RoundMenu(parent=self)
        
        act_launch = Action(FluentIcon.PLAY, "啟動此工具 (Launch)", triggered=lambda: self.toolClicked.emit(self.tool_data))
        act_open_dir = Action(FluentIcon.FOLDER, "開啟所在資料夾 (Open Folder)", triggered=self.open_tool_folder)
        act_copy_path = Action(FluentIcon.COPY, "複製可執行檔路徑 (Copy Path)", triggered=self.copy_executable_path)

        menu.addAction(act_launch)
        menu.addSeparator()
        menu.addAction(act_open_dir)
        menu.addAction(act_copy_path)

        menu.exec(pos)

    def open_tool_folder(self):
        working_dir = self.tool_data.get("working_dir", "")
        if os.path.exists(working_dir):
            os.startfile(working_dir)

    def copy_executable_path(self):
        from PySide6.QtWidgets import QApplication
        exe_path = self.tool_data.get("executable", "")
        QApplication.clipboard().setText(exe_path)
