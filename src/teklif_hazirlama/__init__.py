"""Antsis Teklif & Sipariş uygulaması."""

__version__ = "0.3.1"

APP_NAME = "Antsis Teklif & Sipariş"


def app_window_title(page: str = "") -> str:
    """Pencere başlığı: sayfa + uygulama adı + sürüm."""
    base = f"{APP_NAME} v{__version__}"
    if page:
        return f"{page} — {base}"
    return base
