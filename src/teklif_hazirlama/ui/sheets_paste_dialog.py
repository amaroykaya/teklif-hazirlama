from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from teklif_hazirlama.core.models import SheetsRow
from teklif_hazirlama.core.sheets_tsv_parser import (
    COL_LETTER,
    EMPTY_PLACEHOLDER,
    SHEETS_COLUMNS_A_TO_W,
    SheetsTsvParseError,
    fill_row_empty_with_na,
    first_row_is_header,
    parse_clipboard_tsv,
    rows_from_table_matrix,
)


class SheetsTableWidget(QTableWidget):
    """Ctrl+V ile TSV yapıştırmayı A–W sütunlarına hizalar."""

    def keyPressEvent(self, event) -> None:
        if event.matches(QKeySequence.Paste):
            self.paste_from_clipboard(replace=not self._has_any_data())
            return
        if event.matches(QKeySequence.Delete) or event.key() == Qt.Key_Backspace:
            for item in self.selectedItems():
                item.setText("")
            return
        super().keyPressEvent(event)

    def paste_from_clipboard(self, *, replace: bool = False) -> int:
        text = QApplication.clipboard().text()
        matrix = parse_clipboard_tsv(text)
        if not matrix:
            return 0
        if first_row_is_header(matrix[0]):
            matrix = matrix[1:]
        matrix = [r for r in matrix if any(c.strip() for c in r)]
        if not matrix:
            return 0

        if replace or not self._has_any_data():
            self.setRowCount(len(matrix))
            for r, row in enumerate(matrix):
                filled = fill_row_empty_with_na(row)
                for c, value in enumerate(filled):
                    if c >= self.columnCount():
                        break
                    self.setItem(r, c, QTableWidgetItem(value))
            self._trim_trailing_empty_rows()
            return len(matrix)

        start_row = max(0, self.currentRow())
        start_col = max(0, self.currentColumn())
        needed = start_row + len(matrix)
        if self.rowCount() < needed:
            self.setRowCount(needed)

        for r_off, row in enumerate(matrix):
            filled = fill_row_empty_with_na(row)
            for c_off, value in enumerate(filled):
                col = start_col + c_off
                if col >= self.columnCount():
                    break
                # Hedef hücreye yaz; boş kalan A–W hücrelerini na yap
                self.setItem(start_row + r_off, col, QTableWidgetItem(value))
            # Satırın A–W tamamını na ile doldur (yapıştırma kısa geldiyse)
            if start_col == 0:
                for c in range(23):
                    item = self.item(start_row + r_off, c)
                    if item is None or not item.text().strip():
                        self.setItem(
                            start_row + r_off,
                            c,
                            QTableWidgetItem(EMPTY_PLACEHOLDER),
                        )

        self._trim_trailing_empty_rows()
        return len(matrix)

    def _has_any_data(self) -> bool:
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                item = self.item(r, c)
                if item and item.text().strip():
                    return True
        return False

    def _trim_trailing_empty_rows(self) -> None:
        last = self.rowCount() - 1
        while last >= 0:
            empty = True
            for c in range(self.columnCount()):
                item = self.item(last, c)
                if item and item.text().strip():
                    empty = False
                    break
            if empty:
                self.removeRow(last)
                last -= 1
            else:
                break


