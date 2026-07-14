from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from teklif_hazirlama import app_window_title
from teklif_hazirlama.application.quote_workflow import QuoteWorkflow
from teklif_hazirlama.core.models import HitapKisi
from teklif_hazirlama.core.sheets_clipboard import generate_teklif_no
from teklif_hazirlama.ui.branding import app_icon, make_logo_label
from teklif_hazirlama.ui.dialogs import CustomerDialog, HitapKisiDialog, ListItemDialog


class IstekWindow(QMainWindow):
    def __init__(self, on_back=None):
        super().__init__()
        self.workflow = QuoteWorkflow()
        self.import_path: str | None = None
        self._hitap_contacts: list[HitapKisi] = []
        self._on_back = on_back
        self.setWindowTitle(app_window_title("Teklif Kaydı"))
        self.setWindowIcon(app_icon())
        self._build_ui()
        self._load_defaults()
        self.adjustSize()
        self.resize(520, self.sizeHint().height())

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
        logo = make_logo_label(max_width=140)
        logo.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addWidget(logo)
        layout.addLayout(top)

        form_box = QGroupBox("Teklif Kaydı")
        form = QFormLayout(form_box)
        form.setContentsMargins(8, 8, 8, 8)
        form.setSpacing(4)

        self.customer_combo = QComboBox()
        self.customer_combo.currentIndexChanged.connect(self._on_customer_changed)
        form.addRow("Müşteri", self._managed_row(self.customer_combo, self._add_customer, self._edit_customer))

        self.hitap_kisi = QComboBox()
        self.hitap_kisi.setEditable(True)
        self.hitap_kisi.currentIndexChanged.connect(self._on_hitap_changed)
        form.addRow("Hitap Kişisi", self._managed_row(self.hitap_kisi, self._add_hitap_kisi, self._edit_hitap_kisi))

        self.teklif_no = QLineEdit()
        form.addRow("Teklif No", self.teklif_no)

        self.musteri_teklif_no = QLineEdit()
        form.addRow("Müşteri Teklif No", self.musteri_teklif_no)

        self.hazirlayan = QComboBox()
        self.hazirlayan.setEditable(True)
        form.addRow("Hazırlayan", self._managed_row(self.hazirlayan, self._add_hazirlayan, self._edit_hazirlayan))

        layout.addWidget(form_box)

        import_box = QGroupBox("Import Excel")
        import_layout = QHBoxLayout(import_box)
        self.import_label = QLabel("Dosya seçilmedi")
        self.import_label.setWordWrap(True)
        btn_import = QPushButton("Excel Seç...")
        btn_import.clicked.connect(self._select_import)
        import_layout.addWidget(self.import_label, 1)
        import_layout.addWidget(btn_import)
        layout.addWidget(import_box)

        btn_copy = QPushButton("İlk Teklif Kaydı Kopyala")
        btn_copy.clicked.connect(self._copy_istek)
        layout.addWidget(btn_copy)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

    def _managed_row(self, combo: QComboBox, on_add, on_edit) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(combo, 1)
        btn_add = QPushButton("Ekle")
        btn_add.clicked.connect(on_add)
        btn_edit = QPushButton("Düzenle")
        btn_edit.clicked.connect(on_edit)
        layout.addWidget(btn_add)
        layout.addWidget(btn_edit)
        return row

    def _load_defaults(self) -> None:
        self._reload_customers()
        self._reload_list_combo(self.hazirlayan, self.workflow.store.get_list("hazirlayanlar"))
        self._on_customer_changed()

    def _on_customer_changed(self) -> None:
        code = self.customer_combo.currentData() or ""
        auto = generate_teklif_no(code)
        if auto:
            self.teklif_no.setText(auto)
        self._reload_hitap_kisileri()

    def _on_hitap_changed(self) -> None:
        contact = self._current_hitap()
        code = self.customer_combo.currentData()
        if code and contact and contact.ad:
            self.workflow.store.set_son_hitap(code, contact.ad)

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
            self._reload_hitap_kisileri()
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

    def _select_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Excel Seç",
            str(Path.home() / "Desktop"),
            "Excel Dosyaları (*.xlsx *.xlsm)",
        )
        if path:
            self.import_path = path
            self.import_label.setText(path)

    def _copy_istek(self) -> None:
        if not self.import_path:
            QMessageBox.warning(self, "Eksik bilgi", "Lütfen import Excel dosyasını seçin.")
            return
        code = self.customer_combo.currentData()
        if not code:
            QMessageBox.warning(self, "Eksik bilgi", "Lütfen müşteri seçin.")
            return
        hitap = self._current_hitap()
        if not hitap or not hitap.ad.strip():
            QMessageBox.warning(self, "Eksik bilgi", "Lütfen hitap kişisi seçin.")
            return
        if not self.teklif_no.text().strip():
            QMessageBox.warning(self, "Eksik bilgi", "Lütfen teklif no girin.")
            return
        if not self.musteri_teklif_no.text().strip():
            QMessageBox.warning(self, "Eksik bilgi", "Lütfen müşteri teklif no girin.")
            return
        try:
            text = self.workflow.build_istek_clipboard_text(
                customer_code=code,
                hazirlayan=self.hazirlayan.currentText(),
                import_excel_path=self.import_path,
                teklif_no=self.teklif_no.text(),
                musteri_teklif_no=self.musteri_teklif_no.text(),
                hitap_kisi=hitap.ad,
            )
            self.workflow.store.add_unique("hazirlayanlar", self.hazirlayan.currentText().strip())
        except Exception as exc:
            QMessageBox.critical(self, "Hata", str(exc))
            return

        QApplication.clipboard().setText(text)
        row_count = text.count("\n") + (1 if text.strip() else 0)
        msg = (
            f"{row_count} satır panoya kopyalandı.\n"
            "Google Sheets'te en alt satırın A hücresine yapıştırın."
        )
        self.status.setText(msg)
        QMessageBox.information(self, "Teklif Kaydı", msg)

    def _go_back(self) -> None:
        if self._on_back:
            self._on_back()
        else:
            self.close()
