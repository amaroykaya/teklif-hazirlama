from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

from teklif_hazirlama import app_window_title
from teklif_hazirlama.ui.branding import (
    app_icon,
    apply_menu_window_style,
    make_choice_button,
    make_logo_label,
    style_file_button,
)
from teklif_hazirlama.ui.istek_window import IstekWindow
from teklif_hazirlama.ui.main_window import MainWindow


class QuoteStartWindow(QMainWindow):
    def __init__(self, on_back=None):
        super().__init__()
        self._on_back = on_back
        self._child: QMainWindow | None = None
        self.setWindowTitle(app_window_title("Antsis Teklif Hazırlama"))
        self.setWindowIcon(app_icon())
        self._build_ui()
        self.adjustSize()
        self.resize(480, max(440, self.sizeHint().height()))

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("menuRoot")
        apply_menu_window_style(central)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(36, 24, 36, 28)
        layout.setSpacing(10)

        if self._on_back:
            btn_back = QPushButton("← Ana Menü")
            style_file_button(btn_back)
            btn_back.setMinimumWidth(0)
            btn_back.clicked.connect(self._go_back)
            layout.addWidget(btn_back, alignment=Qt.AlignLeft)

        logo = make_logo_label(max_width=220)
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #e2e8f0;")
        layout.addWidget(line)

        title = QLabel("Teklif işlemeyi seçin")
        title.setObjectName("menuTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        hint = QLabel("Kayıt kopyalama veya form hazırlama")
        hint.setObjectName("menuHint")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        layout.addSpacing(6)

        btn_istek = make_choice_button(
            "Teklif Kaydı",
            "Google Sheets'e ilk teklif satırlarını kopyala",
        )
        btn_istek.clicked.connect(self._open_istek)
        layout.addWidget(btn_istek)

        btn_form = make_choice_button(
            "İlk Teklif Formu Hazırlama",
            "Excel ve PDF teklif belgesi oluştur",
            primary=True,
        )
        btn_form.clicked.connect(self._open_form)
        layout.addWidget(btn_form)

        btn_revise = make_choice_button(
            "Revize Teklif Formu Hazırlama",
            "Mevcut teklifi revizyonlu olarak güncelle",
        )
        btn_revise.clicked.connect(self._open_revise)
        layout.addWidget(btn_revise)

        layout.addStretch(1)

    def _open_istek(self) -> None:
        self._open_child(IstekWindow(on_back=self._back_to_menu), maximized=False)

    def _open_form(self) -> None:
        self._open_child(MainWindow(on_back=self._back_to_menu, mode="normal"), maximized=True)

    def _open_revise(self) -> None:
        self._open_child(MainWindow(on_back=self._back_to_menu, mode="revise"), maximized=True)

    def _open_child(self, window: QMainWindow, *, maximized: bool) -> None:
        if self._child is not None:
            self._child.close()
        self._child = window
        self.hide()
        if maximized:
            window.showMaximized()
        else:
            window.show()

    def _back_to_menu(self) -> None:
        if self._child is not None:
            self._child.close()
            self._child = None
        self.show()

    def _go_back(self) -> None:
        if self._on_back:
            self._on_back()
        else:
            self.close()
