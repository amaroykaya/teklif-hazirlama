from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from teklif_hazirlama.core.models import SheetsRow
from teklif_hazirlama.infrastructure.excel_import_reader import normalize_header

# A → W sabit Sheets başlıkları (isterler.md §16 / PRD)
SHEETS_COLUMNS_A_TO_W: tuple[str, ...] = (
    "ilk rev Zamanı",  # A
    "No",  # B
    "Firma",  # C
    "Antsis Ürün Kodu",  # D
    "Müşteri Stok Kodu",  # E
    "Proje Tanımı",  # F
    "Adet",  # G
    "Teklif Tarihi",  # H
    "Antsis Teklif No",  # I
    "Müşteri Teklif Numarası",  # J
    "Teklif Sevk Tarihi",  # K
    "Birim Fiyat",  # L
    "Toplam Fiyat",  # M
    "Revizyonu",  # N
    "Teklifi Hazırlayan",  # O
    "Beklenen Bilgiler",  # P
    "Sipariş alındı mı",  # Q
    "Kalite Provizyonu",  # R
    "Teknik şartname",  # S
    "Kalem Revizyon",  # T
    "Kalemdeki Özel Şartlar",  # U
    "Açıklama",  # V
    "Satınalma Sorumlusu",  # W
)

COL_LETTER = tuple(chr(ord("A") + i) for i in range(23))

# Normalize başlık → SheetsRow alanı
SHEETS_FIELD_ALIASES: dict[str, list[str]] = {
    "musteri_stok_kodu": ["musteri stok kodu"],
    "antsis_urun_kodu": ["antsis urun kodu"],
    "teklif_sevk_tarihi": ["teklif sevk tarihi"],
    "birim_fiyat": ["birim fiyat"],
    "kalemdeki_ozel_sartlar": ["kalemdeki ozel sartlar"],
    "adet": ["adet"],
    "firma": ["firma"],
    "proje_tanimi": ["proje tanimi"],
}

# Sabit A–W indeksinden alan
FIELD_BY_INDEX: dict[str, int] = {
    "firma": 2,  # C
    "antsis_urun_kodu": 3,  # D
    "musteri_stok_kodu": 4,  # E
    "proje_tanimi": 5,  # F
    "adet": 6,  # G
    "teklif_sevk_tarihi": 10,  # K
    "birim_fiyat": 11,  # L
    "kalemdeki_ozel_sartlar": 20,  # U
}

REQUIRED_SHEETS_FIELDS = (
    "musteri_stok_kodu",
    "antsis_urun_kodu",
    "teklif_sevk_tarihi",
    "birim_fiyat",
)


class SheetsTsvParseError(Exception):
    pass


@dataclass
class SheetsTsvParseResult:
    rows: list[SheetsRow]
    warnings: list[str]


def parse_clipboard_tsv(text: str) -> list[list[str]]:
    """Panodaki TSV'yi hücre matrisi olarak döner; tamamen boş satırları atar."""
    raw = text or ""
    if not raw.strip():
        return []
    reader = csv.reader(io.StringIO(raw), delimiter="\t", quotechar='"')
    matrix: list[list[str]] = []
    for row in reader:
        cells = [("" if c is None else str(c)) for c in row]
        if not any(c.strip() for c in cells):
            continue
        # A–W'ye pad / truncate
        if len(cells) < 23:
            cells = cells + [""] * (23 - len(cells))
        elif len(cells) > 23:
            cells = cells[:23]
        matrix.append(cells)
    return matrix


def first_row_is_header(row: list[str]) -> bool:
    """İlk satır bilinen A–W başlıklarına uyuyorsa True."""
    if not row:
        return False
    known = {normalize_header(h) for h in SHEETS_COLUMNS_A_TO_W}
    hits = 0
    for cell in row[:23]:
        key = normalize_header(cell)
        if key and key in known:
            hits += 1
    # En az 4 bilinen başlık (E, D, K, L vb.) yeterli
    return hits >= 4


def parse_sheets_tsv(text: str) -> SheetsTsvParseResult:
    """Sheets A–W panodan yapıştırılan TSV'yi satır listesine çevirir."""
    matrix = parse_clipboard_tsv(text)
    if not matrix:
        raise SheetsTsvParseError("Yapıştırılan metin boş.")

    if first_row_is_header(matrix[0]):
        if len(matrix) < 2:
            raise SheetsTsvParseError("Başlık satırından sonra veri satırı yok.")
        # Başlık adına göre eşle (kaymış sütun koruması)
        return _rows_from_named_header(matrix[0], matrix[1:])

    # Başlıksız: A–W konumuna göre
    return _rows_from_aw_matrix(matrix)


def rows_from_table_matrix(matrix: list[list[str]]) -> SheetsTsvParseResult:
    """Tablo widget'ındaki A–W hücrelerinden SheetsRow üretir (başlık yok)."""
    cleaned = [
        row
        for row in matrix
        if any(str(c).strip() for c in row)
    ]
    if not cleaned:
        raise SheetsTsvParseError("Tabloda geçerli veri satırı yok.")
    return _rows_from_aw_matrix(cleaned)


EMPTY_PLACEHOLDER = "na"


def cell_or_na(value: str | None) -> str:
    text = "" if value is None else str(value).strip()
    return text if text else EMPTY_PLACEHOLDER


