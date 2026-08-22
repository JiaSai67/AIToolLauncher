import winreg

class ThemeColors:
    def __init__(self, is_dark):
        self.is_dark = is_dark
        if is_dark:
            self.bg_root = "#222222"
            self.bg_card = "#2B2B2B"
            self.text_main = "#FFFFFF"
            self.text_dim = "#AAAAAA"
            self.success = "#6CCB5F"
            self.error = "#FF99A4"
            self.select_bg = "#5E35B1"
            self.border = "#444444"
            self.link = "#64B5F6"
        else:
            self.bg_root = "#f4f5f7"
            self.bg_card = "#FFFFFF"
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
