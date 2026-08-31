import winreg

class ThemeColors:
    def __init__(self, is_dark):
        self.is_dark = is_dark
        if is_dark:
            self.bg_root = "#202020"
            self.bg_card = "#2D2D2D"
            self.text_title = "#E3E3E3"
            self.text_main = "#CCCCCC"
            self.text_dim = "#999999"
            self.success = "#529E48"
            self.error = "#D85E6D"
            self.select_bg = "#4527A0"
            self.border = "#3D3D3D"
            self.link = "#5C9DFF"
        else:
            self.bg_root = "#f4f5f7"
            self.bg_card = "#FFFFFF"
            self.text_title = "#1A1A1A"
            self.text_main = "#2c3e50"
            self.text_dim = "#7f8c8d"
            self.success = "#27ae60"
            self.error = "#e74c3c"
            self.select_bg = "#3498db"
            self.border = "#bdc3c7"
            self.link = "#2980b9"

def is_dark_theme():
    try:
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        return False

def get_theme_colors():
    return ThemeColors(is_dark_theme())
