import os, sys, subprocess, webbrowser
from PySide6.QtCore import (
    Qt, Signal, Property, QRectF, QPointF, QSize, QTimer,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QSequentialAnimationGroup
)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor, QFont, QPen, QLinearGradient
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy, QGraphicsOpacityEffect
)
from qfluentwidgets import (
    CardWidget, SimpleCardWidget, StrongBodyLabel, CaptionLabel,
    FluentIcon, RoundMenu, Action, ToolTipFilter, ToolTipPosition
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


def draw_liquid_fill_icon(src_pixmap: QPixmap, size: int, progress: int,
                          gold_sweep: float = 0.0, flash: float = 0.0,
                          checkmark_progress: float = 0.0) -> QPixmap:
    """
    繪製多重進度與慶祝特效之圖標：
    1. 填水灌滿 (Liquid Water Fill) 0~100%
    2. 金色光瀑自上而下鋪滿 (Gold Sweep)
    3. 金光閃爍 (Flash Effect)
    4. 綠色圓圈帶打勾動態繪製 (Animated Green Checkmark)
    """
    if src_pixmap.isNull():
        return src_pixmap

    full_colored = get_rounded_pixmap(src_pixmap, size)
    dest = QPixmap(size, size)
    dest.fill(Qt.transparent)

    painter = QPainter(dest)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    radius = max(6, int(size * 0.22))
    clip_path = QPainterPath()
    clip_path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)

    # 1. 底層：偏黑/暗化圖示 (未填水區域)
    painter.setOpacity(0.24)
    painter.drawPixmap(0, 0, full_colored)

    # 2. 頂層：依進度由底部向上填水 (Filled Liquid Layer)
    progress_ratio = max(0.0, min(1.0, progress / 100.0))
    if progress_ratio > 0:
        painter.setOpacity(1.0)
        painter.setClipPath(clip_path)

        fill_h = size * progress_ratio
        fill_y = size - fill_h

        painter.drawPixmap(
            QRectF(0, fill_y, size, fill_h),
            full_colored,
            QRectF(0, fill_y, size, fill_h)
        )

        # 水面波紋微光線 (Water Surface Glow)
        if progress_ratio < 1.0:
            painter.setPen(QColor(96, 205, 255, 230))
            painter.drawLine(0, int(fill_y), size, int(fill_y))

    # 3. 金色光瀑鋪滿效果 (Gold Sweep Effect 0.0 ~ 1.0)
    if gold_sweep > 0.0:
        painter.setOpacity(min(0.85, gold_sweep * 0.95))
        painter.setClipPath(clip_path)

        sweep_h = size * gold_sweep
        grad = QLinearGradient(0, 0, 0, sweep_h)
        grad.setColorAt(0.0, QColor(255, 215, 0, 240))      # Gold
        grad.setColorAt(0.7, QColor(255, 235, 120, 200))    # Light Gold
        grad.setColorAt(1.0, QColor(255, 255, 255, 220))    # Shimmer Edge

        painter.fillRect(QRectF(0, 0, size, sweep_h), grad)

    # 4. 金色閃光特效 (Flash Effect 0.0 ~ 1.0)
    if flash > 0.0:
        painter.setOpacity(flash * 0.75)
        painter.setClipPath(clip_path)
        painter.fillRect(QRectF(0, 0, size, size), QColor(255, 245, 180))

    painter.end()

    # 5. 綠色圓圈帶打勾動畫 (Animated Green Checkmark 0.0 ~ 1.0)
    if checkmark_progress > 0.0:
        painter = QPainter(dest)
        painter.setRenderHint(QPainter.Antialiasing, True)

        center_x = size / 2.0
        center_y = size / 2.0
        r = size * 0.32

        # 圓形背景半透明遮罩
        painter.setBrush(QColor(18, 18, 22, 190))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(center_x, center_y), r + 4, r + 4)

        # (A) 綠色外圓圈繪製 (0.0 ~ 0.5 進度)
        circle_ratio = min(1.0, checkmark_progress / 0.5)
        pen_circle = QPen(QColor("#10B981"), max(3, int(size * 0.06)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen_circle)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(
            QRectF(center_x - r, center_y - r, r * 2, r * 2),
            90 * 16,
            -int(360 * 16 * circle_ratio)
        )

        # (B) 綠色打勾打擊動畫 (0.5 ~ 1.0 進度)
        if checkmark_progress > 0.4:
            tick_ratio = min(1.0, (checkmark_progress - 0.4) / 0.6)
            pen_tick = QPen(QColor("#34D399"), max(3, int(size * 0.07)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen_tick)

            p1 = QPointF(center_x - r * 0.45, center_y)
            p2 = QPointF(center_x - r * 0.1, center_y + r * 0.38)
            p3 = QPointF(center_x + r * 0.5, center_y - r * 0.35)

            if tick_ratio <= 0.4:
                # 繪製前半段小勾
                sub = tick_ratio / 0.4
                curr = QPointF(p1.x() + (p2.x() - p1.x()) * sub, p1.y() + (p2.y() - p1.y()) * sub)
                painter.drawLine(p1, curr)
            else:
                # 繪製完整小勾 + 後半段長勾
                painter.drawLine(p1, p2)
                sub = (tick_ratio - 0.4) / 0.6
                curr = QPointF(p2.x() + (p3.x() - p2.x()) * sub, p2.y() + (p3.y() - p2.y()) * sub)
                painter.drawLine(p2, curr)

        painter.end()

    # 6. 下載進度文字 (僅在非打勾動畫時顯示)
    elif progress_ratio < 1.0 or (gold_sweep == 0.0 and flash == 0.0):
        if progress_ratio > 0.0:
            painter = QPainter(dest)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setPen(QColor(255, 255, 255, 245))
            font = painter.font()
            font.setBold(True)
            font.setPixelSize(max(11, int(size * 0.23)))
            painter.setFont(font)
            painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, f"{int(progress)}%")
            painter.end()

    return dest


class ToolCardWidget(CardWidget):
    """
    小工具磁貼卡片
    支援狀態與全套動畫：
    1. 未開啟 (IDLE)       - 預設精緻半透明磨砂卡片，圖標置中
    2. 已開啟 (RUNNING)    - 翡翠綠 (邊框與光暈)，再次點選直接呼叫軟體置頂
    3. 錯誤   (ERROR)      - 緋紅 (邊框與光暈)
    4. 安裝中 (INSTALLING) - 偏黑專案卡片，以該專案原生圖標進行 0~100% 填水灌滿特效
    5. 完成安裝慶祝動畫    - 金色光瀑鋪滿 ➔ 閃光 ➔ 綠色圓圈帶打勾動畫
    6. 新增/移除卡片動畫   - 彈出向外擴展 (Pop Out) 與 內縮消失 (Pop In)
    """
    toolClicked = Signal(dict, bool)         # (tool_data, is_installed)
    installRequested = Signal(dict)          # (repo_data)
    reinstallRequested = Signal(dict)        # (tool_data)
    uninstallRequested = Signal(dict)        # (tool_data)
    cloudIconLoaded = Signal(str)            # (cached_icon_path)

    STATE_IDLE = "idle"
    STATE_RUNNING = "running"
    STATE_ERROR = "error"
    STATE_INSTALLING = "installing"

    def __init__(self, data: dict, is_installed: bool = True, icon_size: int = 56, parent=None):
        super().__init__(parent)
        self.data = data
        self.is_installed = is_installed
        self.icon_size = icon_size
        self.current_state = self.STATE_IDLE
        self.install_progress = 0

        # 動畫屬性
        self._scale_factor = 1.0
        self._card_opacity = 1.0
        self._gold_sweep = 0.0
        self._flash_intensity = 0.0
        self._checkmark_progress = 0.0

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

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
        if self.is_installed:
            exe_path = self.data.get("executable", "")
            self.setToolTip(f"【{name}】 (已安裝)\n{desc}\n路徑: {exe_path}")
        else:
            url = self.data.get("html_url") or self.data.get("clone_url", "")
            self.setToolTip(f"【{name}】 (未安裝 - 雲端專案)\n{desc}\n倉庫: {url}")

        self.installEventFilter(ToolTipFilter(self, showDelay=250, position=ToolTipPosition.BOTTOM))

    # === 動畫屬性 Properties ===
    def get_scale_factor(self) -> float:
        return self._scale_factor

    def set_scale_factor(self, val: float):
        self._scale_factor = val
        self.update()

    scaleFactor = Property(float, get_scale_factor, set_scale_factor)

    def get_card_opacity(self) -> float:
        return self._card_opacity

    def set_card_opacity(self, val: float):
        self._card_opacity = val
        if self.opacity_effect:
            self.opacity_effect.setOpacity(val)

    cardOpacity = Property(float, get_card_opacity, set_card_opacity)

    def get_gold_sweep(self) -> float:
        return self._gold_sweep

    def set_gold_sweep(self, val: float):
        self._gold_sweep = val
        self.update_icon()

    goldSweep = Property(float, get_gold_sweep, set_gold_sweep)

    def get_flash_intensity(self) -> float:
        return self._flash_intensity

    def set_flash_intensity(self, val: float):
        self._flash_intensity = val
        self.update_icon()

    flashIntensity = Property(float, get_flash_intensity, set_flash_intensity)

    def get_checkmark_progress(self) -> float:
        return self._checkmark_progress

    def set_checkmark_progress(self, val: float):
        self._checkmark_progress = val
        self.update_icon()

    checkmarkProgress = Property(float, get_checkmark_progress, set_checkmark_progress)

    def paintEvent(self, event):
        """
        支援以中心為錨點進行平滑縮放動畫
        """
        if self._scale_factor != 1.0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            cx = self.width() / 2.0
            cy = self.height() / 2.0
            painter.translate(cx, cy)
            painter.scale(self._scale_factor, self._scale_factor)
            painter.translate(-cx, -cy)
            super().paintEvent(event)
            painter.end()
        else:
            super().paintEvent(event)

    # === 動畫流程 Animation Helpers ===
    def popup_expand_animation(self, on_finished=None):
        """
        從中向外擴展彈出效果 (Pop Out Animation)
        """
        try:
            self.anim_group = QParallelAnimationGroup(self)

            anim_scale = QPropertyAnimation(self, b"scaleFactor")
            anim_scale.setDuration(320)
            anim_scale.setStartValue(0.0)
            anim_scale.setKeyValueAt(0.7, 1.08)
            anim_scale.setEndValue(1.0)
            anim_scale.setEasingCurve(QEasingCurve.OutBack)

            anim_opac = QPropertyAnimation(self, b"cardOpacity")
            anim_opac.setDuration(240)
            anim_opac.setStartValue(0.0)
            anim_opac.setEndValue(1.0)

            self.anim_group.addAnimation(anim_scale)
            self.anim_group.addAnimation(anim_opac)
            if on_finished:
                self.anim_group.finished.connect(on_finished)
            self.anim_group.start()
        except Exception:
            if on_finished:
                on_finished()

    def shrink_collapse_animation(self, on_finished=None):
        """
        向內收縮並啵一聲消失效果 (Pop In / Shrink Animation)
        """
        try:
            self.anim_shrink_group = QParallelAnimationGroup(self)

            anim_scale = QPropertyAnimation(self, b"scaleFactor")
            anim_scale.setDuration(280)
            anim_scale.setStartValue(1.0)
            anim_scale.setKeyValueAt(0.3, 1.08)
            anim_scale.setEndValue(0.0)
            anim_scale.setEasingCurve(QEasingCurve.InBack)

            anim_opac = QPropertyAnimation(self, b"cardOpacity")
            anim_opac.setDuration(220)
            anim_opac.setStartValue(1.0)
            anim_opac.setEndValue(0.0)

            self.anim_shrink_group.addAnimation(anim_scale)
            self.anim_shrink_group.addAnimation(anim_opac)
            if on_finished:
                self.anim_shrink_group.finished.connect(on_finished)
            self.anim_shrink_group.start()
        except Exception:
            if on_finished:
                on_finished()

    def play_install_success_celebration(self, on_finished=None):
        """
        完成安裝慶祝動畫：
        1. 金色由上至下鋪滿 (Gold Sweep)
        2. 金色閃光 (Flash)
        3. 綠色圓圈帶打勾動態繪製 (Animated Green Checkmark)
        4. 復原為正式已安裝卡片
        """
        try:
            self.celeb_group = QSequentialAnimationGroup(self)

            # 1. 金色鋪滿動畫 (350ms)
            anim_sweep = QPropertyAnimation(self, b"goldSweep")
            anim_sweep.setDuration(350)
            anim_sweep.setStartValue(0.0)
            anim_sweep.setEndValue(1.0)
            anim_sweep.setEasingCurve(QEasingCurve.OutQuad)

            # 2. 閃光動畫 (180ms)
            anim_flash = QPropertyAnimation(self, b"flashIntensity")
            anim_flash.setDuration(180)
            anim_flash.setStartValue(1.0)
            anim_flash.setEndValue(0.0)

            # 3. 綠色圓圈帶打勾繪製動畫 (450ms)
            anim_check = QPropertyAnimation(self, b"checkmarkProgress")
            anim_check.setDuration(450)
            anim_check.setStartValue(0.0)
            anim_check.setEndValue(1.0)
            anim_check.setEasingCurve(QEasingCurve.OutCubic)

            self.celeb_group.addAnimation(anim_sweep)
            self.celeb_group.addAnimation(anim_flash)
            self.celeb_group.addAnimation(anim_check)

            def _after_celeb():
                def _restore():
                    try:
                        self.set_gold_sweep(0.0)
                        self.set_flash_intensity(0.0)
                        self.set_checkmark_progress(0.0)
                        self.apply_state(self.STATE_IDLE)
                    except Exception:
                        pass
                    if on_finished:
                        try:
                            on_finished()
                        except Exception:
                            pass
                QTimer.singleShot(500, _restore)

            self.celeb_group.finished.connect(_after_celeb)
            self.celeb_group.start()
        except Exception:
            if on_finished:
                on_finished()

    def apply_state(self, state: str):
        """
        切換並套用卡片外觀
        """
        self.current_state = state

        if state == self.STATE_INSTALLING:
            # 📥 安裝中 (偏黑專案卡片 + 0~100% 填水灌滿圖標)
            self.setStyleSheet("""
                ToolCardWidget {
                    background-color: rgba(18, 18, 20, 0.75);
                    border: 1.5px dashed rgba(96, 205, 255, 0.6);
                    border-radius: 8px;
                }
            """)
            self.badge_label.setText(f"📥 下載中 {self.install_progress}%")
            self.badge_label.setStyleSheet("color: #60CDFF; font-size: 10px; font-weight: bold;")
            self.badge_label.show()
            self.update_icon()

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
            self.update_icon()

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
            self.update_icon()

        else:
            # ⚪ 未開啟 (預設半透明壓克力卡片，圖標置中)
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
            self.update_icon()

    def set_install_progress(self, progress: int, status_text: str = ""):
        """
        更新填水灌滿圖標之進度 (0~100%)
        """
        self.install_progress = max(0, min(100, progress))
        if self.current_state != self.STATE_INSTALLING:
            self.current_state = self.STATE_INSTALLING
            self.apply_state(self.STATE_INSTALLING)

        text = status_text or f"📥 下載中 {self.install_progress}%"
        self.badge_label.setText(text)
        self.update_icon()

    def on_cloud_icon_ready(self, icon_path: str):
        if os.path.exists(icon_path):
            self.update_icon()

    def update_icon(self):
        raw_pixmap = self.get_tool_raw_pixmap()
        if self.current_state == self.STATE_INSTALLING or self._gold_sweep > 0.0 or self._checkmark_progress > 0.0:
            # 呈現 填水 / 金色光瀑 / 閃光 / 綠色打勾 特效圖標
            water_pixmap = draw_liquid_fill_icon(
                raw_pixmap, self.icon_size, self.install_progress,
                gold_sweep=self._gold_sweep,
                flash=self._flash_intensity,
                checkmark_progress=self._checkmark_progress
            )
            self.icon_label.setPixmap(water_pixmap)
        else:
            rounded_pixmap = get_rounded_pixmap(raw_pixmap, self.icon_size)
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
