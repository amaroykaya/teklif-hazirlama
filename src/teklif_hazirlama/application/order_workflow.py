from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from teklif_hazirlama.core.models import OrderRow
from teklif_hazirlama.core.order_clipboard import (
    build_order_sheets_html,
    build_order_sheets_tsv,
)
from teklif_hazirlama.core.order_excel_parser import (
    OrderExcelParser,
    build_proje_text,
    extract_antsis_parca_no,
    normalize_uretim_yeri,
    pad_musteri_parca_no,
    siparis_satir_no_to_ss,
)
from teklif_hazirlama.core.order_pdf_parser import OrderPdfParser


class OrderWorkflow:
    def __init__(self) -> None:
        self.excel_parser = OrderExcelParser()
        self.pdf_parser = OrderPdfParser()

    def build_rows(
        self,
        *,
        excel_path: str | Path,
        pdf_path: str | Path | None = None,
        firma: str = "Roketsan",
    ) -> list[OrderRow]:
        excel_rows = self.excel_parser.parse(excel_path)
        pdf_header = None
        pdf_lines: dict[str, object] = {}
        if pdf_path:
            pdf_header, pdf_lines = self.pdf_parser.parse(pdf_path)

        rows: list[OrderRow] = []
        for source in excel_rows:
            ss_no = siparis_satir_no_to_ss(source.siparis_satir_no)
            pdf_line = pdf_lines.get(ss_no)
            kalite = getattr(pdf_line, "kalite_provizyonlari", "")
            buyer = getattr(pdf_header, "buyer", "") if pdf_header else ""
            uretim_yeri = normalize_uretim_yeri(source.uretim_yeri)
            aciklama = build_aciklama_text(
                buyer=buyer,
                kalite_provizyonlari=kalite,
                sevk_yeri=uretim_yeri,
            )
            rows.append(
                OrderRow(
                    no="",
                    firma=(firma or "").strip() or "Roketsan",
                    antsis_parca_no=extract_antsis_parca_no(source.stok_tanimi),
                    siparis_satir_no=source.siparis_satir_no,
                    musteri_parca_no=pad_musteri_parca_no(source.stok_kodu),
                    proje=build_proje_text(source),
                    siparis_adedi=str(source.miktar),
                    siparis_tarihi=getattr(pdf_header, "siparis_tarihi", "") if pdf_header else "",
                    siparis_numarasi=getattr(pdf_header, "siparis_numarasi", "") if pdf_header else "",
                    planlanan_sevk_tarihi=getattr(pdf_line, "planlanan_sevk_tarihi", ""),
                    sevk_tarihi="",
                    fatura_durumu="",
                    birim_fiyat=_format_decimal(source.birim_fiyat),
                    toplam_fiyat=_format_decimal(source.birim_fiyat * source.miktar),
                    sevkiyata_kalan_sure="",
                    teknik_resim=source.teknik_resim,
                    urun_revizyonu=source.urun_revizyonu,
                    kalite_provizyonlari=kalite,
                    aciklama=aciklama,
                )
            )
        return rows

    def build_clipboard_text(
        self,
        *,
        excel_path: str | Path,
        pdf_path: str | Path | None = None,
        firma: str = "Roketsan",
    ) -> tuple[str, list[OrderRow]]:
        rows = self.build_rows(excel_path=excel_path, pdf_path=pdf_path, firma=firma)
        return build_order_sheets_tsv(rows), rows

    def build_clipboard_text_from_rows(self, rows: list[OrderRow]) -> str:
        return build_order_sheets_tsv(rows)

    def build_clipboard_html_from_rows(self, rows: list[OrderRow]) -> str:
        return build_order_sheets_html(rows)


def build_aciklama_text(
    *,
    buyer: str = "",
    kalite_provizyonlari: str = "",
    sevk_yeri: str = "",
) -> str:
    return "\n".join(
        [
            f"Sorumlu: {buyer.strip()}",
            f"Kalite Provizyonları: {kalite_provizyonlari.strip()}",
            f"Sevk yeri : {sevk_yeri.strip()}",
        ]
    )


def _format_decimal(value: Decimal | int) -> str:
    amount = Decimal(value).quantize(Decimal("0.01"))
    text = f"{amount:.2f}"
    if text.endswith(".00"):
        return text[:-3]
    return text.replace(".", ",")
