"""Uygulama markası: logo yolları ve UI yardımcıları."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel

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
