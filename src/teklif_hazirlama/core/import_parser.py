from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from teklif_hazirlama.core.models import QuoteLine
from teklif_hazirlama.core.tedarikci_notu_parser import (
    append_aciklama_eki,
    parse_tedarikci_notu,
)
from teklif_hazirlama.infrastructure.excel_import_reader import (
    FIELD_ALIASES,
    REQUIRED_FIELDS,
    REQUIRED_FIELDS_ISTEK,
    ImportSheetReader,
    normalize_header,
)

_URUN_KODU_RE = re.compile(r"(ANT-[A-Z0-9]+(?:-[A-Z0-9]+)*)", re.IGNORECASE)


class ImportParseError(Exception):
    pass


_TR_MONTHS = {
    "oca": 1,
    "sub": 2,
    "şub": 2,
    "mar": 3,
    "nis": 4,
    "may": 5,
    "haz": 6,
    "tem": 7,
    "agu": 8,
    "ağu": 8,
    "eyl": 9,
    "eki": 10,
    "kas": 11,
    "ara": 12,
}


class ImportParser:
    HEADER_ROW = 2
    DATA_START_ROW = 3

    def __init__(self):
        self.reader = ImportSheetReader()

    def parse(
        self,
        excel_path: str | Path,
        *,
        mode: str = "teklif",
    ) -> tuple[list[QuoteLine], list[str]]:
        path = Path(excel_path)
        required = REQUIRED_FIELDS_ISTEK if mode == "istek" else REQUIRED_FIELDS
        header_row, data_start_row = self._detect_layout(path, mode=mode)
        self._validate_and_resolve_columns(path, required, header_row=header_row)

        lines: list[QuoteLine] = []
        errors: list[str] = []
        candidate_rows = 0

        for row, cells in self.reader.read_rows(
            path,
            header_row=header_row,
            data_start_row=data_start_row,
        ):
            if not self._include_row(cells.get("teklifte_bulun"), mode=mode):
                continue
            candidate_rows += 1
            try:
                if mode == "istek":
                    lines.append(self._parse_row_istek(row, cells))
                else:
                    lines.append(self._parse_row(row, cells))
            except ImportParseError as exc:
                errors.append(f"Satır {row}: {exc}")

        if not lines and candidate_rows == 0:
            if mode == "istek":
                raise ImportParseError(
                    "Import Excel'de işlenecek satır bulunamadı "
                    "(Teklifte Bulun = Y veya boş)."
                )
            raise ImportParseError(
                "Import Excel'de işlenecek satır bulunamadı (Teklifte Bulun = Y)."
            )
        if not lines and errors:
            raise ImportParseError(
                "Satırlar okunamadı:\n" + "\n".join(errors[:8])
            )

        return lines, errors

    def istek_no_from_path(self, excel_path: str | Path) -> str:
        return Path(excel_path).stem

    def _detect_layout(self, path: Path, *, mode: str) -> tuple[int, int]:
        """İstek: yeni Excel (başlık 1). Teklif formu: eski model (başlık 2)."""
        if mode == "teklif":
            return self.HEADER_ROW, self.DATA_START_ROW
        for header_row, data_start in ((1, 2), (2, 3)):
            try:
                headers = self.reader.header_row_values(path, header_row=header_row)
            except Exception:
                continue
            normalized = {normalize_header(h) for h in headers}
            if "stok kodu" in normalized and "miktar" in normalized:
                return header_row, data_start
        return 1, 2

    def _include_row(self, value, *, mode: str) -> bool:
        if value is True:
            return True
        text = str(value or "").strip().upper()
        if text in {"Y", "YES", "EVET", "1"}:
            return True
        # Yeni istek Excel'inde Teklifte Bulun boş gelebiliyor
        if mode == "istek" and text == "":
            return True
        return False

    def _validate_and_resolve_columns(
        self, path: Path, required: tuple[str, ...], *, header_row: int
    ) -> dict[str, int]:
        columns = self.reader.resolve_columns(path, header_row=header_row)
        missing = [field for field in required if field not in columns]
        if missing:
            labels = []
            for field in missing:
                aliases = FIELD_ALIASES.get(field, [field])
                labels.append(aliases[0])
            raise ImportParseError(
                "Import Excel'de eksik sütun(lar): " + ", ".join(labels)
            )
        return columns

    def _cell_text(self, value) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        if isinstance(value, int):
            return str(value)
        return str(value).strip()

    def _parse_row_istek(self, row: int, cells: dict) -> QuoteLine:
        """Teklif isteği: tek Excel; fiyat/tedarikçi notu zorunlu değil."""
        adet = self._to_int(cells.get("miktar"), "Miktar")
        if adet <= 0:
            raise ImportParseError("Miktar pozitif olmalı")

        stok_kodu = self._cell_text(cells.get("stok_kodu"))
        stok_tanimi = self._cell_text(cells.get("stok_tanimi"))
        if not stok_kodu and not stok_tanimi:
            raise ImportParseError("Stok Kodu / Stok Tanımı boş")

        stok_aciklama = f"{stok_tanimi} / {stok_kodu}".strip(" /")
        birim = cells.get("fiyat")
        toplam = cells.get("satir_toplami")
        birim_fiyat = self._to_decimal_optional(birim)
        if toplam is not None and str(toplam).strip() != "":
            toplam_fiyat = self._to_decimal_optional(toplam)
        else:
            toplam_fiyat = birim_fiyat * adet

        parsed = parse_tedarikci_notu(cells.get("tedarikci_notu"))
        aciklama = append_aciklama_eki(stok_aciklama, parsed.aciklama_eki)
        urun_kodu = parsed.urun_kodu or self._extract_urun_kodu(stok_tanimi)

        return QuoteLine(
            row_number=row,
            adet=adet,
            ants_is_urun_kodu=urun_kodu,
            aciklama=aciklama,
            birim_fiyat=birim_fiyat,
            toplam_fiyat=toplam_fiyat,
            teslim_suresi_parcasi=parsed.teslim_suresi_parcasi,
            stok_kodu=stok_kodu,
            stok_aciklama=stok_aciklama,
            termin_tarihi=self._to_date(cells.get("termin_tarihi")),
            kalite_provizyonlari=self._cell_text(cells.get("kalite_provizyonlari")),
            teknik_resim_sartname=self._cell_text(cells.get("teknik_resim_sartname")),
            kalem_revizyon=self._cell_text(cells.get("kalem_revizyon")),
        )

    def _parse_row(self, row: int, cells: dict) -> QuoteLine:
        adet = self._to_int(cells.get("miktar"), "Miktar")
        if adet <= 0:
            raise ImportParseError("Miktar pozitif olmalı")

        stok_kodu = self._cell_text(cells.get("stok_kodu"))
        stok_tanimi = self._cell_text(cells.get("stok_tanimi"))
        stok_aciklama = f"{stok_tanimi} / {stok_kodu}".strip(" /")
        aciklama = stok_aciklama

        birim_fiyat = self._to_decimal(cells.get("fiyat"), "Fiyat")
        toplam_raw = cells.get("satir_toplami")
        if toplam_raw is not None and str(toplam_raw).strip() != "":
            toplam_fiyat = self._to_decimal(toplam_raw, "Satır Toplamı")
            if toplam_fiyat == 0:
                toplam_fiyat = birim_fiyat * adet
        else:
            toplam_fiyat = birim_fiyat * adet

        notu_raw = cells.get("tedarikci_notu")
        notu_text = self._cell_text(notu_raw)
        if notu_text.lower() == "na" or notu_text == "":
            parsed_urun = "na"
            teslim_parcasi = ""
            aciklama = stok_aciklama
        else:
            parsed = parse_tedarikci_notu(notu_raw)
            aciklama = append_aciklama_eki(stok_aciklama, parsed.aciklama_eki)
            if not parsed.urun_kodu:
                raise ImportParseError(
                    "Antsis ürün kodu çıkarılamadı (Tedarikçi Notu)"
                )
            parsed_urun = parsed.urun_kodu
            teslim_parcasi = parsed.teslim_suresi_parcasi

        return QuoteLine(
            row_number=row,
            adet=adet,
            ants_is_urun_kodu=parsed_urun,
            aciklama=aciklama,
            birim_fiyat=birim_fiyat,
            toplam_fiyat=toplam_fiyat,
            teslim_suresi_parcasi=teslim_parcasi,
            stok_kodu=stok_kodu,
            stok_aciklama=stok_aciklama,
            termin_tarihi=self._to_date(cells.get("termin_tarihi")),
        )

    def _extract_urun_kodu(self, text: str) -> str:
        match = _URUN_KODU_RE.search(text or "")
        return match.group(1).upper() if match else ""

    def _to_date(self, value) -> date | None:
        if value is None or str(value).strip() == "":
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(text[:10], fmt).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            pass
        return self._parse_tr_month_date(text)

    def _parse_tr_month_date(self, text: str) -> date | None:
        """Ağu 10, 2026 / Oca 01, 2027"""
        match = re.match(
            r"^([A-Za-zÇĞİÖŞÜçğıöşü]{3})\s+(\d{1,2}),\s*(\d{4})$",
            text.strip(),
        )
        if not match:
            return None
        mon_key = normalize_header(match.group(1))[:3]
        # normalize_header lowercases and strips diacritics → agu, oca, tem
        month = _TR_MONTHS.get(mon_key) or _TR_MONTHS.get(match.group(1).casefold()[:3])
        if not month:
            # try without normalize (ağu → ağu after casefold)
            raw = match.group(1).casefold()[:3]
            month = _TR_MONTHS.get(raw)
        if not month:
            return None
        try:
            return date(int(match.group(3)), month, int(match.group(2)))
        except ValueError:
            return None

    def _to_int(self, value, field: str) -> int:
        if value is None:
            raise ImportParseError(f"{field} boş")
        try:
            return int(float(value))
        except (TypeError, ValueError):
            raise ImportParseError(f"{field} geçersiz: {value!r}")

    def _to_decimal(self, value, field: str) -> Decimal:
        if value is None:
            raise ImportParseError(f"{field} boş")
        if str(value).strip().lower() == "na":
            return Decimal("0")
        try:
            return self._to_decimal_optional(value)
        except (InvalidOperation, ValueError, ImportParseError):
            raise ImportParseError(f"{field} geçersiz: {value!r}")

    def _to_decimal_optional(self, value) -> Decimal:
        if value is None or str(value).strip() == "":
            return Decimal("0")
        if str(value).strip().lower() == "na":
            return Decimal("0")
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        text = str(value).strip()
        text = re.sub(r"[A-Za-z$€₺]", "", text).replace(" ", "")
        if text.count(",") == 1 and text.count(".") > 1:
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", ".")
        if text in {"", ".", "-", "-."}:
            return Decimal("0")
        try:
            return Decimal(text)
        except (InvalidOperation, ValueError):
            raise ImportParseError(f"Geçersiz tutar: {value!r}")
