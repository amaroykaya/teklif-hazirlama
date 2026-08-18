from __future__ import annotations

import html

from teklif_hazirlama.core.models import OrderRow
from teklif_hazirlama.core.quality_highlight import (
    format_aciklama_html,
    format_quality_html,
)

ORDER_SHEETS_HEADERS = [
    "No",
    "Firma",
    "Antsis Parça No",
    "Sipariş Satır No",
    "Müşteri Parça No",
    "Proje",
    "Sipariş Adedi",
    "Sipariş Tarihi",
    "sipariş numarası",
    "Planlanan Sevk Tarihi",
    "Sevk Tarihi",
    "Fatura Durumu",
    "Birim Fiyat",
    "Toplam Fiyat",
    "Sevkiyata Kalan Süre",
    "Teknik resim",
    "Ürün Revizyonu",
    "Kalite Provizyonları",
    "Açıklama",
]


def row_cells(row: OrderRow) -> list[str]:
    return [
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


def build_order_sheets_tsv(rows: list[OrderRow]) -> str:
    lines: list[str] = []
    for row in rows:
        lines.append("\t".join(_tsv_cell(cell) for cell in row_cells(row)))
    return "\n".join(lines)


def build_order_sheets_html(rows: list[OrderRow]) -> str:
    """Google Sheets'e formatlı yapıştırma için HTML tablo."""
    body_rows: list[str] = []
    for row in rows:
        cells = row_cells(row)
        tds: list[str] = []
        for index, value in enumerate(cells):
            if index == 17:  # Kalite Provizyonları
                inner = format_quality_html(value)
            elif index == 18:  # Açıklama
                inner = format_aciklama_html(value)
            else:
                inner = html.escape(value).replace("\n", "<br>")
            tds.append(f"<td>{inner}</td>")
        body_rows.append("<tr>" + "".join(tds) + "</tr>")
    return (
        '<html><body><table border="0" cellspacing="0" cellpadding="0">'
        + "".join(body_rows)
        + "</table></body></html>"
    )


def _tsv_cell(value: str) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    if any(ch in text for ch in ("\n", "\t", '"')):
        return f'"{text.replace(chr(34), chr(34) * 2)}"'
    return text
