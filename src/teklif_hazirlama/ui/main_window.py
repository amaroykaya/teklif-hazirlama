from __future__ import annotations

from pathlib import Path

from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QSize, QUrl, Qt
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from teklif_hazirlama import app_window_title
from teklif_hazirlama.application.quote_workflow import QuoteRequest, QuoteWorkflow
from teklif_hazirlama.core.models import HitapKisi, QuoteLine, SheetsRow
from teklif_hazirlama.core.sheets_clipboard import generate_teklif_no
from teklif_hazirlama.core.template_filler import load_default_sartlar
from teklif_hazirlama.ui.branding import app_icon, make_logo_label
from teklif_hazirlama.ui.dialogs import CustomerDialog, HitapKisiDialog, ListItemDialog
from teklif_hazirlama.ui.sheets_paste_dialog import SheetsPasteDialog


class MainWindow(QMainWindow):
    def __init__(self, on_back=None, mode: str = "normal"):
        super().__init__()
        self.mode = mode if mode in ("normal", "revise") else "normal"
        self.is_revise = self.mode == "revise"
        self.workflow = QuoteWorkflow()
        self.source_import_path: str | None = None  # orijinal ERP
        self.import_path: str | None = None  # doldurulmuş çalışma kopyası
        self.sheets_rows: list[SheetsRow] = []
        self.sheets_matrix: list[list[str]] = []
        self._quote_lines: list[QuoteLine] = []
        self._hitap_contacts: list[HitapKisi] = []
        self._on_back = on_back
        self.setWindowTitle(
            app_window_title(
                "Revize Teklif Formu Hazırlama"
                if self.is_revise
                else "İlk Teklif Formu Hazırlama"
            )
        )
        self.setWindowIcon(app_icon())
        self._build_ui()
        self._load_defaults()
        self._fit_sartlar_height()
        self.showMaximized()

    def _fit_sartlar_height(self) -> None:
        """Özel Şartlar / Şartlar kompakt kalsın (kaydırma ile okunur)."""
        height = 56
        for editor in (self.ozel_sartlar, self.sartlar):
            editor.setMinimumHeight(height)
            editor.setFixedHeight(height)

    def _bold_label(self, text: str) -> QLabel:
        label = QLabel(text)
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        label.setFixedHeight(18)
        return label

    def _labeled_col(self, title: str, widget: QWidget) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignTop)
        lay.addWidget(self._bold_label(title))
        lay.addWidget(widget)
        return box

    @staticmethod
    def _excel_file_icon(size: int = 22) -> QIcon:
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

    @staticmethod
    def _teklif_create_icon(size: int = 22) -> QIcon:
        """Belge + PDF hissi veren ikon."""
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # sayfa
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QColor("#4b5563"))
        painter.drawRoundedRect(3, 1, size - 8, size - 3, 2, 2)
        # satırlar
        painter.setPen(QColor("#9ca3af"))
        mid = size // 2
        for y in (6, 10, 14):
            painter.drawLine(6, y, size - 8, y)
        # köşe rozeti
        painter.setBrush(QColor("#c2410c"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(size - 12, size - 12, 10, 10, 2, 2)
        painter.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 6)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            size - 12, size - 12, 10, 10, Qt.AlignmentFlag.AlignCenter, "P"
        )
        painter.end()
        return QIcon(pm)

    def _make_group(self, title: str) -> QGroupBox:
        return QGroupBox(title)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        top = QHBoxLayout()
        if self._on_back:
            btn_back = QPushButton("← Ana Menü")
            btn_back.clicked.connect(self._go_back)
            top.addWidget(btn_back)
        top.addStretch()
        logo = make_logo_label(max_width=160)
        logo.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addWidget(logo)
        layout.addLayout(top)

        form_box = self._make_group("Teklif Bilgileri")
        form_lay = QVBoxLayout(form_box)
        form_lay.setContentsMargins(8, 8, 8, 8)
        form_lay.setSpacing(6)

        # Satır 1: Müşteri | Teklif No | [Revizyon] | Hazırlayan
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.setAlignment(Qt.AlignTop)

        self.customer_combo = QComboBox()
        self.customer_combo.currentIndexChanged.connect(self._on_customer_changed)
        row1.addWidget(
            self._labeled_col(
                "Müşteri",
                self._managed_row(
                    self.customer_combo, self._add_customer, self._edit_customer
                ),
            ),
            2,
        )

        self.teklif_no = QLineEdit()
        row1.addWidget(self._labeled_col("Teklif No", self.teklif_no), 2)

        self.revizyon = QLineEdit()
        if self.is_revise:
            row1.addWidget(self._labeled_col("Revizyon", self.revizyon), 1)

        self.hazirlayan = QComboBox()
        self.hazirlayan.setEditable(True)
        row1.addWidget(
            self._labeled_col(
                "Hazırlayan",
                self._managed_row(
                    self.hazirlayan, self._add_hazirlayan, self._edit_hazirlayan
                ),
            ),
            2,
        )
        form_lay.addLayout(row1)

        # Satır 2: Hitap Kişisi | Hitap Telefon
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.setAlignment(Qt.AlignTop)

        self.hitap_kisi = QComboBox()
        self.hitap_kisi.currentIndexChanged.connect(self._on_hitap_changed)
        row2.addWidget(
            self._labeled_col(
                "Hitap Kişisi",
                self._managed_row(
                    self.hitap_kisi, self._add_hitap_kisi, self._edit_hitap_kisi
                ),
            ),
            2,
        )

        self.hitap_telefon = QLineEdit()
        self.hitap_telefon.setReadOnly(True)
        row2.addWidget(self._labeled_col("Hitap Telefon", self.hitap_telefon), 2)
        form_lay.addLayout(row2)

        layout.addWidget(form_box)

        # Hitap ile İstek No arasında: Sheets | Import (kompakt)
        steps_top = QHBoxLayout()
        steps_top.setSpacing(8)

        sheets_box = self._make_group("Google Sheets")
        sheets_layout = QHBoxLayout(sheets_box)
        sheets_layout.setContentsMargins(8, 4, 8, 4)
        sheets_layout.setSpacing(8)
        self.sheets_label = QLabel(
            "İlk revizyonla birlikte satır yapıştır"
            if self.is_revise
            else "Satır yapıştırılmadı"
        )
        self.sheets_label.setWordWrap(True)
        self.sheets_label.setMaximumHeight(32)
        btn_sheets = QPushButton("Yapıştır / Düzenle")
        btn_sheets.setFixedHeight(28)
        btn_sheets.clicked.connect(self._paste_sheets)
        sheets_layout.addWidget(self.sheets_label, 1)
        sheets_layout.addWidget(btn_sheets, 0, Qt.AlignVCenter)
        sheets_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        steps_top.addWidget(sheets_box, 1)

        import_box = self._make_group("Import Excel")
        import_layout = QHBoxLayout(import_box)
        import_layout.setContentsMargins(8, 4, 8, 4)
        import_layout.setSpacing(8)
        self.import_label = QLabel("Dosya seçilmedi")
        self.import_label.setWordWrap(True)
        self.import_label.setMaximumHeight(32)
        btn_import = QPushButton(" Excel Seç...")
        btn_import.setIcon(self._excel_file_icon(20))
        btn_import.setIconSize(QSize(20, 20))
        btn_import.setFixedHeight(30)
        btn_import.clicked.connect(self._select_import)
        import_layout.addWidget(self.import_label, 1)
        import_layout.addWidget(btn_import, 0, Qt.AlignVCenter)
        import_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        steps_top.addWidget(import_box, 1)

        layout.addLayout(steps_top)

        # İstek No | Teslim Tarihi | Teslimat | Teslimat Şekli | Ödeme Şekli
        logistics = QWidget()
        logistics_row = QHBoxLayout(logistics)
        logistics_row.setContentsMargins(0, 0, 0, 0)
        logistics_row.setSpacing(8)
        logistics_row.setAlignment(Qt.AlignTop)

        self.istek_no = QLineEdit()
        self.istek_no.setPlaceholderText("Sheets yapıştırınca dolar")
        logistics_row.addWidget(self._labeled_col("İstek No", self.istek_no), 1)

        self.teslim_tarihi = QTextEdit()
        self.teslim_tarihi.setFixedHeight(72)
        self.teslim_tarihi.setPlaceholderText("Sheets yapıştırınca dolar")
        logistics_row.addWidget(self._labeled_col("Teslim Tarihi", self.teslim_tarihi), 4)

        self.teslimat = QComboBox()
        self.teslimat.setEditable(True)
        logistics_row.addWidget(
            self._labeled_col(
                "Teslimat",
                self._managed_row(
                    self.teslimat,
                    self._add_teslimat,
                    self._edit_teslimat,
                    stacked_buttons=True,
                ),
            ),
            2,
        )

        self.teslimat_sekli = QComboBox()
        self.teslimat_sekli.setEditable(True)
        logistics_row.addWidget(
            self._labeled_col(
                "Teslimat Şekli",
                self._managed_row(
                    self.teslimat_sekli,
                    self._add_teslimat_sekli,
                    self._edit_teslimat_sekli,
                    stacked_buttons=True,
                ),
            ),
            2,
        )

        self.odeme_sekli = QTextEdit()
        self.odeme_sekli.setFixedHeight(72)
        logistics_row.addWidget(self._labeled_col("Ödeme Şekli", self.odeme_sekli), 1)

        layout.addWidget(logistics)

        # Ürün satırları + şartlar
        lines_box = self._make_group("Ürün Satırları")
        lines_lay = QVBoxLayout(lines_box)
        lines_lay.setContentsMargins(6, 4, 6, 4)

        if self.is_revise:
            cols = [
                "Adet",
                "Antsis Ürün Kodu",
                "Açıklama",
                "Birim Fiyat",
                "İndirim",
                "İndirimli Birim Fiyat",
                "İndirimli Toplam Fiyat",
            ]
            # Form oranları: A ~1, B ~1.5, C-D ~3, E ~1.2, F ~1, G ~1.3, H ~1.3
            col_widths = [52, 120, 260, 90, 70, 110, 120]
        else:
            cols = [
                "Adet",
                "Antsis Ürün Kodu",
                "Açıklama",
                "Birim Fiyat",
                "Toplam Fiyat",
            ]
            # Form oranları: A, B, C-F (geniş), G, H
            col_widths = [52, 120, 320, 90, 100]

        self.lines_table = QTableWidget(0, len(cols))
        self.lines_table.setHorizontalHeaderLabels(cols)
        header = self.lines_table.horizontalHeader()
        header.setStretchLastSection(False)
        for i, width in enumerate(col_widths):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
            self.lines_table.setColumnWidth(i, width)
        # Açıklama sütunu esnek
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.lines_table.verticalHeader().setVisible(False)
        self.lines_table.setAlternatingRowColors(True)
        # Tek tıkla hemen yazılabilsin (QLineEdit gibi; çift tık gerekmesin)
        self.lines_table.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.lines_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.lines_table.setFocusPolicy(Qt.StrongFocus)
        # Seçim / odak mavi vurgusunu kapat
        self.lines_table.setStyleSheet(
            "QTableWidget::item:selected,"
            "QTableWidget::item:focus {"
            "  background: transparent;"
            "  color: palette(text);"
            "  outline: none;"
            "  border: none;"
            "}"
        )
        self.lines_table.itemChanged.connect(self._on_line_item_changed)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("Satır Ekle")
        btn_add.clicked.connect(self._add_line_row)
        btn_del = QPushButton("Satır Sil")
        btn_del.clicked.connect(self._remove_line_row)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        btn_row.addStretch(1)
        lines_lay.addLayout(btn_row)
        lines_lay.addWidget(self.lines_table)
        self._fit_lines_table_height()

        self.ozel_sartlar = QTextEdit()
        self.ozel_sartlar.setPlaceholderText("Özel şartları buraya yazın...")
        self.sartlar = QTextEdit()
        self.sartlar.setPlaceholderText(
            "Şartlar satır satır; istenmeyen satırı silin veya düzenleyin..."
        )
        # İçerik metni kalın olmasın (yalnızca alan etiketleri bold)
        normal = QFont(self.font())
        normal.setBold(False)
        self.ozel_sartlar.setFont(normal)
        self.sartlar.setFont(normal)
        sartlar_row = QHBoxLayout()
        sartlar_row.setContentsMargins(0, 4, 0, 0)
        sartlar_row.setSpacing(8)
        sartlar_row.addWidget(self._labeled_col("Özel Şartlar", self.ozel_sartlar), 1)
        sartlar_row.addWidget(self._labeled_col("Şartlar", self.sartlar), 1)
        lines_lay.addLayout(sartlar_row)
        layout.addWidget(lines_box)

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        # Çıktı / Teklif Oluştur her zaman görünür kalsın (kaydırma dışında)
        footer = QWidget()
        footer_lay = QVBoxLayout(footer)
        footer_lay.setContentsMargins(8, 4, 8, 8)
        footer_lay.setSpacing(6)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        out_box = self._make_group("Çıktı")
        out_layout = QVBoxLayout(out_box)
        out_layout.setContentsMargins(8, 4, 8, 4)
        default_out = str(Path.home() / "Desktop")
        self.output_dir = QLineEdit(default_out)
        btn_out = QPushButton("Klasör Seç...")
        btn_out.clicked.connect(self._select_output_dir)
        out_layout.addWidget(self._bold_label("Kayıt Klasörü"))
        out_row = QHBoxLayout()
        out_row.addWidget(self.output_dir, 1)
        out_row.addWidget(btn_out)
        out_layout.addLayout(out_row)
        out_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        bottom.addWidget(out_box, 2)

        action_col = QVBoxLayout()
        action_col.addStretch(1)
        btn_preview = QPushButton(" Önizleme (Excel)")
        btn_preview.setIcon(self._teklif_create_icon(20))
        btn_preview.setIconSize(QSize(20, 20))
        btn_preview.setMinimumHeight(34)
        btn_preview.clicked.connect(self._preview)
        btn_create = QPushButton(" Teklif Oluştur (Excel + PDF)")
        btn_create.setIcon(self._teklif_create_icon(22))
        btn_create.setIconSize(QSize(22, 22))
        btn_create.setMinimumHeight(34)
        btn_create.clicked.connect(self._generate)
        action_col.addWidget(btn_preview)
        action_col.addWidget(btn_create)
        action_col.addStretch(1)
        bottom.addLayout(action_col, 1)

        footer_lay.addLayout(bottom)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setMaximumHeight(40)
        footer_lay.addWidget(self.status)
        outer.addWidget(footer, 0)

    def _managed_row(
        self, combo: QComboBox, on_add, on_edit, *, stacked_buttons: bool = False
    ) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        btn_add = QPushButton("Ekle")
        btn_add.clicked.connect(on_add)
        btn_edit = QPushButton("Düzenle")
        btn_edit.clicked.connect(on_edit)
        if stacked_buttons:
            # Seçim kutusu, yanındaki Ekle ile üstten hizalı
            layout.setAlignment(Qt.AlignTop)
            combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            layout.addWidget(combo, 1, Qt.AlignTop)
            btn_col = QVBoxLayout()
            btn_col.setContentsMargins(0, 0, 0, 0)
            btn_col.setSpacing(2)
            btn_col.setAlignment(Qt.AlignTop)
            btn_col.addWidget(btn_add)
            btn_col.addWidget(btn_edit)
            layout.addLayout(btn_col, 0)
        else:
            layout.addWidget(combo, 1)
            layout.addWidget(btn_add)
            layout.addWidget(btn_edit)
        return row

    def _load_defaults(self) -> None:
        store = self.workflow.store
        self._reload_customers()
        self._reload_list_combo(self.hazirlayan, store.get_list("hazirlayanlar"))
        self._reload_list_combo(self.teslimat, store.get_list("teslimatlar"))
        self._reload_list_combo(self.teslimat_sekli, store.get_list("teslimat_sekilleri"))
        self._reload_hitap_kisileri()
        self._on_customer_changed()
        self.sartlar.setPlainText(
            "\n".join(load_default_sartlar(revise=self.is_revise))
        )

    def _reload_customers(self, select_code: str | None = None) -> None:
        current = select_code or self.customer_combo.currentData()
        self.customer_combo.blockSignals(True)
        self.customer_combo.clear()
        for customer in self.workflow.customers.list_customers():
            self.customer_combo.addItem(customer.name, customer.code)
        if current:
            index = self.customer_combo.findData(current)
            if index >= 0:
                self.customer_combo.setCurrentIndex(index)
        self.customer_combo.blockSignals(False)

    def _reload_list_combo(self, combo: QComboBox, items: list[str], select: str | None = None) -> None:
        current = select or combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        for item in items:
            combo.addItem(item)
        if current:
            index = combo.findText(current)
            if index >= 0:
                combo.setCurrentIndex(index)
            else:
                combo.setEditText(current)
        combo.blockSignals(False)

    def _reload_hitap_kisileri(self, select_ad: str | None = None) -> None:
        code = self.customer_combo.currentData()
        self._hitap_contacts = self.workflow.store.get_hitap_kisileri(code)
        preferred = select_ad or self.workflow.store.get_son_hitap(code or "")
        self.hitap_kisi.blockSignals(True)
        self.hitap_kisi.clear()
        for contact in self._hitap_contacts:
            self.hitap_kisi.addItem(contact.ad, contact.ad)
        if preferred:
            index = self.hitap_kisi.findText(preferred)
            if index >= 0:
                self.hitap_kisi.setCurrentIndex(index)
        elif self.hitap_kisi.count() > 0:
            self.hitap_kisi.setCurrentIndex(0)
        self.hitap_kisi.blockSignals(False)
        self._on_hitap_changed()

    def _current_hitap(self) -> HitapKisi | None:
        ad = self.hitap_kisi.currentText().strip()
        if not ad:
            return None
        for contact in self._hitap_contacts:
            if contact.ad == ad:
                return contact
        return HitapKisi(ad=ad, musteri_kodu=self.customer_combo.currentData() or "")

    def _set_hitap_fields(self, contact: HitapKisi | None) -> None:
        self.hitap_telefon.setText(contact.telefon if contact else "")

    def _on_customer_changed(self) -> None:
        code = self.customer_combo.currentData()
        if not code:
            return
        customer = self.workflow.customers.load(code)
        self.odeme_sekli.setPlainText(customer.varsayilan_odeme_sekli.strip())
        auto = generate_teklif_no(customer.teklif_no_oneki)
        if auto:
            self.teklif_no.setText(auto)
        self._reload_hitap_kisileri()

    def _on_hitap_changed(self) -> None:
        contact = self._current_hitap()
        self._set_hitap_fields(contact)
        code = self.customer_combo.currentData()
        if code and contact and contact.ad:
            self.workflow.store.set_son_hitap(code, contact.ad)

    def _add_customer(self) -> None:
        dialog = CustomerDialog(self)
        if dialog.exec() != CustomerDialog.Accepted:
            return
        customer = dialog.customer()
        if not customer:
            return
        try:
            self.workflow.customers.save(customer)
        except Exception as exc:
            QMessageBox.critical(self, "Hata", str(exc))
            return
        self._reload_customers(select_code=customer.code)
        self._on_customer_changed()

    def _edit_customer(self) -> None:
        code = self.customer_combo.currentData()
        if not code:
            QMessageBox.warning(self, "Eksik bilgi", "Düzenlenecek müşteriyi seçin.")
            return
        customer = self.workflow.customers.load(code)
        dialog = CustomerDialog(self, customer=customer, allow_delete=True)
        if dialog.exec() != CustomerDialog.Accepted:
            return
        if dialog.was_deleted():
            try:
                self.workflow.customers.delete(code)
                self.workflow.store.delete_hitap_for_customer(code)
            except Exception as exc:
                QMessageBox.critical(self, "Hata", str(exc))
                return
            self._reload_customers()
            if self.customer_combo.count() > 0:
                self._on_customer_changed()
            else:
                self.hitap_kisi.clear()
                self.hitap_telefon.clear()
                self.odeme_sekli.clear()
            return
        updated = dialog.customer()
        if not updated:
            return
        try:
            self.workflow.customers.save(updated)
        except Exception as exc:
            QMessageBox.critical(self, "Hata", str(exc))
            return
        self._reload_customers(select_code=updated.code)
        self._on_customer_changed()

    def _add_hitap_kisi(self) -> None:
        code = self.customer_combo.currentData()
        if not code:
            QMessageBox.warning(self, "Eksik bilgi", "Önce müşteri seçin.")
            return
        customer = self.workflow.customers.load(code)
        dialog = HitapKisiDialog(code, customer.name, self)
        if dialog.exec() != HitapKisiDialog.Accepted:
            return
        contact = dialog.contact()
        if not contact:
            return
        try:
            self.workflow.store.save_hitap_kisi(contact)
        except Exception as exc:
            QMessageBox.critical(self, "Hata", str(exc))
            return
        self._reload_hitap_kisileri(select_ad=contact.ad)

    def _edit_hitap_kisi(self) -> None:
        contact = self._current_hitap()
        if not contact:
            QMessageBox.warning(self, "Eksik bilgi", "Düzenlenecek hitap kişisini seçin.")
            return
        code = self.customer_combo.currentData()
        customer = self.workflow.customers.load(code)
        builtin = self.workflow.store.is_builtin_hitap(code, contact.ad)
        dialog = HitapKisiDialog(
            code,
            customer.name,
            self,
            contact=contact,
            builtin=builtin,
            allow_delete=True,
        )
        if dialog.exec() != HitapKisiDialog.Accepted:
            return
        if dialog.was_deleted():
            self.workflow.store.delete_hitap_kisi(code, dialog.original_ad())
            self._reload_hitap_kisileri()
            return
        updated = dialog.contact()
        if not updated:
            QMessageBox.warning(self, "Eksik bilgi", "Ad soyad zorunludur.")
            return
        try:
            self.workflow.store.save_hitap_kisi(updated, original_ad=dialog.original_ad())
        except Exception as exc:
            QMessageBox.critical(self, "Hata", str(exc))
            return
        self._reload_hitap_kisileri(select_ad=updated.ad)

    def _manage_list_item(self, key: str, combo: QComboBox, title: str, label: str, add: bool) -> None:
        store = self.workflow.store
        if add:
            dialog = ListItemDialog(f"{title} Ekle", label, self)
            if dialog.exec() != ListItemDialog.Accepted:
                return
            value = dialog.text()
            if not value:
                QMessageBox.warning(self, "Eksik bilgi", f"{label} boş olamaz.")
                return
            try:
                store.add_list_item(key, value)
            except ValueError as exc:
                QMessageBox.warning(self, "Uyarı", str(exc))
                return
            self._reload_list_combo(combo, store.get_list(key), select=value)
            return

        current = combo.currentText().strip()
        if not current:
            QMessageBox.warning(self, "Eksik bilgi", f"Düzenlenecek {label.lower()} seçin.")
            return
        dialog = ListItemDialog(f"{title} Düzenle", label, self, value=current, allow_delete=True)
        if dialog.exec() != ListItemDialog.Accepted:
            return
        if dialog.was_deleted():
            store.remove_list_item(key, current)
            self._reload_list_combo(combo, store.get_list(key))
            return
        new_value = dialog.text()
        if not new_value:
            QMessageBox.warning(self, "Eksik bilgi", f"{label} boş olamaz.")
            return
        try:
            store.update_list_item(key, current, new_value)
        except ValueError as exc:
            QMessageBox.warning(self, "Uyarı", str(exc))
            return
        self._reload_list_combo(combo, store.get_list(key), select=new_value)

    def _add_hazirlayan(self) -> None:
        self._manage_list_item("hazirlayanlar", self.hazirlayan, "Hazırlayan", "Hazırlayan", add=True)

    def _edit_hazirlayan(self) -> None:
        self._manage_list_item("hazirlayanlar", self.hazirlayan, "Hazırlayan", "Hazırlayan", add=False)

    def _add_teslimat(self) -> None:
        self._manage_list_item("teslimatlar", self.teslimat, "Teslimat", "Teslimat", add=True)

    def _edit_teslimat(self) -> None:
        self._manage_list_item("teslimatlar", self.teslimat, "Teslimat", "Teslimat", add=False)

    def _add_teslimat_sekli(self) -> None:
        self._manage_list_item("teslimat_sekilleri", self.teslimat_sekli, "Teslimat Şekli", "Teslimat Şekli", add=True)

    def _edit_teslimat_sekli(self) -> None:
        self._manage_list_item("teslimat_sekilleri", self.teslimat_sekli, "Teslimat Şekli", "Teslimat Şekli", add=False)

    def _paste_sheets(self) -> None:
        dialog = SheetsPasteDialog(
            self,
            initial_matrix=self.sheets_matrix or None,
            revise=self.is_revise,
        )
        if dialog.exec() != QDialog.Accepted:
            return
        self.sheets_rows = dialog.rows()
        self.sheets_matrix = dialog.matrix()
        n = len(self.sheets_rows)
        self.sheets_label.setText(f"{n} Sheets satırı hazır (düzenlenebilir)")

        # Sheets master → UI hemen dolsun
        applied = self.workflow.apply_sheets(
            self.sheets_rows, revise=self.is_revise
        )
        self._fill_lines_table(applied.quote_lines)
        if applied.teslim_tarihi_text:
            self.teslim_tarihi.setPlainText(applied.teslim_tarihi_text)
        if applied.teklif_no and not self.teklif_no.text().strip():
            self.teklif_no.setText(applied.teklif_no)
        if applied.istek_no:
            self.istek_no.setText(applied.istek_no)
        if self.is_revise and applied.form_revizyon and hasattr(self, "revizyon"):
            if not self.revizyon.text().strip():
                self.revizyon.setText(applied.form_revizyon)
        # Özel Şartlar paneli Sheets'ten doldurulmaz (boş kalır)

        if self.source_import_path:
            self._run_enrich(self.source_import_path)
        else:
            msg = (
                f"{n} Sheets satırı tabloya işlendi "
                f"({len(applied.quote_lines)} ürün satırı). "
                "Import Excel seçerseniz eksikler tamamlanır ve karşılaştırma yapılır."
            )
            if applied.warnings:
                msg += "\n" + "\n".join(applied.warnings)
            self.status.setText(msg)
            if self.is_revise and applied.warnings:
                QMessageBox.information(
                    self,
                    "Revize Sheets",
                    msg,
                )

    def _select_import(self) -> None:
        if not self.sheets_rows:
            QMessageBox.warning(
                self,
                "Eksik adım",
                "Önce 'Yapıştır / Düzenle' ile Google satırlarını ekleyin.\n"
                "Sheets master kaynaktır; Excel eksikleri tamamlar ve "
                "çelişkilerde uyarır.",
            )
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Excel Seç",
            str(Path.home() / "Desktop"),
            "Excel Dosyaları (*.xlsx *.xlsm)",
        )
        if not path:
            return
        self._run_enrich(path)

    def _run_enrich(self, source_path: str) -> None:
        try:
            result = self.workflow.enrich_import(
                source_path,
                self.sheets_rows,
                revise=self.is_revise,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Hata", str(exc))
            return

        self.source_import_path = source_path
        self.import_path = str(result.enriched_path)
        if result.istek_no:
            self.istek_no.setText(result.istek_no)
        if result.teslim_tarihi_text:
            self.teslim_tarihi.setPlainText(result.teslim_tarihi_text)
        if (
            self.is_revise
            and result.form_revizyon
            and hasattr(self, "revizyon")
            and not self.revizyon.text().strip()
        ):
            self.revizyon.setText(result.form_revizyon)
        self._fill_lines_table(result.quote_lines)
        self.import_label.setText(
            f"Dolduruldu ({result.filled_rows} satır): {result.enriched_path.name}\n"
            f"Kaynak: {Path(source_path).name}"
        )

        parts: list[str] = []
        if result.matches:
            parts.append("Eşleşenler:")
            parts.extend(result.matches)
            parts.append("")
        if result.conflicts:
            parts.append("Çelişkiler (Sheets kullanıldı):")
            parts.extend(result.conflicts)
            parts.append("")
        if result.warnings:
            parts.extend(result.warnings)
        msg = "\n".join(parts) if parts else "Import tamamlandı; çelişki yok."
        self.status.setText(msg)

        next_step = (
            "\n\nŞimdi 'Teklif Oluştur (Excel + PDF)' kullanabilirsiniz."
        )
        title = "Import Excel — karşılaştırma"
        body = (
            "Sheets master kaynak olarak uygulandı.\n"
            "Excel eksik alanları tamamladı; doldurulmuş kopya üretildi.\n\n"
            + msg
            + next_step
        )
        if result.conflicts:
            QMessageBox.warning(self, title, body)
        else:
            QMessageBox.information(self, title, body)

    def _fit_lines_table_height(self) -> None:
        rows = max(1, self.lines_table.rowCount())
        row_h = max(26, self.lines_table.verticalHeader().defaultSectionSize())
        header_h = max(26, self.lines_table.horizontalHeader().height())
        # Ürün tablosu kompakt: boşken ~4 satır, doluyken en fazla 8
        visible = max(4, min(rows, 8))
        height = header_h + visible * row_h + 10
        self.lines_table.setMinimumHeight(height)
        self.lines_table.setMaximumHeight(header_h + 8 * row_h + 10)
        self.lines_table.setFixedHeight(height)

    def _empty_quote_line(self, row_number: int) -> QuoteLine:
        return QuoteLine(
            row_number=row_number,
            adet=0,
            ants_is_urun_kodu="",
            aciklama="",
            birim_fiyat=Decimal("0"),
            toplam_fiyat=Decimal("0"),
            indirimli_birim_fiyat=Decimal("0") if self.is_revise else None,
        )

    def _make_table_item(self, text: str, *, left: bool = False) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(
            Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
        )
        item.setTextAlignment(
            (Qt.AlignLeft | Qt.AlignVCenter) if left else Qt.AlignCenter
        )
        return item

    def _add_line_row(self) -> None:
        row = self.lines_table.rowCount()
        self.lines_table.blockSignals(True)
        self.lines_table.insertRow(row)
        if self.is_revise:
            defaults = ["1", "", "", "0,00", "0,00%", "0,00", "0,00"]
        else:
            defaults = ["1", "", "", "0,00", "0,00"]
        for col, text in enumerate(defaults):
            self.lines_table.setItem(
                row, col, self._make_table_item(text, left=(col == 2))
            )
        line = self._empty_quote_line(row + 1)
        line.adet = 1
        self._quote_lines.append(line)
        self.lines_table.blockSignals(False)
        self._fit_lines_table_height()
        self.lines_table.setCurrentCell(row, 0)
        item = self.lines_table.item(row, 0)
        if item is not None:
            self.lines_table.editItem(item)

    def _remove_line_row(self) -> None:
        row = self.lines_table.currentRow()
        if row < 0:
            row = self.lines_table.rowCount() - 1
        if row < 0:
            return
        self.lines_table.removeRow(row)
        if row < len(self._quote_lines):
            del self._quote_lines[row]
        self._fit_lines_table_height()

    def _fill_lines_table(self, lines: list[QuoteLine]) -> None:
        self._quote_lines = list(lines)
        self.lines_table.blockSignals(True)
        self.lines_table.setRowCount(0)
        self.lines_table.setRowCount(len(lines))
        for row, line in enumerate(lines):
            if self.is_revise:
                birim = line.birim_fiyat
                indirimli = (
                    line.indirimli_birim_fiyat
                    if line.indirimli_birim_fiyat is not None
                    else line.birim_fiyat
                )
                indirim = Decimal("0")
                if birim > 0:
                    indirim = (Decimal("1") - (indirimli / birim)).quantize(
                        Decimal("0.0001")
                    )
                values = [
                    str(line.adet),
                    line.ants_is_urun_kodu,
                    line.aciklama,
                    self._format_decimal(birim),
                    self._format_percent(indirim),
                    self._format_decimal(indirimli),
                    self._format_decimal(line.toplam_fiyat),
                ]
            else:
                values = [
                    str(line.adet),
                    line.ants_is_urun_kodu,
                    line.aciklama,
                    self._format_decimal(line.birim_fiyat),
                    self._format_decimal(line.toplam_fiyat),
                ]
            for col, text in enumerate(values):
                self.lines_table.setItem(
                    row, col, self._make_table_item(text, left=(col == 2))
                )
            if "\n" in (line.aciklama or ""):
                self.lines_table.resizeRowToContents(row)
        self.lines_table.blockSignals(False)
        self._fit_lines_table_height()

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        q = value.quantize(Decimal("0.01"))
        text = f"{q:.2f}"
        return text.replace(".", ",")

    @staticmethod
    def _format_percent(value: Decimal) -> str:
        # 0.10 → 10,00%
        pct = (value * Decimal("100")).quantize(Decimal("0.01"))
        return f"{str(pct).replace('.', ',')}%"

    @staticmethod
    def _parse_decimal(text: str) -> Decimal:
        raw = (text or "").strip().replace(" ", "")
        raw = raw.replace("$", "").replace("€", "").replace("₺", "").replace("%", "")
        if "," in raw and "." in raw:
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", ".")
        try:
            return Decimal(raw)
        except (InvalidOperation, ValueError):
            return Decimal("0")

    def _parse_percent(self, text: str) -> Decimal:
        """'10%' veya '0,10' → oran (0.10)."""
        raw = (text or "").strip().replace(" ", "")
        if raw.endswith("%"):
            return (self._parse_decimal(raw[:-1]) / Decimal("100")).quantize(
                Decimal("0.0001")
            )
        val = self._parse_decimal(raw)
        # 10 gibi büyük sayı yüzde kabul
        if val > 1:
            return (val / Decimal("100")).quantize(Decimal("0.0001"))
        return val

    def _on_line_item_changed(self, item: QTableWidgetItem) -> None:
        row = item.row()
        col = item.column()
        if row < 0:
            return

        def text(c: int) -> str:
            it = self.lines_table.item(row, c)
            return it.text() if it else ""

        def set_text(c: int, value: str) -> None:
            it = self.lines_table.item(row, c)
            if it is None:
                it = self._make_table_item("", left=(c == 2))
                self.lines_table.setItem(row, c, it)
            it.setText(value)

        try:
            adet = int(float(text(0).replace(",", ".") or "0"))
        except ValueError:
            adet = 0

        self.lines_table.blockSignals(True)
        try:
            if self.is_revise:
                # 0 Adet, 1 Kod, 2 Açıklama, 3 Birim, 4 İndirim, 5 İndirimli Birim, 6 İndirimli Toplam
                birim = self._parse_decimal(text(3))
                if col == 4:
                    # İndirim değişti → indirimli birim = birim * (1 - indirim)
                    ratio = self._parse_percent(text(4))
                    indirimli = (birim * (Decimal("1") - ratio)).quantize(
                        Decimal("0.01")
                    )
                    set_text(5, self._format_decimal(indirimli))
                else:
                    indirimli = self._parse_decimal(text(5))
                    if col in (3, 5) and birim > 0:
                        ratio = (Decimal("1") - (indirimli / birim)).quantize(
                            Decimal("0.0001")
                        )
                        set_text(4, self._format_percent(ratio))
                    elif col in (3, 5) and birim == 0:
                        set_text(4, self._format_percent(Decimal("0")))
                if col in (0, 3, 4, 5):
                    indirimli = self._parse_decimal(text(5))
                    toplam = (indirimli * Decimal(adet)).quantize(Decimal("0.01"))
                    set_text(6, self._format_decimal(toplam))
            else:
                # 0 Adet, 1 Kod, 2 Açıklama, 3 Birim, 4 Toplam
                if col in (0, 3):
                    birim = self._parse_decimal(text(3))
                    toplam = (birim * Decimal(adet)).quantize(Decimal("0.01"))
                    set_text(4, self._format_decimal(toplam))
        finally:
            self.lines_table.blockSignals(False)

    def _lines_from_table(self) -> list[QuoteLine]:
        lines: list[QuoteLine] = []
        for row in range(self.lines_table.rowCount()):
            base = self._quote_lines[row] if row < len(self._quote_lines) else None

            def cell(col: int) -> str:
                item = self.lines_table.item(row, col)
                return item.text().strip() if item else ""

            try:
                adet = int(float(cell(0).replace(",", ".") or "0"))
            except ValueError:
                adet = 0
            code = cell(1)
            aciklama = cell(2)
            # Boş satırları atla
            if adet <= 0 and not code and not aciklama.strip():
                continue

            if self.is_revise:
                birim = self._parse_decimal(cell(3))
                indirimli = self._parse_decimal(cell(5))
                toplam = self._parse_decimal(cell(6))
                if toplam == 0 and adet:
                    toplam = (indirimli * Decimal(adet)).quantize(Decimal("0.01"))
                lines.append(
                    QuoteLine(
                        row_number=len(lines) + 1,
                        adet=adet,
                        ants_is_urun_kodu=code,
                        aciklama=aciklama,
                        birim_fiyat=birim,
                        toplam_fiyat=toplam,
                        indirimli_birim_fiyat=indirimli,
                        teslim_suresi_parcasi=base.teslim_suresi_parcasi if base else "",
                        stok_kodu=base.stok_kodu if base else "",
                        stok_aciklama=base.stok_aciklama if base else "",
                        termin_tarihi=base.termin_tarihi if base else None,
                        kalite_provizyonlari=base.kalite_provizyonlari if base else "",
                        teknik_resim_sartname=base.teknik_resim_sartname if base else "",
                        kalem_revizyon=base.kalem_revizyon if base else "",
                    )
                )
            else:
                birim = self._parse_decimal(cell(3))
                toplam_text = cell(4)
                toplam = (
                    self._parse_decimal(toplam_text)
                    if toplam_text
                    else birim * Decimal(adet)
                )
                lines.append(
                    QuoteLine(
                        row_number=len(lines) + 1,
                        adet=adet,
                        ants_is_urun_kodu=code,
                        aciklama=aciklama,
                        birim_fiyat=birim,
                        toplam_fiyat=toplam,
                        teslim_suresi_parcasi=base.teslim_suresi_parcasi if base else "",
                        stok_kodu=base.stok_kodu if base else "",
                        stok_aciklama=base.stok_aciklama if base else "",
                        termin_tarihi=base.termin_tarihi if base else None,
                        kalite_provizyonlari=base.kalite_provizyonlari if base else "",
                        teknik_resim_sartname=base.teknik_resim_sartname if base else "",
                        kalem_revizyon=base.kalem_revizyon if base else "",
                    )
                )
        return lines

    def _select_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Çıktı Klasörü", self.output_dir.text())
        if path:
            self.output_dir.setText(path)

    def _parse_ozel_sartlar(self) -> list[str]:
        return [line.strip() for line in self.ozel_sartlar.toPlainText().splitlines() if line.strip()]

    def _parse_sartlar(self) -> list[str]:
        return [line.strip() for line in self.sartlar.toPlainText().splitlines() if line.strip()]

    def _build_request(self) -> QuoteRequest | None:
        quote_lines = self._lines_from_table()
        if not quote_lines:
            QMessageBox.warning(
                self,
                "Eksik bilgi",
                "Ürün satırı yok. 'Satır Ekle' ile ekleyin veya Import Excel seçin.",
            )
            return None

        hitap = self._current_hitap()
        if not hitap or not hitap.ad.strip():
            QMessageBox.warning(self, "Eksik bilgi", "Lütfen hitap kişisi seçin.")
            return None

        if not self.teklif_no.text().strip():
            QMessageBox.warning(self, "Eksik bilgi", "Teklif No zorunludur.")
            return None

        return QuoteRequest(
            customer_code=self.customer_combo.currentData(),
            teklif_no=self.teklif_no.text(),
            hitap_kisi=hitap.ad,
            hitap_adres_satirlari=[],
            hitap_telefon=hitap.telefon,
            hazirlayan=self.hazirlayan.currentText(),
            teslimat=self.teslimat.currentText(),
            teslimat_sekli=self.teslimat_sekli.currentText(),
            odeme_sekli=self.odeme_sekli.toPlainText(),
            import_excel_path=self.import_path or "",
            source_excel_path=self.source_import_path or "",
            sartlar=self._parse_sartlar(),
            ozel_sartlar=self._parse_ozel_sartlar(),
            output_dir=self.output_dir.text(),
            revizyon=self.revizyon.text() if self.is_revise else "",
            sheets_rows=[],
            is_revise=self.is_revise,
            istek_no=self.istek_no.text().strip(),
            teslim_tarihi_text=self.teslim_tarihi.toPlainText().strip(),
            quote_lines=quote_lines,
        )

    def _preview(self) -> None:
        request = self._build_request()
        if request is None:
            return
        try:
            result = self.workflow.generate(
                request, create_pdf=False, preview=True
            )
        except Exception as exc:
            QMessageBox.critical(self, "Hata", str(exc))
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(result.document_path)))
        msg = (
            f"Önizleme Excel açıldı:\n{result.document_path.name}\n\n"
            "Kontrol edip ardından 'Teklif Oluştur (Excel + PDF)' ile "
            "kalıcı çıktıyı üretebilirsiniz.\n"
            "Önizleme dosyası geçicidir; uygulama kapanınca silinir."
        )
        if result.warnings:
            msg += "\n\nUyarılar:\n" + "\n".join(result.warnings)
        self.status.setText(msg)
        QMessageBox.information(self, "Önizleme", msg)

    def _generate(self) -> None:
        request = self._build_request()
        if request is None:
            return

        try:
            result = self.workflow.generate(request, create_pdf=True)
        except Exception as exc:
            QMessageBox.critical(self, "Hata", str(exc))
            return

        folder = result.output_folder or result.document_path.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        lines = [
            f"Klasör: {folder}",
            "",
            "İçerik:",
        ]
        n = 1
        if result.original_excel_path:
            lines.append(f"{n}) Import (ilk hali): {result.original_excel_path.name}")
            n += 1
        if result.enriched_excel_path:
            lines.append(
                f"{n}) Import (doldurulmuş): {result.enriched_excel_path.name}"
            )
            n += 1
        lines.append(f"{n}) Teklif formu (Excel): {result.document_path.name}")
        n += 1
        if result.pdf_path:
            lines.append(f"{n}) Teklif PDF: {result.pdf_path.name}")
        else:
            lines.append(f"{n}) Teklif PDF: üretilemedi (uyarılara bakın)")
        if result.warnings:
            lines.append("")
            lines.append("Uyarılar:")
            lines.extend(result.warnings)
        msg = "\n".join(lines)
        self.status.setText(msg)
        QMessageBox.information(self, "Tamamlandı", msg)

    def _go_back(self) -> None:
        if self._on_back:
            self._on_back()
        else:
            self.close()


def run_app() -> None:
    from teklif_hazirlama.ui.start_window import run_app as run_start_app

    run_start_app()
