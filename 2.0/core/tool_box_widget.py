import os, sys, subprocess
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel
)
from qfluentwidgets import (
    CardWidget, StrongBodyLabel, CaptionLabel, TransparentToolButton,
    FluentIcon, RoundMenu, Action, ToolTipFilter, ToolTipPosition
)

class ToolCardWidget(CardWidget):
    """
    單一工具磁貼卡片 (Tool Card)
    支援動態圖示縮放、懸浮微光動效、雙擊與點擊啟動
    """
    toolClicked = Signal(dict)

    def __init__(self, tool_data: dict, icon_size: int = 52, parent=None):
        super().__init__(parent)
        self.tool_data = tool_data
        self.icon_size = icon_size
        self.setCursor(Qt.PointingHandCursor)
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(self.icon_size * 2 + 30, self.icon_size + 70)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(6)
        self.layout.setAlignment(Qt.AlignCenter)

        # 1. App Icon
        self.icon_label = QLabel(self)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.update_icon()
        self.layout.addWidget(self.icon_label)

        # 2. Tool Title
        self.title_label = StrongBodyLabel(self.tool_data.get("name", "未命名工具"), self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        self.layout.addWidget(self.title_label)

        # ToolTip
        desc = self.tool_data.get("description", "無附加說明")
        exe_path = self.tool_data.get("executable", "")
        self.setToolTip(f"【{self.tool_data.get('name')}】\n{desc}\n路徑: {exe_path}")
        self.installEventFilter(ToolTipFilter(self, showDelay=300, position=ToolTipPosition.BOTTOM))

    def update_icon(self):
        pixmap = self.get_tool_pixmap()
        scaled = pixmap.scaled(
            self.icon_size, self.icon_size,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.icon_label.setPixmap(scaled)

    def get_tool_pixmap(self) -> QPixmap:
        working_dir = self.tool_data.get("working_dir", "")
        candidate_paths = [
            os.path.join(working_dir, "resources", "icon.png"),
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
        self.setFixedSize(self.icon_size * 2 + 30, self.icon_size + 70)
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


class CategoryBoxWidget(CardWidget):
    """
    分類收納盒組件 (Category Box)
    具備毛玻璃卡片盒外觀、折疊/展開切換、計數徽章與卡片流式網格
    """
    toolLaunchRequested = Signal(dict)

    def __init__(self, category_name: str, tools: list, icon_size: int = 52, parent=None):
        super().__init__(parent)
        self.category_name = category_name
        self.tools = tools
        self.icon_size = icon_size
        self.is_collapsed = False
        self.card_widgets = []
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 12, 14, 14)
        self.main_layout.setSpacing(10)

        # 1. Box Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 0, 4, 0)

        self.title_label = StrongBodyLabel(f"📦 {self.category_name}", self)
        self.count_badge = CaptionLabel(f"({len(self.tools)} 個項目)", self)
        self.count_badge.setStyleSheet("color: #888888; font-weight: bold;")

        self.toggle_btn = TransparentToolButton(FluentIcon.CHEVRON_UP_MED, self)
        self.toggle_btn.setToolTip("折疊 / 展開收納盒")
        self.toggle_btn.clicked.connect(self.toggle_collapse)

        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.count_badge)
        header_layout.addStretch(1)
        header_layout.addWidget(self.toggle_btn)
        self.main_layout.addLayout(header_layout)

        # 2. Grid Container for tools
        self.grid_container = QWidget(self)
        self.grid_layout = QHBoxLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 4, 0, 0)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(Qt.AlignLeft)

        self.render_tool_cards()
        self.main_layout.addWidget(self.grid_container)

    def render_tool_cards(self):
        for c in self.card_widgets:
            c.deleteLater()
        self.card_widgets.clear()

        for t in self.tools:
            card = ToolCardWidget(t, icon_size=self.icon_size, parent=self.grid_container)
            card.toolClicked.connect(self.toolLaunchRequested.emit)
            self.grid_layout.addWidget(card)
            self.card_widgets.append(card)

        self.grid_layout.addStretch(1)

    def update_icon_size(self, size: int):
        self.icon_size = size
        for card in self.card_widgets:
            card.set_icon_size(size)

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        self.grid_container.setVisible(not self.is_collapsed)
        if self.is_collapsed:
            self.toggle_btn.setIcon(FluentIcon.CHEVRON_DOWN_MED)
        else:
            self.toggle_btn.setIcon(FluentIcon.CHEVRON_UP_MED)
