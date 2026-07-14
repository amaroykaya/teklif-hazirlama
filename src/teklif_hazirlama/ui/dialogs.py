from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from teklif_hazirlama.core.models import CustomerConfig, HitapKisi
from teklif_hazirlama.infrastructure.storage import slugify_code


class ListItemDialog(QDialog):
    def __init__(self, title: str, label: str, parent=None, value: str = "", allow_delete: bool = False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(420, 140)
        self._allow_delete = allow_delete
        self._deleted = False

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.value = QLineEdit(value)
        form.addRow(label, self.value)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if allow_delete:
            delete_row = QHBoxLayout()
            delete_row.addStretch()
            btn_delete = QPushButton("Sil")
            btn_delete.clicked.connect(self._confirm_delete)
            delete_row.addWidget(btn_delete)
            layout.addLayout(delete_row)

    def _confirm_delete(self) -> None:
        answer = QMessageBox.question(
            self,
            "Sil",
            "Bu kaydı silmek istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self._deleted = True
            self.accept()

    def text(self) -> str:
        return self.value.text().strip()

    def was_deleted(self) -> bool:
        return self._deleted


class CustomerDialog(QDialog):
    def __init__(
        self,
        parent=None,
        customer: CustomerConfig | None = None,
        allow_delete: bool = False,
    ):
        super().__init__(parent)
        self._allow_delete = allow_delete
        self._deleted = False
        self._original_code = customer.code if customer else ""
        self.setWindowTitle("Müşteri Düzenle" if customer else "Müşteri Ekle")
        self.resize(520, 420)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name = QLineEdit(customer.name if customer else "")
        self.unvan = QLineEdit(customer.firma.get("unvan", "") if customer else "")
        self.adres1 = QLineEdit()
        self.adres2 = QLineEdit()
        self.adres3 = QLineEdit()
        self.telefon = QLineEdit(customer.firma.get("telefon", "") if customer else "")
        self.para_birimi = QLineEdit(customer.para_birimi if customer else "USD")
        self.gecerlilik = QSpinBox()
        self.gecerlilik.setRange(1, 365)
        self.gecerlilik.setValue(customer.gecerlilik_gun if customer else 30)
        self.odeme = QTextEdit()
        self.odeme.setFixedHeight(90)
        if customer:
            self.odeme.setPlainText(customer.varsayilan_odeme_sekli.strip())
            lines = customer.firma.get("adres_satirlari", [])
            if len(lines) > 0:
                self.adres1.setText(lines[0])
            if len(lines) > 1:
                self.adres2.setText(lines[1])
            if len(lines) > 2:
                self.adres3.setText(lines[2])

        form.addRow("Firma Adı", self.name)
        form.addRow("Ünvan", self.unvan)
        form.addRow("Adres 1", self.adres1)
        form.addRow("Adres 2", self.adres2)
        form.addRow("Adres 3", self.adres3)
        form.addRow("Telefon", self.telefon)
        form.addRow("Para Birimi", self.para_birimi)
        form.addRow("Geçerlilik (gün)", self.gecerlilik)
        form.addRow("Varsayılan Ödeme Şekli", self.odeme)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addLayout(form)
        layout.addWidget(buttons)

        if self._allow_delete:
            delete_row = QHBoxLayout()
            delete_row.addStretch()
            btn_delete = QPushButton("Sil")
            btn_delete.clicked.connect(self._confirm_delete)
            delete_row.addWidget(btn_delete)
            layout.addLayout(delete_row)

    def _validate_and_accept(self) -> None:
        if not self.name.text().strip():
            QMessageBox.warning(self, "Eksik bilgi", "Firma adı zorunludur.")
            return
        if not self.adres1.text().strip():
            QMessageBox.warning(self, "Eksik bilgi", "En az bir adres satırı zorunludur.")
            return
        self.accept()

    def _confirm_delete(self) -> None:
        answer = QMessageBox.question(
            self,
            "Sil",
            "Bu müşteriyi silmek istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self._deleted = True
            self.accept()

    def was_deleted(self) -> bool:
        return self._deleted

    def customer(self) -> CustomerConfig | None:
        name = self.name.text().strip()
        if not name:
            return None
        adres = [line for line in [self.adres1.text(), self.adres2.text(), self.adres3.text()] if line.strip()]
        code = self._original_code or slugify_code(name)
        return CustomerConfig(
            code=code,
            name=name,
            gecerlilik_gun=self.gecerlilik.value(),
            para_birimi=self.para_birimi.text().strip() or "USD",
            firma={
                "unvan": self.unvan.text().strip() or name,
                "adres_satirlari": adres,
                "telefon": self.telefon.text().strip(),
            },
            varsayilan_odeme_sekli=self.odeme.toPlainText().strip(),
        )


class HitapKisiDialog(QDialog):
    def __init__(
        self,
        musteri_kodu: str,
        musteri_adi: str,
        parent=None,
        contact: HitapKisi | None = None,
        builtin: bool = False,
        allow_delete: bool = False,
    ):
        super().__init__(parent)
        is_edit = contact is not None
        self.setWindowTitle("Hitap Kişisi Düzenle" if is_edit else "Hitap Kişisi Ekle")
        self.resize(420, 200)
        self.musteri_kodu = musteri_kodu
        self._builtin = builtin
        self._allow_delete = allow_delete
        self._deleted = False
        self._original_ad = contact.ad if contact else ""

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.musteri_label = QLineEdit(musteri_adi)
        self.musteri_label.setReadOnly(True)

        self.ad = QLineEdit()
        self.telefon = QLineEdit()

        if contact:
            self.ad.setText(contact.ad)
            self.telefon.setText(contact.telefon)

        if is_edit and builtin:
            self.ad.setReadOnly(True)

        form.addRow("Müşteri", self.musteri_label)
        form.addRow("Hitap Kişisi", self.ad)
        form.addRow("Telefon", self.telefon)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(buttons)

        if is_edit and allow_delete:
            delete_row = QHBoxLayout()
            delete_row.addStretch()
            btn_delete = QPushButton("Sil")
            btn_delete.clicked.connect(self._confirm_delete)
            delete_row.addWidget(btn_delete)
            layout.addLayout(delete_row)

    def _validate_and_accept(self) -> None:
        if not self.ad.text().strip():
            QMessageBox.warning(self, "Eksik bilgi", "Hitap kişisi adı zorunludur.")
            return
        self.accept()

    def _confirm_delete(self) -> None:
        answer = QMessageBox.question(
            self,
            "Sil",
            "Bu hitap kişisini silmek istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self._deleted = True
            self.accept()

    def was_deleted(self) -> bool:
        return self._deleted

    def original_ad(self) -> str:
        return self._original_ad

    def contact(self) -> HitapKisi | None:
        ad = self.ad.text().strip()
        if not ad:
            return None
        return HitapKisi(
            ad=ad,
            musteri_kodu=self.musteri_kodu,
            telefon=self.telefon.text().strip(),
        )
