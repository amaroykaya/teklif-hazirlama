from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

from teklif_hazirlama import app_window_title
from teklif_hazirlama.ui.branding import app_icon, make_logo_label
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
        self.resize(440, self.sizeHint().height())

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(12)

        if self._on_back:
            btn_back = QPushButton("← Ana Menü")
            btn_back.clicked.connect(self._go_back)
            layout.addWidget(btn_back, alignment=Qt.AlignLeft)

        logo = make_logo_label(max_width=220)
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        title = QLabel("Teklif işlemeyi seçin")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        btn_istek = QPushButton("Teklif Kaydı")
        btn_istek.setMinimumHeight(40)
        btn_istek.clicked.connect(self._open_istek)
        layout.addWidget(btn_istek)

        btn_form = QPushButton("İlk Teklif Formu Hazırlama")
        btn_form.setMinimumHeight(40)
        btn_form.clicked.connect(self._open_form)
        layout.addWidget(btn_form)

        btn_revise = QPushButton("Revize Teklif Formu Hazırlama")
        btn_revise.setMinimumHeight(40)
        btn_revise.clicked.connect(self._open_revise)
        layout.addWidget(btn_revise)

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