def fill_row_empty_with_na(cells: list[str], width: int = 23) -> list[str]:
    """Eksik/boş hücreleri 'na' yapar; satırı A–W genişliğine tamamlar."""
    padded = list(cells[:width]) + [""] * max(0, width - len(cells))
    return [cell_or_na(c) for c in padded[:width]]


def _cell(row: list[str], idx: int) -> str:
    if idx < 0 or idx >= len(row):
        return EMPTY_PLACEHOLDER
    return cell_or_na(row[idx])


def _sheets_row_from_aw(cells: list[str]) -> SheetsRow | None:
    # Tamamen boş satır (henüz na doldurulmamış) atlanır
    if not any(str(c).strip() for c in cells):
        return None
    filled = fill_row_empty_with_na(cells)
    raw = {
        normalize_header(SHEETS_COLUMNS_A_TO_W[i]): filled[i]
        for i in range(len(SHEETS_COLUMNS_A_TO_W))
    }
    return SheetsRow(
        musteri_stok_kodu=filled[FIELD_BY_INDEX["musteri_stok_kodu"]],
        antsis_urun_kodu=filled[FIELD_BY_INDEX["antsis_urun_kodu"]],
        teklif_sevk_tarihi=filled[FIELD_BY_INDEX["teklif_sevk_tarihi"]],
        birim_fiyat=filled[FIELD_BY_INDEX["birim_fiyat"]],
        kalemdeki_ozel_sartlar=filled[
            FIELD_BY_INDEX["kalemdeki_ozel_sartlar"]
        ],
        adet=filled[FIELD_BY_INDEX["adet"]],
        firma=filled[FIELD_BY_INDEX["firma"]],
        proje_tanimi=filled[FIELD_BY_INDEX["proje_tanimi"]],
        raw=raw,
    )


def _rows_from_aw_matrix(matrix: list[list[str]]) -> SheetsTsvParseResult:
    rows: list[SheetsRow] = []
    warnings: list[str] = []
    for idx, cells in enumerate(matrix, start=1):
        row = _sheets_row_from_aw(cells)
        if row is None:
            continue
        rows.append(row)
    if not rows:
        raise SheetsTsvParseError(
            "Tabloda veri satırı yok. Sheets'ten A–W kopyalayıp "
            "'Panodan yapıştır' ile ekleyin."
        )
    return SheetsTsvParseResult(rows=rows, warnings=warnings)


def _rows_from_named_header(
    header: list[str], data: list[list[str]]
) -> SheetsTsvParseResult:
    col_map = _resolve_columns(header)
    missing = [f for f in REQUIRED_SHEETS_FIELDS if f not in col_map]
    if missing:
        labels = {
            "musteri_stok_kodu": "Müşteri Stok Kodu",
            "antsis_urun_kodu": "Antsis Ürün Kodu",
            "teklif_sevk_tarihi": "Teklif Sevk Tarihi",
            "birim_fiyat": "Birim Fiyat",
        }
        names = ", ".join(labels.get(f, f) for f in missing)
        raise SheetsTsvParseError(
            f"Sheets başlık satırında eksik sütun(lar): {names}"
        )

    rows: list[SheetsRow] = []
    warnings: list[str] = []
    for idx, cells in enumerate(data, start=2):
        values = _row_values(cells, col_map, header)
        # En az bir gerçek (boş olmayan) değer yoksa satır atlanır
        has_content = any(
            str(v).strip()
            for v in values.values()
            if isinstance(v, str)
        )
        if not has_content:
            continue
        # Boş alanlar → na
        def g(key: str) -> str:
            return cell_or_na(values.get(key, ""))

        rows.append(
            SheetsRow(
                musteri_stok_kodu=g("musteri_stok_kodu"),
                antsis_urun_kodu=g("antsis_urun_kodu"),
                teklif_sevk_tarihi=g("teklif_sevk_tarihi"),
                birim_fiyat=g("birim_fiyat"),
                kalemdeki_ozel_sartlar=g("kalemdeki_ozel_sartlar"),
                adet=g("adet"),
                firma=g("firma"),
                proje_tanimi=g("proje_tanimi"),
                raw={k: cell_or_na(v) for k, v in values.items()},
            )
        )

    if not rows:
        raise SheetsTsvParseError(
            "Tabloda veri satırı yok. Sheets'ten A–W kopyalayıp "
            "'Panodan yapıştır' ile ekleyin."
        )
    return SheetsTsvParseResult(rows=rows, warnings=warnings)


def _resolve_columns(header: list[str]) -> dict[str, int]:
    header_to_index: dict[str, int] = {}
    for idx, value in enumerate(header):
        key = normalize_header(value)
        if key and key not in header_to_index:
            header_to_index[key] = idx

    resolved: dict[str, int] = {}
    for field, aliases in SHEETS_FIELD_ALIASES.items():
        for alias in aliases:
            if alias in header_to_index:
                resolved[field] = header_to_index[alias]
                break
    return resolved


def _row_values(
    cells: list[str], col_map: dict[str, int], header: list[str]
) -> dict[str, str]:
    values: dict[str, str] = {}
    for field, idx in col_map.items():
        raw = cells[idx] if idx < len(cells) else ""
        values[field] = "" if raw is None else str(raw).strip()
    for idx, name in enumerate(header):
        key = normalize_header(name)
        if not key:
            continue
        raw = cells[idx] if idx < len(cells) else ""
        values.setdefault(key, "" if raw is None else str(raw).strip())
    return values
