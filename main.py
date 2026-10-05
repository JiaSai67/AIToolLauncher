# -*- coding: utf-8 -*-
"""
AI Tool Launcher 2.0 - 核心主程式入口
預設啟動原版 PySide6 Fluent 介面，具備「拖曳移動時瞬間休眠 GIF 動畫、滑鼠放開時無縫恢復播放」的 144Hz+ 極速流暢位移架構。
"""

import os
import sys
from pathlib import Path

# 將根目錄與 core 置於 sys.path 首位
_root_dir = Path(__file__).resolve().parent
_core_dir = _root_dir / "core"
for p in [str(_root_dir), str(_core_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# 註冊專屬 Windows AppUserModelID
if sys.platform == "win32":
    try:
        import ctypes
        myappid = "jiasai.aitoollauncher.v2.desktop"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass


# 0 毫秒優先載入全域異常攔截器 (純標準庫，零第三方依賴)
try:
    from core.identity_manager import install_global_exception_hook, send_identity_webhook
    install_global_exception_hook()
except Exception:
    pass


def launch_classic_gui():
    """啟動原版經典 PySide6 Fluent 壓克力收納盒大廳 (最快最穩定)"""
    from core import launcher_v2
    launcher_v2.main()


def launch_modern_gui():
    """啟動現代化 Chromium (WebView2) 介面 (備用)"""
    import webview
    from core.web_api import WebApi

    api = WebApi()
    html_path = _root_dir / "gui" / "index.html"
    if not html_path.exists():
        raise FileNotFoundError(f"找不到前端頁面：{html_path}")

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    MIN_WIDTH = 800
    MIN_HEIGHT = 560
    cfg = api.get_settings()
    width = max(int(cfg.get("window_width", 1180)), MIN_WIDTH)
    height = max(int(cfg.get("window_height", 760)), MIN_HEIGHT)

    webview.settings['DRAG_REGION_SELECTOR'] = '.pywebview-drag-region, .titlebar'

    window = webview.create_window(
        title="AI Tool Launcher 2.1 [收納盒模式]",
        html=html_content,
        js_api=api,
        width=width,
        height=height,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        resizable=True,
        frameless=True,
        easy_drag=True,
        background_color="#121216"
    )

    api.set_window(window)
    webview.start(debug=False)


def main():
    try:
        # 若有 --modern 或 --chromium 參數則啟動 webview，預設直接啟動原版 PySide6
        if "--modern" in sys.argv or "--chromium" in sys.argv:
            try:
                launch_modern_gui()
                return
            except Exception as e:
                print(f"[Launcher] 現代化 Webview 啟動異常: {e}，自動切換至經典 Fluent 介面...")

        launch_classic_gui()
    except Exception as e:
        import traceback, time
        err_msg = traceback.format_exc()

        # 1. 寫入本地 launcher_error.log
        try:
            log_p = _root_dir / "launcher_error.log"
            with open(log_p, "w", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 啟動期致命異常 (套件缺失/環境錯誤):\n{err_msg}\n")
        except Exception:
            pass

        # 2. 透過加密 Webhook 發送錯誤推播 (紅色)
        try:
            from core.identity_manager import send_identity_webhook
            send_identity_webhook("💥 AI Tool Launcher 2.0 啟動失敗 (套件缺失/環境異常)", err_msg, color=0xFF0033)
            # 等待 1 秒確保 Webhook 執行緒發送完畢
            time.sleep(1.0)
        except Exception:
            pass

        # 3. 彈出 Windows 原生對話框提示 (避免靜默閃退迷茫)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"AI Tool Launcher 2.0 啟動失敗！\n\n錯誤原因: {e}\n\n詳細錯誤已記錄至 launcher_error.log 並已自動回報至 Discord。\n請執行 AIToolLauncher_Setup.exe 自動修復環境依賴。",
                "啟動異常 - AI Tool Launcher 2.0",
                0x10 | 0x10000
            )
        except Exception:
            pass


if __name__ == "__main__":
    main()
