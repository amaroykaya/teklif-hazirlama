from datetime import date
from decimal import Decimal

from teklif_hazirlama.core.models import CustomerConfig, QuoteDocument, QuoteHeader, QuoteLine


def test_urun_kodlari_sartlar_unique_preserve_order():
    customer = CustomerConfig(
        code="roketsan",
        name="Roketsan",
        gecerlilik_gun=30,
        firma={"unvan": "Roketsan", "adres_satirlari": [], "telefon": ""},
    )
    header = QuoteHeader(
        teklif_no="T1",
        tarih=date(2026, 7, 11),
        hitap_kisi="Test",
        hazirlayan="A",
        teslimat="B",
        teslimat_sekli="C",
        odeme_sekli="D",
        istek_no="Q1",
    )
    lines = [
        QuoteLine(row_number=1, adet=1, ants_is_urun_kodu="ANT-A", aciklama="a", birim_fiyat=Decimal("1"), toplam_fiyat=Decimal("1")),
        QuoteLine(row_number=2, adet=1, ants_is_urun_kodu="ANT-B", aciklama="b", birim_fiyat=Decimal("1"), toplam_fiyat=Decimal("1")),
        QuoteLine(row_number=3, adet=1, ants_is_urun_kodu="ANT-A", aciklama="a2", birim_fiyat=Decimal("1"), toplam_fiyat=Decimal("1")),
        QuoteLine(row_number=4, adet=1, ants_is_urun_kodu="ANT-C", aciklama="c", birim_fiyat=Decimal("1"), toplam_fiyat=Decimal("1")),
        QuoteLine(row_number=5, adet=1, ants_is_urun_kodu="ANT-B", aciklama="b2", birim_fiyat=Decimal("1"), toplam_fiyat=Decimal("1")),
    ]
    doc = QuoteDocument(customer=customer, header=header, lines=lines, teslim_tarihi_text="")
    assert doc.urun_kodlari_sartlar == "ANT-A, ANT-B, ANT-C"
