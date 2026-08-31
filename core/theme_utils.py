from qfluentwidgets import isDarkTheme

def get_theme_colors():
    if isDarkTheme():
        return {
            "success": "#6CCB5F",
            "error": "#FF99A4",
            "text": "#FFFFFF",
            "subtext": "#AAAAAA",
            "accent": "#9A70FF"
        }
    else:
        return {
            "success": "#107C41",
            "error": "#C42B1C",
            "text": "#000000",
            "subtext": "#666666",
            "accent": "#7A50DF"
        }
