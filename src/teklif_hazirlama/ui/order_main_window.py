from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, QSize, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from teklif_hazirlama import app_window_title
from teklif_hazirlama.application.order_workflow import OrderWorkflow
from teklif_hazirlama.core.models import OrderRow
from teklif_hazirlama.core.order_clipboard import ORDER_SHEETS_HEADERS
from teklif_hazirlama.core.quality_highlight import (
    format_aciklama_html,
    format_quality_html,
)
from teklif_hazirlama.ui.branding import (
    app_icon,
    excel_file_icon,
    make_logo_label,
    pdf_file_icon,
    style_action_button,
    style_file_button,
)

KALITE_COL = 17
ACIKLAMA_COL = 18


class OrderMainWindow(QMainWindow):
    def __init__(self, on_back=None):
        super().__init__()
        self.workflow = OrderWorkflow()
        self._on_back = on_back
        self.excel_path: str | None = None
        self.pdf_path: str | None = None
        self._rows: list[OrderRow] = []
        self.setWindowTitle(app_window_title("Antsis Sipariş İşleme"))
        self.setWindowIcon(app_icon())
        self._build_ui()
        self.showMaximized()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
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

        form_box = QGroupBox("Sipariş Bilgileri")
        form = QFormLayout(form_box)
        self.firma_combo = QComboBox()
        self.firma_combo.setEditable(True)
        self.firma_combo.addItems(["Roketsan"])
        self.firma_combo.setCurrentText("Roketsan")
        form.addRow("Firma", self.firma_combo)
        layout.addWidget(form_box)

        files_box = QGroupBox("Kaynak Dosyalar")
        files_layout = QVBoxLayout(files_box)
        self.pdf_label = QLabel("PDF seçilmedi")
        self.pdf_label.setWordWrap(True)
        self.excel_label = QLabel("Excel seçilmedi")
        self.excel_label.setWordWrap(True)

        pdf_row = QHBoxLayout()
        pdf_row.addWidget(self.pdf_label, 1)
        btn_pdf = QPushButton(" PDF Seç...")
        btn_pdf.setIcon(pdf_file_icon(20))
        btn_pdf.setIconSize(QSize(20, 20))
        style_file_button(btn_pdf)
        btn_pdf.clicked.connect(self._select_pdf)
        pdf_row.addWidget(btn_pdf)
        files_layout.addLayout(pdf_row)

        excel_row = QHBoxLayout()
        excel_row.addWidget(self.excel_label, 1)
        btn_excel = QPushButton(" Excel Seç...")
        btn_excel.setIcon(excel_file_icon(20))
        btn_excel.setIconSize(QSize(20, 20))
        style_file_button(btn_excel)
        btn_excel.clicked.connect(self._select_excel)
        excel_row.addWidget(btn_excel)
        files_layout.addLayout(excel_row)
        layout.addWidget(files_box)

        action_row = QHBoxLayout()
        btn_parse = QPushButton("Oku / Birleştir")
        style_action_button(btn_parse, primary=True)
        btn_parse.clicked.connect(self._parse_files)
        btn_copy_main = QPushButton("Ana Sipariş Kopyala")
        style_action_button(btn_copy_main)
        btn_copy_main.clicked.connect(self._copy_rows)
        btn_copy_anten = QPushButton("Anten Sipariş Kopyala")
        style_action_button(btn_copy_anten)
        btn_copy_anten.clicked.connect(self._copy_anten_rows)
        btn_copy_elektronik = QPushButton("Elektronik Sipariş Kopyala")
        style_action_button(btn_copy_elektronik)
        btn_copy_elektronik.clicked.connect(self._copy_elektronik_rows)
        action_row.addWidget(btn_parse)
        action_row.addWidget(btn_copy_main)
        action_row.addWidget(btn_copy_anten)
        action_row.addWidget(btn_copy_elektronik)
        action_row.addStretch()
        self.count_label = QLabel("0 satır")
        action_row.addWidget(self.count_label)
        layout.addLayout(action_row)

        self.table = QTableWidget(0, len(ORDER_SHEETS_HEADERS))
        self.table.setHorizontalHeaderLabels(ORDER_SHEETS_HEADERS)
        self.table.horizontalHeader().setDefaultSectionSize(130)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setDefaultSectionSize(36)
        layout.addWidget(self.table, 1)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

    def _select_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Sipariş PDF Seç",
            str(Path.home() / "Desktop"),
            "PDF Dosyaları (*.pdf)",
        )
        if path:
            self.pdf_path = path
            self.pdf_label.setText(path)

    def _select_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Sipariş Excel Seç",
            str(Path.home() / "Desktop"),
            "Excel Dosyaları (*.xlsx *.xlsm *.xls)",
        )
        if path:
            self.excel_path = path
            self.excel_label.setText(path)

    def _parse_files(self) -> None:
        if not self.excel_path:
            QMessageBox.warning(self, "Eksik bilgi", "Lütfen sipariş Excel dosyasını seçin.")
            return
        try:
            self._rows = self.workflow.build_rows(
                excel_path=self.excel_path,
                pdf_path=self.pdf_path,
                firma=self.firma_combo.currentText().strip(),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Hata", str(exc))
            return
        self._load_rows()
        self.status.setText(
            "Satırlar oluşturuldu. Gerekirse hücreleri düzenleyip 'Ana Sipariş Kopyala' kullanın."
        )

    def _load_rows(self) -> None:
        self.table.setRowCount(len(self._rows))
        for row_index, row in enumerate(self._rows):
            values = [
                row.no,
                row.firma,
                row.antsis_parca_no,
                row.siparis_satir_no,
                row.musteri_parca_no,
                row.proje,
                row.siparis_adedi,
                row.siparis_tarihi,
                row.siparis_numarasi,
                row.planlanan_sevk_tarihi,
                row.sevk_tarihi,
                row.fatura_durumu,
                row.birim_fiyat,
                row.toplam_fiyat,
                row.sevkiyata_kalan_sure,
                row.teknik_resim,
                row.urun_revizyonu,
                row.kalite_provizyonlari,
                row.aciklama,
            ]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                self.table.setItem(row_index, col_index, item)
                if col_index == KALITE_COL:
                    self._set_rich_cell(row_index, col_index, format_quality_html(value))
                elif col_index == ACIKLAMA_COL:
                    self._set_rich_cell(row_index, col_index, format_aciklama_html(value))
                    self.table.setRowHeight(row_index, max(54, self.table.rowHeight(row_index)))
        self.count_label.setText(f"{len(self._rows)} satır")

    def _set_rich_cell(self, row: int, col: int, html_text: str) -> None:
        label = QLabel(html_text)
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(True)
        label.setMargin(2)
        self.table.setCellWidget(row, col, label)

    def _copy_rows(self) -> None:
        self._copy_to_clipboard(
            title="Ana Sipariş Kopyala",
            text_builder=self.workflow.build_clipboard_text_from_rows,
            html_builder=self.workflow.build_clipboard_html_from_rows,
        )

    def _copy_anten_rows(self) -> None:
        self._copy_to_clipboard(
            title="Anten Sipariş Kopyala",
            text_builder=self.workflow.build_anten_clipboard_text_from_rows,
            html_builder=self.workflow.build_anten_clipboard_html_from_rows,
        )

    def _copy_elektronik_rows(self) -> None:
        self._copy_to_clipboard(
            title="Elektronik Sipariş Kopyala",
            text_builder=self.workflow.build_elektronik_clipboard_text_from_rows,
            html_builder=self.workflow.build_elektronik_clipboard_html_from_rows,
        )

    def _copy_to_clipboard(self, *, title: str, text_builder, html_builder) -> None:
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Eksik bilgi", "Önce satırları oluşturun.")
            return
        rows = self._rows_from_table()
        text = text_builder(rows)
        html_text = html_builder(rows)
        mime = QMimeData()
        mime.setText(text)
        mime.setHtml(html_text)
        QApplication.clipboard().setMimeData(mime)
        msg = f"{len(rows)} satır panoya kopyalandı (kritik kalite kodları kırmızı/kalın)."
        self.status.setText(msg)
        QMessageBox.information(self, title, msg)

    def _rows_from_table(self) -> list[OrderRow]:
        rows: list[OrderRow] = []
        for row_index in range(self.table.rowCount()):
            values = []
            for col_index in range(self.table.columnCount()):
                item = self.table.item(row_index, col_index)
                values.append(item.text() if item else "")
            rows.append(
                OrderRow(
                    no=values[0],
                    firma=values[1],
                    antsis_parca_no=values[2],
                    siparis_satir_no=values[3],
                    musteri_parca_no=values[4],
                    proje=values[5],
                    siparis_adedi=values[6],
                    siparis_tarihi=values[7],
                    siparis_numarasi=values[8],
                    planlanan_sevk_tarihi=values[9],
                    sevk_tarihi=values[10],
                    fatura_durumu=values[11],
                    birim_fiyat=values[12],
                    toplam_fiyat=values[13],
                    sevkiyata_kalan_sure=values[14],
                    teknik_resim=values[15],
                    urun_revizyonu=values[16],
                    kalite_provizyonlari=values[17],
                    aciklama=values[18],
                )
            )
        return rows

    def _go_back(self) -> None:
        if self._on_back:
            self._on_back()
        else:
            self.close()
