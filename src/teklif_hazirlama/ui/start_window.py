from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from teklif_hazirlama import APP_NAME, __version__, app_window_title
from teklif_hazirlama.ui.branding import app_icon, make_logo_label
from teklif_hazirlama.ui.order_start_window import OrderStartWindow
from teklif_hazirlama.ui.quote_start_window import QuoteStartWindow


class StartWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(app_window_title())
        self.setWindowIcon(app_icon())
        self._child: QMainWindow | None = None
        self._build_ui()
        self.adjustSize()
        self.resize(420, self.sizeHint().height())

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(12)

        logo = make_logo_label(max_width=220)
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        brand = QLabel(APP_NAME)
        brand.setAlignment(Qt.AlignCenter)
        brand_font = brand.font()
        brand_font.setPointSize(max(11, brand_font.pointSize() + 1))
        brand_font.setBold(True)
        brand.setFont(brand_font)
        layout.addWidget(brand)

        version = QLabel(f"Sürüm {__version__}")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        title = QLabel("Ne yapmak istiyorsunuz?")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        btn_quote = QPushButton("Antsis Teklif Hazırlama")
        btn_quote.setMinimumHeight(40)
        btn_quote.clicked.connect(self._open_quote)
        layout.addWidget(btn_quote)

        btn_order = QPushButton("Antsis Sipariş İşleme")
        btn_order.setMinimumHeight(40)
        btn_order.clicked.connect(self._open_order)
        layout.addWidget(btn_order)

    def _open_quote(self) -> None:
        self._open_child(
            QuoteStartWindow(on_back=self._back_to_start), maximized=False
        )

    def _open_order(self) -> None:
        self._open_child(
            OrderStartWindow(on_back=self._back_to_start), maximized=False
        )

    def _open_child(self, window: QMainWindow, *, maximized: bool) -> None:
        if self._child is not None:
            self._child.close()
        self._child = window
        self.hide()
        if maximized:
            window.showMaximized()
        else:
            window.show()

    def _back_to_start(self) -> None:
        if self._child is not None:
            self._child.close()
            self._child = None
        self.show()


def run_app() -> None:
    from teklif_hazirlama.application.quote_workflow import cleanup_preview_files

    app = QApplication([])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setWindowIcon(app_icon())
    app.aboutToQuit.connect(cleanup_preview_files)
    window = StartWindow()
    window.show()
    app.exec()
