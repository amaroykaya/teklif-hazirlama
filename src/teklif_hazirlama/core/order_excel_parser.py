from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

from teklif_hazirlama.core.import_parser import ImportParseError, ImportParser
from teklif_hazirlama.core.models import OrderExcelRow
from teklif_hazirlama.infrastructure.excel_import_reader import ImportSheetReader

ORDER_FIELD_ALIASES: dict[str, list[str]] = {
    "stok_kodu": ["stok kodu"],
    "stok_tanimi": ["stok tanimi"],
    "satir_no": ["satir no"],
    "miktar": ["miktar"],
    "birim_fiyat": ["birim fiyat", "fiyat"],
    "teknik_resim": ["teknik resim"],
    "urun_revizyonu": ["urun revizyonu"],
    "proje_kodu": ["proje kodu"],
    "uretim_yeri": ["uretim yeri"],
}

ORDER_REQUIRED_FIELDS = (
    "stok_kodu",
    "stok_tanimi",
    "satir_no",
    "miktar",
)

# ANT-xxxx, ANT_1029, ANT5307 — stok tanımından Antsis parça no
_ANT_CODE_RE = re.compile(
    r"\b(ANT(?:[-_][A-Z0-9]+)+|ANT[0-9][A-Z0-9_-]*)\b",
    re.IGNORECASE,
)
_SS_PREFIX_RE = re.compile(r"^\s*(\d+)\s*-\s*\d+\s*$")
_URETIM_YERI_PREFIX_RE = re.compile(r"^\s*\d+\s*-\s*")
_ROKETSAN_PREFIX_RE = re.compile(r"^\s*roketsan\s+", re.IGNORECASE)


class OrderExcelParser:
    def __init__(self) -> None:
        self.reader = ImportSheetReader()
        self.import_parser = ImportParser()

    def parse(self, excel_path: str | Path) -> list[OrderExcelRow]:
        path = Path(excel_path)
        header_row, data_start_row = self._detect_layout(path)
        columns = self.reader.resolve_columns(
            path,
            header_row=header_row,
            aliases=ORDER_FIELD_ALIASES,
        )
        missing = [field for field in ORDER_REQUIRED_FIELDS if field not in columns]
        if missing:
            raise ImportParseError(
                "Sipariş Excel'de eksik sütun(lar): "
                + ", ".join(ORDER_FIELD_ALIASES[field][0] for field in missing)
            )

        rows: list[OrderExcelRow] = []
        for row_number, cells in self.reader.read_rows(
            path,
            header_row=header_row,
            data_start_row=data_start_row,
            aliases=ORDER_FIELD_ALIASES,
        ):
            siparis_satir_no = self._cell_text(cells.get("satir_no"))
            stok_kodu = self._cell_text(cells.get("stok_kodu"))
            stok_tanimi = self._cell_text(cells.get("stok_tanimi"))
            if not siparis_satir_no and not stok_kodu and not stok_tanimi:
                continue
            miktar = self._to_int(cells.get("miktar"))
            if miktar <= 0:
                continue
            rows.append(
                OrderExcelRow(
                    row_number=row_number,
                    siparis_satir_no=siparis_satir_no,
                    stok_kodu=stok_kodu,
                    stok_tanimi=stok_tanimi,
                    teknik_resim=self._cell_text(cells.get("teknik_resim")),
                    urun_revizyonu=self._cell_text(cells.get("urun_revizyonu")),
                    proje_kodu=self._cell_text(cells.get("proje_kodu")),
                    miktar=miktar,
                    birim_fiyat=self._to_decimal(cells.get("birim_fiyat")),
                    uretim_yeri=self._cell_text(cells.get("uretim_yeri")),
                )
            )
        if not rows:
            raise ImportParseError("Sipariş Excel'de işlenecek satır bulunamadı.")
        return rows

    def _detect_layout(self, path: Path) -> tuple[int, int]:
        for header_row, data_start in ((1, 2), (2, 3)):
            try:
                headers = self.reader.header_row_values(path, header_row=header_row)
            except Exception:
                continue
            normalized = {self.reader_header(h) for h in headers}
            if "stok kodu" in normalized and "satir no" in normalized:
                return header_row, data_start
        return 1, 2

    @staticmethod
    def reader_header(value) -> str:
        return " ".join(str(value or "").strip().lower().replace("ı", "i").split())

    @staticmethod
    def _cell_text(value) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip()

    @staticmethod
    def _to_int(value) -> int:
        if value is None or str(value).strip() == "":
            return 0
        return int(float(value))

    def _to_decimal(self, value) -> Decimal:
        if value is None or str(value).strip() == "":
            return Decimal("0")
        return self.import_parser._to_decimal_optional(value)


def extract_antsis_parca_no(stok_tanimi: str) -> str:
    match = _ANT_CODE_RE.search(stok_tanimi or "")
    return match.group(1).upper() if match else ""


def pad_musteri_parca_no(stok_kodu: str) -> str:
    text = (stok_kodu or "").strip()
    if not text:
        return ""
    return text.zfill(8) if text.isdigit() else text


def siparis_satir_no_to_ss(satir_no: str) -> str:
    text = (satir_no or "").strip()
    match = _SS_PREFIX_RE.match(text)
    if match:
        return f"SS{match.group(1)}"
    return text.upper().replace(" ", "")


def normalize_uretim_yeri(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    text = _URETIM_YERI_PREFIX_RE.sub("", text)
    text = _ROKETSAN_PREFIX_RE.sub("", text)
    return text.strip(" -")


def build_proje_text(row: OrderExcelRow) -> str:
    proje_kodu = row.proje_kodu.strip()
    if proje_kodu:
        proje_kodu = f"Proje kodu : {proje_kodu.replace(' - ', '-').replace('- ', '-').replace(' -', '-')}"
    parts = [
        row.stok_tanimi.strip(),
        row.teknik_resim.strip(),
        row.urun_revizyonu.strip(),
        proje_kodu,
        siparis_satir_no_to_ss(row.siparis_satir_no),
    ]
    return " / ".join(part for part in parts if part)
