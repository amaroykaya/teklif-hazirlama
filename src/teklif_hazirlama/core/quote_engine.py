from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from teklif_hazirlama.core.models import CustomerConfig, QuoteDocument, QuoteHeader, QuoteLine
from teklif_hazirlama.core.tedarikci_notu_parser import build_teslim_tarihi_text


KDV_ORANI = Decimal("0.20")


class QuoteEngine:
    def build_document(
        self,
        customer: CustomerConfig,
        header: QuoteHeader,
        lines: list[QuoteLine],
        ozel_sartlar: list[str] | None = None,
        sartlar: list[str] | None = None,
    ) -> QuoteDocument:
        if not lines:
            raise ValueError("En az bir teklif satırı gerekli")

        ara_toplam = sum((line.toplam_fiyat for line in lines), Decimal("0"))
        kdv = (ara_toplam * KDV_ORANI).quantize(Decimal("0.01"))
        toplam = ara_toplam + kdv

        teslim_parcalar = [line.teslim_suresi_parcasi for line in lines]
        teslim_tarihi_text = build_teslim_tarihi_text(teslim_parcalar)

        return QuoteDocument(
            customer=customer,
            header=header,
            lines=lines,
            teslim_tarihi_text=teslim_tarihi_text,
            sartlar=sartlar if sartlar is not None else [],
            ozel_sartlar=ozel_sartlar or [],
            ara_toplam=ara_toplam,
            kdv=kdv,
            toplam=toplam,
        )

    def gecerlilik_tarihi(self, customer: CustomerConfig, tarih):
        return tarih + timedelta(days=customer.gecerlilik_gun)
