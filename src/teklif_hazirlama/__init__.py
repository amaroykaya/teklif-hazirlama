"""Teklif Hazırlama uygulaması."""

__version__ = "0.2.0"

APP_NAME = "Antsis Teklif Hazırlama"


def app_window_title(page: str = "") -> str:
    """Pencere başlığı: sayfa + uygulama adı + sürüm."""
    base = f"{APP_NAME} v{__version__}"
    if page:
        return f"{page} — {base}"
    return base
