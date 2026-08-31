import json, os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QButtonGroup
)
from qfluentwidgets import (
    SubtitleLabel, BodyLabel, CaptionLabel, StrongBodyLabel,
    Slider, SwitchButton, RadioButton, CheckBox, CardWidget,
    setTheme, Theme
)

class SettingsPanel(QWidget):
    settingsChanged = Signal(dict)

    def __init__(self, settings_file: str, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsInterface")
        self.settings_file = settings_file
        self.settings = self.load_settings()
        self.init_ui()

    def load_settings(self) -> dict:
        default_settings = {
            "window_opacity": 95,
            "acrylic_blur": True,
            "icon_size": 52,
            "theme_mode": "Auto",
            "always_on_top": False
        }
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_settings.update(data)
            except Exception:
                pass
        return default_settings

    def save_settings(self):
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Title
        title_box = QVBoxLayout()
        title = SubtitleLabel("🎨 視覺與個性化設置 (Personalization)", self)
        subtitle = CaptionLabel("即時自訂收納盒的壓克力磨砂質感、透明度、圖示大小與系統主題", self)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        main_layout.addLayout(title_box)

        # Scroll Area for settings cards
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        c_layout.setSpacing(16)

        # 1. 窗口透明度 Card
        self.opacity_card = self.create_slider_card(
            title="窗口透明度 (Window Opacity)",
            desc="調節整個收納盒大廳的視窗透明程度",
            min_val=30, max_val=100,
            cur_val=self.settings.get("window_opacity", 95),
            unit="%",
            on_change=self.on_opacity_changed
        )
        c_layout.addWidget(self.opacity_card)

        # 2. 圖標大小 Card
        self.icon_card = self.create_slider_card(
            title="圖標大小 (Icon Scale)",
            desc="動態縮放收納盒中所有工具卡片的圖示與磁貼尺寸",
            min_val=36, max_val=80,
            cur_val=self.settings.get("icon_size", 52),
            unit=" px",
            on_change=self.on_icon_size_changed
        )
        c_layout.addWidget(self.icon_card)

        # 3. 磨砂玻璃特效 Card
        self.acrylic_card = self.create_switch_card(
            title="磨砂玻璃效果 (Acrylic / Mica Blur)",
            desc="啟用 Windows 原生壓克力高質感毛玻璃背景襯底",
            checked=self.settings.get("acrylic_blur", True),
            on_change=self.on_acrylic_changed
        )
        c_layout.addWidget(self.acrylic_card)

        # 4. 外觀主題 Card (跟隨系統 / 淺色 / 深色)
        self.theme_card = self.create_theme_card()
        c_layout.addWidget(self.theme_card)

        # 5. 視窗行為 Card (置頂)
        self.behavior_card = self.create_behavior_card()
        c_layout.addWidget(self.behavior_card)

        c_layout.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def create_slider_card(self, title: str, desc: str, min_val: int, max_val: int, cur_val: int, unit: str, on_change):
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        t_label = StrongBodyLabel(title, card)
        v_label = BodyLabel(f"{cur_val}{unit}", card)
        v_label.setStyleSheet("color: #9A70FF; font-weight: bold;")
        top_row.addWidget(t_label)
        top_row.addStretch(1)
        top_row.addWidget(v_label)
        layout.addLayout(top_row)

        d_label = CaptionLabel(desc, card)
        layout.addWidget(d_label)

        slider = Slider(Qt.Horizontal, card)
        slider.setRange(min_val, max_val)
        slider.setValue(cur_val)
        slider.valueChanged.connect(lambda v: [v_label.setText(f"{v}{unit}"), on_change(v)])
        layout.addWidget(slider)

        return card

    def create_switch_card(self, title: str, desc: str, checked: bool, on_change):
        card = CardWidget(self)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)

        vbox = QVBoxLayout()
        t_label = StrongBodyLabel(title, card)
        d_label = CaptionLabel(desc, card)
        vbox.addWidget(t_label)
        vbox.addWidget(d_label)
        layout.addLayout(vbox)
        layout.addStretch(1)

        switch = SwitchButton(card)
        switch.setChecked(checked)
        switch.checkedChanged.connect(on_change)
        layout.addWidget(switch)

        return card

    def create_theme_card(self):
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        t_label = StrongBodyLabel("外觀主題 (Appearance Theme)", card)
        d_label = CaptionLabel("切換收納盒大廳的色彩模式（支援微軟 Fluent 深淺模式自動適配）", card)
        layout.addWidget(t_label)
        layout.addWidget(d_label)

        btn_group = QButtonGroup(self)
        row = QHBoxLayout()
        row.setSpacing(16)

        self.radio_auto = RadioButton("📱 跟隨系統 (Auto)", card)
        self.radio_light = RadioButton("☀️ 淺色 (Light)", card)
        self.radio_dark = RadioButton("🌙 深色 (Dark)", card)

        btn_group.addButton(self.radio_auto, 0)
        btn_group.addButton(self.radio_light, 1)
        btn_group.addButton(self.radio_dark, 2)

        cur_mode = self.settings.get("theme_mode", "Auto")
        if cur_mode == "Light":
            self.radio_light.setChecked(True)
        elif cur_mode == "Dark":
            self.radio_dark.setChecked(True)
        else:
            self.radio_auto.setChecked(True)

        self.radio_auto.toggled.connect(lambda c: self.on_theme_changed("Auto") if c else None)
        self.radio_light.toggled.connect(lambda c: self.on_theme_changed("Light") if c else None)
        self.radio_dark.toggled.connect(lambda c: self.on_theme_changed("Dark") if c else None)

        row.addWidget(self.radio_auto)
        row.addWidget(self.radio_light)
        row.addWidget(self.radio_dark)
        row.addStretch(1)
        layout.addLayout(row)

        return card

    def create_behavior_card(self):
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        t_label = StrongBodyLabel("視窗置頂與行為 (Window Behavior)", card)
        layout.addWidget(t_label)

        self.chk_top = CheckBox("📌 保持收納盒視窗最上層顯示 (Always on Top)", card)
        self.chk_top.setChecked(self.settings.get("always_on_top", False))
        self.chk_top.stateChanged.connect(self.on_top_changed)
        layout.addWidget(self.chk_top)

        return card

    def on_opacity_changed(self, val: int):
        self.settings["window_opacity"] = val
        self.save_settings()
        self.settingsChanged.emit(self.settings)

    def on_icon_size_changed(self, val: int):
        self.settings["icon_size"] = val
        self.save_settings()
        self.settingsChanged.emit(self.settings)

    def on_acrylic_changed(self, checked: bool):
        self.settings["acrylic_blur"] = checked
        self.save_settings()
        self.settingsChanged.emit(self.settings)

    def on_theme_changed(self, mode: str):
        self.settings["theme_mode"] = mode
        self.save_settings()
        if mode == "Light":
            setTheme(Theme.LIGHT)
        elif mode == "Dark":
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.AUTO)
        self.settingsChanged.emit(self.settings)

    def on_top_changed(self, state: int):
        self.settings["always_on_top"] = (state == Qt.Checked or state == 2)
        self.save_settings()
        self.settingsChanged.emit(self.settings)
