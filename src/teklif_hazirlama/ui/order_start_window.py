from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget

from teklif_hazirlama import app_window_title
from teklif_hazirlama.ui.branding import app_icon, make_logo_label
from teklif_hazirlama.ui.order_main_window import OrderMainWindow


class OrderStartWindow(QMainWindow):
    def __init__(self, on_back=None):
        super().__init__()
        self._on_back = on_back
        self._child: QMainWindow | None = None
        self.setWindowTitle(app_window_title("Antsis Sipariş İşleme"))
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

        title = QLabel("Sipariş işlemeyi seçin")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        btn_main = QPushButton("Ana Sipariş İşleme")
        btn_main.setMinimumHeight(40)
        btn_main.clicked.connect(self._open_main_order)
        layout.addWidget(btn_main)

        btn_anten = QPushButton("Anten Sipariş İşleme")
        btn_anten.setMinimumHeight(40)
        btn_anten.clicked.connect(self._show_not_ready)
        layout.addWidget(btn_anten)

        btn_elektronik = QPushButton("Elektronik Sipariş İşleme")
        btn_elektronik.setMinimumHeight(40)
        btn_elektronik.clicked.connect(self._show_not_ready)
        layout.addWidget(btn_elektronik)

    def _open_main_order(self) -> None:
        self._open_child(OrderMainWindow(on_back=self._back_to_menu))

    def _show_not_ready(self) -> None:
        QMessageBox.information(
            self,
            "Bilgi",
            "Bu alt akış sonraki fazda eklenecek. Şimdilik Ana Sipariş İşleme aktif.",
        )

    def _open_child(self, window: QMainWindow) -> None:
        if self._child is not None:
            self._child.close()
        self._child = window
        self.hide()
        window.showMaximized()

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