class SheetsPasteDialog(QDialog):
    """Google Sheets A–W satırlarını Excel benzeri tabloda gösterir."""

    def __init__(
        self,
        parent=None,
        initial_matrix: list[list[str]] | None = None,
        *,
        revise: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle("Google satırlarını yapıştır / düzenle")
        self.resize(1100, 520)
        self._rows: list[SheetsRow] = []
        self._warnings: list[str] = []
        self._matrix: list[list[str]] = []
        self._revise = revise

        layout = QVBoxLayout(self)
        if revise:
            hint = (
                "Revize teklif: hem Revizyonu=1 (ilk teklif) hem güncel "
                "revizyon (2, 3, …) satırlarını birlikte yapıştırın.\n"
                "Eşleme Müşteri Stok Kodu ile yapılır; eski birim fiyat "
                "Revizyonu=1'den, diğer alanlar güncel satırdan alınır.\n"
                "1) Sheets'ten A–W kopyalayıp yapıştırın (Ctrl+V).\n"
                "2) Gerekirse hücreleri düzenleyin.\n"
                "3) Tamam → sonra ana ekranda Excel seçin."
            )
        else:
            hint = (
                "1) Sheets'ten A–W kopyalayıp yapıştırın (Ctrl+V).\n"
                "2) Gerekirse hücreleri düzenleyin.\n"
                "3) Tamam → sonra ana ekranda Excel seçin; sütunlar otomatik dolar."
            )
        layout.addWidget(QLabel(hint))

        toolbar = QHBoxLayout()
        btn_paste = QPushButton("Panodan yapıştır")
        btn_paste.clicked.connect(self._paste_replace)
        btn_clear = QPushButton("Tabloyu temizle")
        btn_clear.clicked.connect(self._clear_table)
        toolbar.addWidget(btn_paste)
        toolbar.addWidget(btn_clear)
        toolbar.addStretch()
        self.count_label = QLabel("0 satır")
        toolbar.addWidget(self.count_label)
        layout.addLayout(toolbar)

        self.table = SheetsTableWidget(0, 23)
        headers = [
            f"{letter}\n{name}"
            for letter, name in zip(COL_LETTER, SHEETS_COLUMNS_A_TO_W)
        ]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.horizontalHeader().setDefaultSectionSize(110)
        self.table.horizontalHeader().setStretchLastSection(False)
        # Önemli sütunları biraz geniş tut
        for col in (3, 4, 10, 11, 20):  # D E K L U
            self.table.setColumnWidth(col, 140)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QTableWidget.ContiguousSelection)
        layout.addWidget(self.table, 1)

        # Dialog düzeyinde Ctrl+V
        QShortcut(QKeySequence.Paste, self, activated=self._paste_replace)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.table.itemChanged.connect(self._update_count)
        if initial_matrix:
            self._load_matrix(initial_matrix)
        self._update_count()

    def _load_matrix(self, matrix: list[list[str]]) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(matrix))
        for r, row in enumerate(matrix):
            filled = fill_row_empty_with_na(row)
            for c, value in enumerate(filled):
                if c >= 23:
                    break
                self.table.setItem(r, c, QTableWidgetItem(value))
        self.table.blockSignals(False)

    def _paste_replace(self) -> None:
        n = self.table.paste_from_clipboard(replace=True)
        self._update_count()
        if n == 0:
            QMessageBox.information(
                self,
                "Yapıştırma",
                "Panoda yapıştırılacak Sheets satırı bulunamadı.",
            )
        else:
            self.count_label.setText(f"{self.table.rowCount()} satır")

    def _clear_table(self) -> None:
        self.table.setRowCount(0)
        self._update_count()

    def _update_count(self) -> None:
        self.count_label.setText(f"{self.table.rowCount()} satır")

    def _matrix_from_table(self) -> list[list[str]]:
        matrix: list[list[str]] = []
        for r in range(self.table.rowCount()):
            row: list[str] = []
            for c in range(23):
                item = self.table.item(r, c)
                row.append(item.text() if item else "")
            if any(cell.strip() and cell.strip().lower() != "na" for cell in row):
                # En az bir gerçek değer varsa satırı al; boşları na yap
                matrix.append(fill_row_empty_with_na(row))
            elif any(cell.strip() for cell in row):
                # Hepsi na veya karışık — yine de satır olarak kabul et
                matrix.append(fill_row_empty_with_na(row))
        return matrix

    def _on_accept(self) -> None:
        # Tablodaki boş hücreleri görünür şekilde na yap
        for r in range(self.table.rowCount()):
            if not any(
                (self.table.item(r, c) and self.table.item(r, c).text().strip())
                for c in range(23)
            ):
                continue
            for c in range(23):
                item = self.table.item(r, c)
                if item is None or not item.text().strip():
                    self.table.setItem(r, c, QTableWidgetItem(EMPTY_PLACEHOLDER))
        try:
            matrix = self._matrix_from_table()
            result = rows_from_table_matrix(matrix)
        except SheetsTsvParseError as exc:
            QMessageBox.warning(self, "Yapıştırma hatası", str(exc))
            return
        self._matrix = matrix
        self._rows = result.rows
        self._warnings = result.warnings
        if result.warnings:
            QMessageBox.information(
                self,
                "Uyarı",
                "Bazı satırlar atlandı:\n" + "\n".join(result.warnings[:10]),
            )
        self.accept()

    def rows(self) -> list[SheetsRow]:
        return list(self._rows)

    def matrix(self) -> list[list[str]]:
        return [list(r) for r in self._matrix]

    def warnings(self) -> list[str]:
        return list(self._warnings)
