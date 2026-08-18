from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from teklif_hazirlama import APP_NAME, __version__, app_window_title
from teklif_hazirlama.ui.branding import (
    app_icon,
    apply_menu_window_style,
    make_choice_button,
    make_logo_label,
)
from teklif_hazirlama.ui.order_main_window import OrderMainWindow
from teklif_hazirlama.ui.quote_start_window import QuoteStartWindow


class StartWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(app_window_title())
        self.setWindowIcon(app_icon())
        self._child: QMainWindow | None = None
        self._build_ui()
        self.adjustSize()
        self.resize(480, max(420, self.sizeHint().height()))

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("menuRoot")
        apply_menu_window_style(central)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(36, 32, 36, 28)
        layout.setSpacing(10)

        logo = make_logo_label(max_width=240)
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        version = QLabel(f"Sürüm {__version__}")
        version.setObjectName("menuVersion")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #e2e8f0;")
        layout.addWidget(line)

        title = QLabel("Ne yapmak istiyorsunuz?")
        title.setObjectName("menuTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        hint = QLabel("Çalışmak istediğiniz modülü seçin")
        hint.setObjectName("menuHint")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        layout.addSpacing(8)

        btn_quote = make_choice_button(
            "Antsis Teklif Hazırlama",
            "Teklif kaydı, ilk form ve revize",
            primary=True,
        )
        btn_quote.clicked.connect(self._open_quote)
        layout.addWidget(btn_quote)

        btn_order = make_choice_button(
            "Antsis Sipariş İşleme",
            "PDF ve Excel'den sipariş satırları",
        )
        btn_order.clicked.connect(self._open_order)
        layout.addWidget(btn_order)

        layout.addStretch(1)

    def _open_quote(self) -> None:
        self._open_child(
            QuoteStartWindow(on_back=self._back_to_start), maximized=False
        )

    def _open_order(self) -> None:
        self._open_child(
            OrderMainWindow(on_back=self._back_to_start), maximized=True
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
