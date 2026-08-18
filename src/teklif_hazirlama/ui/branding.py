"""Uygulama markası: logo yolları ve UI yardımcıları."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton

from teklif_hazirlama import APP_NAME
from teklif_hazirlama.paths import ASSETS

BRANDING = ASSETS / "branding"
LOGO_PNG = BRANDING / "antsis_logo.png"
LOGO_HEADER_PNG = BRANDING / "antsis_logo_header.png"
LOGO_ICO = BRANDING / "antsis_logo.ico"


def app_icon() -> QIcon:
    if LOGO_ICO.exists():
        return QIcon(str(LOGO_ICO))
    if LOGO_PNG.exists():
        return QIcon(str(LOGO_PNG))
    return QIcon()


def logo_pixmap(*, header: bool = True) -> QPixmap:
    path = LOGO_HEADER_PNG if header and LOGO_HEADER_PNG.exists() else LOGO_PNG
    if not path.exists():
        return QPixmap()
    return QPixmap(str(path))


def make_logo_label(*, header: bool = True, max_width: int = 200) -> QLabel:
    """Üst bant için Antsis logo etiketi."""
    label = QLabel()
    pix = logo_pixmap(header=header)
    if not pix.isNull():
        if pix.width() > max_width:
            pix = pix.scaledToWidth(
                max_width, Qt.TransformationMode.SmoothTransformation
            )
        label.setPixmap(pix)
    else:
        label.setText(APP_NAME)
    label.setScaledContents(False)
    return label


def excel_file_icon(size: int = 22) -> QIcon:
    """Masaüstü Excel benzeri yeşil X ikonu."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#217346"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)
    painter.setPen(QColor("#ffffff"))
    font = QFont("Segoe UI", max(9, size // 2 - 1))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "X")
    painter.end()
    return QIcon(pm)


def pdf_file_icon(size: int = 22) -> QIcon:
    """Kırmızı PDF rozeti."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#dc2626"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)
    painter.setPen(QColor("#ffffff"))
    font = QFont("Segoe UI", max(9, size // 2 - 1))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "P")
    painter.end()
    return QIcon(pm)


def style_file_button(button: QPushButton) -> None:
    button.setMinimumHeight(34)
    button.setMinimumWidth(120)
    button.setStyleSheet(
        "QPushButton {"
        "  padding: 6px 12px;"
        "  font-weight: 600;"
        "  border: 1px solid #9ca3af;"
        "  border-radius: 6px;"
        "  background: #f3f4f6;"
        "}"
        "QPushButton:hover { background: #e5e7eb; }"
        "QPushButton:pressed { background: #d1d5db; }"
    )


def style_action_button(button: QPushButton, *, primary: bool = False) -> None:
    button.setMinimumHeight(40)
    if primary:
        button.setStyleSheet(
            "QPushButton {"
            "  padding: 8px 16px;"
            "  font-weight: 600;"
            "  border: 1px solid #1d4ed8;"
            "  border-radius: 6px;"
            "  background: #2563eb;"
            "  color: #ffffff;"
            "}"
            "QPushButton:hover { background: #1d4ed8; }"
            "QPushButton:pressed { background: #1e40af; }"
        )
        return
    button.setStyleSheet(
        "QPushButton {"
        "  padding: 8px 16px;"
        "  font-weight: 600;"
        "  border: 1px solid #6b7280;"
        "  border-radius: 6px;"
        "  background: #e5e7eb;"
        "}"
        "QPushButton:hover { background: #d1d5db; }"
        "QPushButton:pressed { background: #9ca3af; }"
    )


def make_choice_button(
    title: str,
    subtitle: str = "",
    *,
    primary: bool = False,
) -> QPushButton:
    """Ana menü / alt menü için iki satırlık seçim butonu."""
    text = f"{title}\n{subtitle}" if subtitle else title
    button = QPushButton(text)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setMinimumHeight(64 if subtitle else 48)
    if primary:
        button.setStyleSheet(
            "QPushButton {"
            "  padding: 12px 16px;"
            "  font-size: 13px;"
            "  font-weight: 600;"
            "  border: 1px solid #1d4ed8;"
            "  border-radius: 8px;"
            "  background: #2563eb;"
            "  color: #ffffff;"
            "  text-align: center;"
            "}"
            "QPushButton:hover { background: #1d4ed8; }"
            "QPushButton:pressed { background: #1e40af; }"
        )
    else:
        button.setStyleSheet(
            "QPushButton {"
            "  padding: 12px 16px;"
            "  font-size: 13px;"
            "  font-weight: 600;"
            "  border: 1px solid #cbd5e1;"
            "  border-radius: 8px;"
            "  background: #ffffff;"
            "  color: #0f172a;"
            "  text-align: center;"
            "}"
            "QPushButton:hover { background: #f1f5f9; border-color: #94a3b8; }"
            "QPushButton:pressed { background: #e2e8f0; }"
        )
    return button


def apply_menu_window_style(widget) -> None:
    widget.setStyleSheet(
        "QWidget#menuRoot { background: #f8fafc; }"
        "QLabel#menuHint { color: #64748b; font-size: 12px; }"
        "QLabel#menuTitle { color: #0f172a; font-size: 15px; font-weight: 600; }"
        "QLabel#menuVersion { color: #94a3b8; font-size: 11px; }"
    )
