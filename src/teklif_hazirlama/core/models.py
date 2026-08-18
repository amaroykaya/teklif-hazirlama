from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class CustomerConfig(BaseModel):
    code: str
    name: str
    gecerlilik_gun: int
    para_birimi: str = "USD"
    teklif_no_oneki: str = ""
    firma: dict
    varsayilan_odeme_sekli: str = ""


class HitapKisi(BaseModel):
    ad: str
    musteri_kodu: str = ""
    adres_satirlari: list[str] = Field(default_factory=list)
    telefon: str = ""


class SheetsRow(BaseModel):
    """Google Sheets A–W yapıştırma satırı (alanlar başlık adına göre)."""

    musteri_stok_kodu: str = ""
    antsis_urun_kodu: str = ""
    teklif_sevk_tarihi: str = ""
    birim_fiyat: str = ""
    kalemdeki_ozel_sartlar: str = ""
    adet: str = ""
    firma: str = ""
    proje_tanimi: str = ""
    raw: dict[str, str] = Field(default_factory=dict)


class OrderExcelRow(BaseModel):
    row_number: int
    siparis_satir_no: str = ""
    stok_kodu: str = ""
    stok_tanimi: str = ""
    teknik_resim: str = ""
    urun_revizyonu: str = ""
    proje_kodu: str = ""
    miktar: int = 0
    birim_fiyat: Decimal = Decimal("0")
    uretim_yeri: str = ""


class OrderPdfHeader(BaseModel):
    siparis_tarihi: str = ""
    siparis_numarasi: str = ""
    buyer: str = ""


class OrderPdfLine(BaseModel):
    ss_no: str
    planlanan_sevk_tarihi: str = ""
    kalite_provizyonlari: str = ""


class OrderRow(BaseModel):
    no: str = ""
    firma: str = ""
    antsis_parca_no: str = ""
    siparis_satir_no: str = ""
    musteri_parca_no: str = ""
    proje: str = ""
    siparis_adedi: str = ""
    siparis_tarihi: str = ""
    siparis_numarasi: str = ""
    planlanan_sevk_tarihi: str = ""
    sevk_tarihi: str = ""
    fatura_durumu: str = ""
    birim_fiyat: str = ""
    toplam_fiyat: str = ""
    sevkiyata_kalan_sure: str = ""
    teknik_resim: str = ""
    urun_revizyonu: str = ""
    kalite_provizyonlari: str = ""
    aciklama: str = ""


class QuoteLine(BaseModel):
    row_number: int
    adet: int
    ants_is_urun_kodu: str
    aciklama: str
    birim_fiyat: Decimal
    toplam_fiyat: Decimal
    teslim_suresi_parcasi: str = ""
    stok_kodu: str = ""
    stok_aciklama: str = ""
    termin_tarihi: date | None = None
    kalite_provizyonlari: str = ""
    teknik_resim_sartname: str = ""
    kalem_revizyon: str = ""
    # Revize form: boşsa birim_fiyat kullanılır
    indirimli_birim_fiyat: Decimal | None = None


class QuoteHeader(BaseModel):
    teklif_no: str
    tarih: date
    hitap_kisi: str
    hitap_adres_satirlari: list[str] = Field(default_factory=list)
    hitap_telefon: str = ""
    hazirlayan: str
    teslimat: str
    teslimat_sekli: str
    odeme_sekli: str
    istek_no: str
    revizyon: str = ""


class QuoteDocument(BaseModel):
    customer: CustomerConfig
    header: QuoteHeader
    lines: list[QuoteLine]
    teslim_tarihi_text: str
    sartlar: list[str] = Field(default_factory=list)
    ozel_sartlar: list[str] = Field(default_factory=list)
    ara_toplam: Decimal = Decimal("0")
    kdv: Decimal = Decimal("0")
    toplam: Decimal = Decimal("0")

    @property
    def urun_kodlari_sartlar(self) -> str:
        codes: list[str] = []
        seen: set[str] = set()
        for line in self.lines:
            code = (line.ants_is_urun_kodu or "").strip()
            if not code or code in seen:
                continue
            seen.add(code)
            codes.append(code)
        return ", ".join(codes)
