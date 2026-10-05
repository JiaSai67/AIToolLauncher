import json, os, shutil, sys, platform, subprocess
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QEasingCurve
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QButtonGroup, QFileDialog, QApplication
)
from qfluentwidgets import (
    SubtitleLabel, BodyLabel, CaptionLabel, StrongBodyLabel,
    Slider, RadioButton, CardWidget, PushButton, TransparentToolButton,
    FluentIcon, setTheme, Theme, SmoothScrollArea, InfoBar, InfoBarPosition
)


class SettingsPanel(QWidget):
    settingsChanged = Signal(dict)
    checkUpdateRequested = Signal()

    def __init__(self, settings_file: str, version: str = "2.0.25", parent=None):
        super().__init__(parent)
        self.setObjectName("settingsInterface")
        self.version = version
        self.settings_file = settings_file
        self.settings = self.load_settings()
        self.init_ui()

    def load_settings(self) -> dict:
        default_settings = {
            "window_width": 960,
            "window_height": 680,
            "window_is_maximized": False,
            "window_opacity": 95,
            "background_image_path": "",
            "background_opacity": 80,
            "background_blur": 15,
            "icon_size": 56,
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
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        # Title
        title_box = QVBoxLayout()
        title = SubtitleLabel("🎨 個性化設置 (Settings)", self)
        subtitle = CaptionLabel("比照 desk_tidy 自訂背景桌布/動態 GIF、高斯磨砂模糊、顯色濃度與深淺主題模式", self)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        main_layout.addLayout(title_box)

        # Scroll Area for settings cards
        scroll = SmoothScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.enableTransparentBackground()
        scroll.setScrollAnimation(Qt.Vertical, 120, QEasingCurve.OutQuad)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        c_layout.setSpacing(16)

        # 1. 🖼️ 自訂背景圖片 Card
        self.bg_image_card = self.create_background_image_card()
        c_layout.addWidget(self.bg_image_card)

        # 2. 🌫️ 背景磨砂模糊度 Card (0 ~ 40 px)
        self.bg_blur_card = self.create_slider_card(
            title="🌫️ 背景磨砂模糊度 (Frosted Blur Radius)",
            desc="調節背景桌布的真實毛玻璃模糊程度（0 為清晰原圖，10~25 為頂級柔和磨砂質感）",
            min_val=0, max_val=40,
            cur_val=self.settings.get("background_blur", 15),
            unit=" px",
            on_change=self.on_bg_blur_changed
        )
        c_layout.addWidget(self.bg_blur_card)

        # 3. ✨ 背景圖片顯色濃度 Card (10% ~ 100%)
        self.bg_opacity_card = self.create_slider_card(
            title="✨ 背景圖片顯色濃度 (Background Opacity)",
            desc="調節自訂桌布的顯色濃度與底層磨砂透光度（即時生效）",
            min_val=10, max_val=100,
            cur_val=self.settings.get("background_opacity", 80),
            unit="%",
            on_change=self.on_bg_opacity_changed
        )
        c_layout.addWidget(self.bg_opacity_card)

        # 4. 🪟 視窗整體透明度 Card
        self.opacity_card = self.create_slider_card(
            title="🪟 視窗半透明度 (Window Opacity)",
            desc="調節整個收納盒大廳視窗邊框與材質的整體透光率",
            min_val=30, max_val=100,
            cur_val=self.settings.get("window_opacity", 95),
            unit="%",
            on_change=self.on_opacity_changed
        )
        c_layout.addWidget(self.opacity_card)

        # 5. 🔲 圖標大小 Card
        self.icon_card = self.create_slider_card(
            title="🔲 圖標縮放比例 (Icon Scale)",
            desc="動態縮放收納盒中所有圓角卡片與圖示的尺寸",
            min_val=36, max_val=80,
            cur_val=self.settings.get("icon_size", 56),
            unit=" px",
            on_change=self.on_icon_size_changed
        )
        c_layout.addWidget(self.icon_card)

        # 6. 🌙 外觀主題 Card (跟隨系統 / 淺色 / 深色)
        self.theme_card = self.create_theme_card()
        c_layout.addWidget(self.theme_card)

        # 7. 🚀 關於與版本更新 Card
        self.update_card = self.create_update_card()
        c_layout.addWidget(self.update_card)

        # 8. 📋 系統診斷與運行日誌 Card
        self.diagnostics_card = self.create_diagnostics_card()
        c_layout.addWidget(self.diagnostics_card)

        c_layout.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def create_update_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        t_label = StrongBodyLabel("🚀 軟體版本與更新 (AIToolLauncher 2.0)", card)
        d_label = CaptionLabel(f"目前版本：v{self.version} | 點擊右側按鈕可即時檢查 GitHub 主倉庫最新版本", card)
        info_layout.addWidget(t_label)
        info_layout.addWidget(d_label)

        layout.addLayout(info_layout)
        layout.addStretch(1)

        self.btn_check_update = PushButton("檢查更新", card)
        self.btn_check_update.setIcon(FluentIcon.SYNC)
        self.btn_check_update.setFixedWidth(120)
        self.btn_check_update.clicked.connect(self.checkUpdateRequested.emit)
        layout.addWidget(self.btn_check_update)

        return card

    def create_diagnostics_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        t_label = StrongBodyLabel("📋 系統診斷與運行日誌 (Diagnostics & Logs)", card)
        d_label = CaptionLabel("遇到異常、小工具啟動失敗或需回報運行狀況時，可直接查看日誌或一鍵複製環境資訊回報給開發者", card)
        layout.addWidget(t_label)
        layout.addWidget(d_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_view_log = PushButton("查看運行日誌", card)
        self.btn_view_log.setIcon(FluentIcon.DOCUMENT)
        self.btn_view_log.setCursor(Qt.PointingHandCursor)
        self.btn_view_log.clicked.connect(self.on_view_runtime_log)

        self.btn_open_log_dir = PushButton("開啟日誌目錄", card)
        self.btn_open_log_dir.setIcon(FluentIcon.FOLDER)
        self.btn_open_log_dir.setCursor(Qt.PointingHandCursor)
        self.btn_open_log_dir.clicked.connect(self.on_open_log_directory)

        self.btn_copy_diag = PushButton("一鍵複製診斷資訊", card)
        self.btn_copy_diag.setIcon(FluentIcon.COPY)
        self.btn_copy_diag.setCursor(Qt.PointingHandCursor)
        self.btn_copy_diag.clicked.connect(self.on_copy_diagnostic_info)

        btn_row.addWidget(self.btn_view_log)
        btn_row.addWidget(self.btn_open_log_dir)
        btn_row.addWidget(self.btn_copy_diag)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        return card

    def on_view_runtime_log(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_candidates = [
            os.path.join(root_dir, "launcher_error.log"),
            os.path.join(root_dir, "resources", "logs", "launcher_runtime.log"),
            os.path.join(root_dir, "launcher_runtime.log")
        ]
        target_log = None
        for p in log_candidates:
            if os.path.exists(p) and os.path.getsize(p) > 0:
                target_log = p
                break

        if not target_log:
            # 建立一份包含基礎環境與運行的即時診斷報告
            target_log = os.path.join(root_dir, "launcher_runtime.log")
            diag_text = self._build_diagnostic_text()
            try:
                with open(target_log, "w", encoding="utf-8") as f:
                    f.write(f"=== AI Tool Launcher 即時運行診斷報告 ===\n產生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{diag_text}\n\n[狀態說明]: 目前系統無重大攔截崩潰日誌，主程式運作良好。\n")
            except Exception:
                pass

        try:
            if sys.platform == "win32":
                os.startfile(target_log)
            else:
                subprocess.Popen(["xdg-open", target_log])
        except Exception as e:
            InfoBar.warning("開啟失敗", f"無法開啟日誌檔案: {e}", parent=self)

    def on_open_log_directory(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            if sys.platform == "win32":
                os.startfile(root_dir)
            else:
                subprocess.Popen(["xdg-open", root_dir])
        except Exception as e:
            InfoBar.warning("開啟目錄失敗", str(e), parent=self)

    def _build_diagnostic_text(self) -> str:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        lines = [
            f"• Launcher 版本: v{self.version}",
            f"• Python 核心: {platform.python_version()} ({sys.executable})",
            f"• 作業系統: {platform.system()} {platform.release()} ({platform.architecture()[0]})",
            f"• 工作目錄: {root_dir}",
            f"• 螢幕時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        # 附加 Git 狀態
        try:
            git_ver = subprocess.check_output(["git", "--version"], stderr=subprocess.STDOUT, timeout=3).decode("utf-8", "ignore").strip()
            lines.append(f"• Git 版本: {git_ver}")
        except Exception:
            lines.append("• Git 版本: 未檢測到或執行超時")

        return "\n".join(lines)

    def on_copy_diagnostic_info(self):
        diag_text = self._build_diagnostic_text()
        try:
            QApplication.clipboard().setText(diag_text)
            InfoBar.success(
                title="複製成功",
                content="系統診斷資訊已複製至剪貼簿！可直接貼給開發者以供排查。",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3500,
                parent=self
            )
        except Exception as e:
            InfoBar.warning("複製失敗", str(e), parent=self)

    def create_background_image_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        t_label = StrongBodyLabel("🖼️ 自訂背景桌布 (Background Image / GIF)", card)
        top_row.addWidget(t_label)
        top_row.addStretch(1)

        # 選擇按鈕
        self.btn_pick_bg = PushButton(FluentIcon.PHOTO, "選擇圖片 / GIF", card)
        self.btn_pick_bg.setCursor(Qt.PointingHandCursor)
        self.btn_pick_bg.clicked.connect(self.on_pick_background)
        top_row.addWidget(self.btn_pick_bg)

        # 清除按鈕
        self.btn_clear_bg = TransparentToolButton(FluentIcon.DELETE, card)
        self.btn_clear_bg.setToolTip("清除背景圖片 (還原純淨磨砂質感)")
        self.btn_clear_bg.clicked.connect(self.on_clear_background)
        top_row.addWidget(self.btn_clear_bg)

        layout.addLayout(top_row)

        d_label = CaptionLabel("支援 GIF 動畫循環播放、PNG、JPG、WEBP、BMP 等所有格式，選取後自動備份快取", card)
        layout.addWidget(d_label)

        # 顯示目前設定之路徑
        self.bg_path_label = CaptionLabel("", card)
        self.bg_path_label.setStyleSheet("color: #9A70FF; font-weight: 500;")
        self.update_bg_path_label()
        layout.addWidget(self.bg_path_label)

        return card

    def update_bg_path_label(self):
        bg_path = self.settings.get("background_image_path", "")
        if bg_path and os.path.exists(bg_path):
            filename = os.path.basename(bg_path)
            self.bg_path_label.setText(f"目前背景：{filename}（路徑: {bg_path}）")
        else:
            self.bg_path_label.setText("目前背景：預設純淨磨砂質感（未設定自訂桌布）")

    def on_pick_background(self):
        filters = "圖片與動畫檔案 (*.gif *.png *.jpg *.jpeg *.jfif *.webp *.bmp *.svg *.tif *.tiff);;GIF 動畫 (*.gif);;所有檔案 (*.*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "選擇背景圖片或動態 GIF", "", filters)
        if file_path and os.path.exists(file_path):
            # 自動備份快取至 resources/config/ 避免使用者移動原檔後遺失
            config_dir = os.path.dirname(self.settings_file)
            ext = os.path.splitext(file_path)[1].lower()
            cached_bg = os.path.join(config_dir, f"background{ext}")
            try:
                shutil.copy2(file_path, cached_bg)
                saved_path = cached_bg
            except Exception:
                saved_path = file_path

            self.settings["background_image_path"] = saved_path
            self.save_settings()
            self.update_bg_path_label()
            self.settingsChanged.emit(self.settings)

    def on_clear_background(self):
        self.settings["background_image_path"] = ""
        self.save_settings()
        self.update_bg_path_label()
        self.settingsChanged.emit(self.settings)

    def on_bg_blur_changed(self, val: int):
        self.settings["background_blur"] = val
        self.save_settings()
        self.settingsChanged.emit(self.settings)

    def on_bg_opacity_changed(self, val: int):
        self.settings["background_opacity"] = val
        self.save_settings()
        self.settingsChanged.emit(self.settings)

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

    def create_theme_card(self):
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        t_label = StrongBodyLabel("外觀主題 (Appearance Theme)", card)
        d_label = CaptionLabel("切換收納盒大廳的色彩風格（支援 Fluent 深淺模式自動適配）", card)
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

    def on_opacity_changed(self, val: int):
        self.settings["window_opacity"] = val
        self.save_settings()
        self.settingsChanged.emit(self.settings)

    def on_icon_size_changed(self, val: int):
        self.settings["icon_size"] = val
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
