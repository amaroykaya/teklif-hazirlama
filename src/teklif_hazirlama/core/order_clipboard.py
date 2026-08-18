from __future__ import annotations

import html

from teklif_hazirlama.core.order_pdf_parser import strip_po_prefix
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
        strip_po_prefix(row.siparis_numarasi),
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


def anten_row_cells(row: OrderRow) -> list[str]:
    """Ana satırdan Anten Sheets A–P (16 kolon)."""
    return [
        "",  # A
        row.firma,  # B ← Ana B
        row.proje,  # C ← Ana F
        "",  # D
        row.siparis_adedi,  # E ← Ana G
        row.siparis_tarihi,  # F ← Ana H
        strip_po_prefix(row.siparis_numarasi),  # G ← Ana I
        row.planlanan_sevk_tarihi,  # H ← Ana J
        "",  # I
        "",  # J
        "",  # K
        "",  # L
        "yok",  # M
        "",  # N
        row.kalite_provizyonlari,  # O ← Ana R
        row.aciklama,  # P ← Ana S
    ]


def elektronik_row_cells(row: OrderRow) -> list[str]:
    """Ana satırdan Elektronik Sheets A–P (16 kolon)."""
    return [
        "",  # A
        row.antsis_parca_no,  # B ← Ana C
        row.firma,  # C ← Ana B
        "",  # D
        "",  # E
        row.siparis_adedi,  # F ← Ana G
        "",  # G
        row.siparis_tarihi,  # H ← Ana H
        strip_po_prefix(row.siparis_numarasi),  # I ← Ana I
        "",  # J
        "",  # K
        "",  # L
        "",  # M
        "",  # N
        "",  # O
        _proje_and_aciklama(row),  # P ← Ana F + S alt alta
    ]


def _proje_and_aciklama(row: OrderRow) -> str:
    proje = (row.proje or "").strip()
    aciklama = (row.aciklama or "").strip()
    return "\n".join(part for part in (proje, aciklama) if part)


def build_order_sheets_tsv(rows: list[OrderRow]) -> str:
    return _rows_to_tsv(row_cells(row) for row in rows)


def build_anten_sheets_tsv(rows: list[OrderRow]) -> str:
    return _rows_to_tsv(anten_row_cells(row) for row in rows)


def build_elektronik_sheets_tsv(rows: list[OrderRow]) -> str:
    return _rows_to_tsv(elektronik_row_cells(row) for row in rows)


def build_order_sheets_html(rows: list[OrderRow]) -> str:
    """Google Sheets'e formatlı yapıştırma için HTML tablo."""
    return _rows_to_html(
        (row_cells(row) for row in rows),
        quality_index=17,
        aciklama_index=18,
    )


def build_anten_sheets_html(rows: list[OrderRow]) -> str:
    return _rows_to_html(
        (anten_row_cells(row) for row in rows),
        quality_index=14,
        aciklama_index=15,
    )


def build_elektronik_sheets_html(rows: list[OrderRow]) -> str:
    return _rows_to_html(
        (elektronik_row_cells(row) for row in rows),
        quality_index=-1,
        aciklama_index=15,
    )


def _rows_to_tsv(cell_rows) -> str:
    lines: list[str] = []
    for cells in cell_rows:
        lines.append("\t".join(_tsv_cell(cell) for cell in cells))
    return "\n".join(lines)


def _rows_to_html(cell_rows, *, quality_index: int, aciklama_index: int) -> str:
    body_rows: list[str] = []
    for cells in cell_rows:
        tds: list[str] = []
        for index, value in enumerate(cells):
            if index == quality_index:
                inner = format_quality_html(value)
            elif index == aciklama_index:
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
