"""Sheets satırlarını UI ürün satırlarına çevirme ve Excel ile birleştirme."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from teklif_hazirlama.core.models import QuoteLine, SheetsRow
from teklif_hazirlama.core.sevk_tarihi_parser import (
    format_t0_segments,
    parse_sevk_tarihi,
)
from teklif_hazirlama.core.tedarikci_notu_parser import (
    append_aciklama_eki,
    build_teslim_tarihi_text,
)
from teklif_hazirlama.infrastructure.excel_import_reader import normalize_header

NA = "na"


def _is_na(value: str | None) -> bool:
    return not (value or "").strip() or (value or "").strip().lower() == NA


def _parse_price(value: str | None) -> Decimal:
    if _is_na(value):
        return Decimal("0")
    text = re.sub(r"[A-Za-z$€₺]", "", (value or "").strip()).replace(" ", "")
    if "." in text and "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _parse_adet(value: str | None) -> int:
    if _is_na(value):
        return 0
    text = (value or "").strip().replace(" ", "").replace(",", ".")
    try:
        return int(float(text))
    except ValueError:
        return 0


def _raw(sheet: SheetsRow, *keys: str) -> str:
    for key in keys:
        norm = normalize_header(key)
        for rk, rv in (sheet.raw or {}).items():
            if normalize_header(rk) == norm:
                return "" if _is_na(str(rv)) else str(rv).strip()
        # doğrudan normalize key
        val = (sheet.raw or {}).get(norm)
        if val is not None and not _is_na(str(val)):
            return str(val).strip()
    return ""


def _teslim_parcasi(sheet: SheetsRow) -> str:
    code = (sheet.antsis_urun_kodu or "").strip()
    if _is_na(code):
        code = ""
    sevk = parse_sevk_tarihi(sheet.teklif_sevk_tarihi)
    if not sevk.entries:
        return ""
    segments = format_t0_segments(sevk.entries)
    if code:
        return f"{code} - {segments}"
    return segments


def sheets_row_to_quote_line(sheet: SheetsRow, row_number: int) -> QuoteLine:
    adet = _parse_adet(sheet.adet)
    birim = _parse_price(sheet.birim_fiyat)
    toplam_raw = _raw(sheet, "Toplam Fiyat", "toplam fiyat")
    toplam = _parse_price(toplam_raw) if toplam_raw else (
        (birim * Decimal(adet)).quantize(Decimal("0.01")) if adet else Decimal("0")
    )

    stok_kodu = "" if _is_na(sheet.musteri_stok_kodu) else sheet.musteri_stok_kodu.strip()
    # Açıklama = F Proje Tanımı; varsa alt satırda ( U Kalemdeki özel şartlar )
    proje = "" if _is_na(sheet.proje_tanimi) else sheet.proje_tanimi.strip()
    ozel = sheet.kalemdeki_ozel_sartlar
    eki = "" if _is_na(ozel) else ozel.strip()
    aciklama = append_aciklama_eki(proje, eki) if proje or eki else ""

    code = "" if _is_na(sheet.antsis_urun_kodu) else sheet.antsis_urun_kodu.strip()

    return QuoteLine(
        row_number=row_number,
        adet=adet,
        ants_is_urun_kodu=code,
        aciklama=aciklama,
        birim_fiyat=birim,
        toplam_fiyat=toplam,
        teslim_suresi_parcasi=_teslim_parcasi(sheet),
        stok_kodu=stok_kodu,
        stok_aciklama=proje,
        kalite_provizyonlari=_raw(sheet, "Kalite Provizyonu", "kalite provizyonu"),
        teknik_resim_sartname=_raw(sheet, "Teknik şartname", "teknik sartname"),
        kalem_revizyon=_raw(sheet, "Kalem Revizyon", "kalem revizyon"),
    )


@dataclass
class SheetsApplyResult:
    quote_lines: list[QuoteLine]
    teslim_tarihi_text: str = ""
    teklif_no: str = ""
    istek_no: str = ""
    warnings: list[str] = field(default_factory=list)
    # Excel zenginleştirme için (revizede yalnızca güncel satırlar)
    enrich_sheets_rows: list[SheetsRow] = field(default_factory=list)
    # Form "Revizyon" alanı için (Sheets N'den; 2→1, 3→2 …)
    form_revizyon: str = ""


def _revision_number(sheet: SheetsRow) -> int | None:
    text = _raw(sheet, "Revizyonu", "revizyonu")
    if not text:
        return None
    try:
        return int(float(text.replace(",", ".").replace(" ", "")))
    except ValueError:
        return None


def _meta_from_sheets(sheets_rows: list[SheetsRow]) -> tuple[str, str]:
    teklif_no = ""
    istek_no = ""
    if sheets_rows:
        teklif_no = _raw(
            sheets_rows[0],
            "Antsis Teklif No",
            "antsis teklif no",
        )
        istek_no = _raw(
            sheets_rows[0],
            "Müşteri Teklif Numarası",
            "musteri teklif numarasi",
        )
    return teklif_no, istek_no


def apply_sheets_rows(
    sheets_rows: list[SheetsRow],
    *,
    revise: bool = False,
) -> SheetsApplyResult:
    """Sheets → UI ürün satırları (master kaynak). Özel Şartlar paneli doldurulmaz."""
    if revise:
        return _apply_sheets_rows_revise(sheets_rows)

    lines = [
        sheets_row_to_quote_line(row, i + 1)
        for i, row in enumerate(sheets_rows)
    ]
    teslim = build_teslim_tarihi_text(
        [line.teslim_suresi_parcasi for line in lines]
    )
    teklif_no, istek_no = _meta_from_sheets(sheets_rows)

    warnings: list[str] = []
    if not lines:
        warnings.append("Sheets'te ürün satırı yok.")
    return SheetsApplyResult(
        quote_lines=lines,
        teslim_tarihi_text=teslim,
        teklif_no=teklif_no,
        istek_no=istek_no,
        warnings=warnings,
        enrich_sheets_rows=list(sheets_rows),
    )


def _apply_sheets_rows_revise(sheets_rows: list[SheetsRow]) -> SheetsApplyResult:
    """
    Revize: R1 + güncel satırlar birlikte yapıştırılır.
    Forma yalnızca güncel (Revizyonu ≠ 1) satırlar gelir.
    Eski birim fiyat: Müşteri Stok Kodu + aynı kod içindeki sıra (1., 2., …).
    R1'de fazla satır varsa (ör. 5 vs 3) kullanılmaz; güncelde fazla /
    R1'siz satırda birim fiyat uyarısı verilir.
    """
    warnings: list[str] = []
    r1_queues: dict[str, list[SheetsRow]] = {}
    current_all: list[tuple[int, SheetsRow]] = []

    for sheet in sheets_rows:
        stok = "" if _is_na(sheet.musteri_stok_kodu) else sheet.musteri_stok_kodu.strip()
        key = _norm_code_loose(stok)
        rev = _revision_number(sheet)
        if rev == 1:
            if not key:
                warnings.append(
                    "Revize: Revizyonu=1 satırında Müşteri Stok Kodu boş; atlandı."
                )
                continue
            r1_queues.setdefault(key, []).append(sheet)
            continue
        if rev is not None and rev > 1:
            if not key:
                warnings.append(
                    "Revize: Güncel satırda Müşteri Stok Kodu boş; atlandı."
                )
                continue
            current_all.append((rev, sheet))
            continue
        warnings.append(
            f"Stok {sheet.musteri_stok_kodu or '—'}: Revizyonu okunamadı; "
            "güncel satır sayılmadı."
        )

    if not current_all:
        return SheetsApplyResult(
            quote_lines=[],
            warnings=[
                "Revize Sheets'ten ürün satırı üretilemedi. "
                "Revizyonu=1 ve güncel (2/3/…) satırlarını birlikte yapıştırın."
            ]
            + warnings,
            enrich_sheets_rows=[],
        )

    max_current_rev = max(rev for rev, _ in current_all)
    currents = [sheet for rev, sheet in current_all if rev == max_current_rev]
    skipped_lower = len(current_all) - len(currents)
    if skipped_lower:
        warnings.append(
            f"{skipped_lower} satır daha düşük revizyon numarasıyla atlandı; "
            f"güncel olarak Revizyonu={max_current_rev} kullanıldı."
        )

    # Aynı stok tekrarları: sırayla eşlenecek uyarısı
    stok_counts: dict[str, int] = {}
    for sheet in currents:
        key = _norm_code_loose(sheet.musteri_stok_kodu)
        stok_counts[key] = stok_counts.get(key, 0) + 1
    dupes = [k for k, n in stok_counts.items() if n > 1]
    if dupes:
        warnings.append(
            "Aynı Müşteri Stok Kodu birden fazla satırda var; "
            "eski birim fiyat stok kodu + sırayla eşlendi "
            "(gerekirse panodan düzeltin)."
        )

    lines: list[QuoteLine] = []
    enrich_rows: list[SheetsRow] = []

    for sheet in currents:
        key = _norm_code_loose(sheet.musteri_stok_kodu)
        queue = r1_queues.get(key, [])
        r1 = queue.pop(0) if queue else None

        line = sheets_row_to_quote_line(sheet, len(lines) + 1)
        indirimli = _parse_price(sheet.birim_fiyat)
        line.indirimli_birim_fiyat = indirimli
        line.toplam_fiyat = (
            (indirimli * Decimal(line.adet)).quantize(Decimal("0.01"))
            if line.adet
            else Decimal("0")
        )

        if r1 is not None:
            line.birim_fiyat = _parse_price(r1.birim_fiyat)
        else:
            line.birim_fiyat = Decimal("0")
            warnings.append(
                f"Stok {sheet.musteri_stok_kodu or key}: Revizyonu=1 karşılığı yok "
                f"(veya aynı stokta sıra doldu); eski birim fiyat alınamadı."
            )

        lines.append(line)
        enrich_rows.append(sheet)

    unused_r1 = sum(len(q) for q in r1_queues.values())
    if unused_r1:
        warnings.append(
            f"Revizyonu=1'de {unused_r1} satırın güncelde karşılığı yok; "
            "eski fiyat eşlemesinde kullanılmadı."
        )

    teslim = build_teslim_tarihi_text(
        [line.teslim_suresi_parcasi for line in lines]
    )
    meta_source = enrich_rows or sheets_rows
    teklif_no, istek_no = _meta_from_sheets(meta_source)

    form_revizyon = ""
    if max_current_rev >= 2:
        form_revizyon = str(max_current_rev - 1)

    if not lines:
        warnings.append(
            "Revize Sheets'ten ürün satırı üretilemedi. "
            "Revizyonu=1 ve güncel (2/3/…) satırlarını birlikte yapıştırın."
        )

    return SheetsApplyResult(
        quote_lines=lines,
        teslim_tarihi_text=teslim,
        teklif_no=teklif_no,
        istek_no=istek_no,
        warnings=warnings,
        enrich_sheets_rows=enrich_rows,
        form_revizyon=form_revizyon,
    )


@dataclass
class MergeResult:
    quote_lines: list[QuoteLine]
    conflicts: list[str] = field(default_factory=list)
    matches: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _norm_code(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", (value or "")).upper()


def _norm_code_loose(value: str) -> str:
    """Eşleştirme: nokta/boşluk yok; sayısal kodlarda baştaki sıfırlar yok sayılır."""
    norm = _norm_code(value)
    if norm.isdigit():
        return norm.lstrip("0") or "0"
    return norm


_INVISIBLE = re.compile(r"[\u200b-\u200d\ufeff]")


def _strip_trailing_stok(text: str, *stok_codes: str) -> str:
    """Sondaki ' / stok_kodu' eklerini (çift eklenmiş olsa bile) temizle."""
    codes = {_norm_code_loose(c) for c in stok_codes if (c or "").strip()}
    out = text
    while True:
        match = re.search(r"\s*/\s*([A-Za-z0-9._-]+)\s*$", out)
        if not match:
            break
        raw = match.group(1)
        token_norm = _norm_code_loose(raw)
        digits = raw.replace(".", "")
        stockish = digits.isdigit() and len(_norm_code(raw)) >= 4
        if (codes and token_norm in codes) or stockish:
            out = out[: match.start()].rstrip()
            continue
        break
    return out


def _aciklama_core(line: QuoteLine, *peer_stok_codes: str) -> str:
    """Karşılaştırma için açıklama özeti (proje / stok tanımı; eki ve stok kodu yok)."""
    text = (line.stok_aciklama or line.aciklama or "").strip()
    if not text:
        return ""
    first = text.split("\n", 1)[0]
    first = _INVISIBLE.sub("", first).replace("\u00a0", " ")
    first = _strip_trailing_stok(first, line.stok_kodu, *peer_stok_codes)
    return " ".join(first.lower().split())


def _pair_excel_lines(
    sheets_lines: list[QuoteLine], excel_lines: list[QuoteLine]
) -> list[QuoteLine | None]:
    """
    Her Sheets satırı için Excel eşlemesi:
    Müşteri/Excel stok kodu + aynı kod içindeki sıra (1.↔1., 2.↔2.).
    Stok kodu olmayanlar kalan Excel satırlarıyla sıraya göre.
    """
    remaining = list(enumerate(excel_lines))
    paired: list[QuoteLine | None] = [None] * len(sheets_lines)

    for i, sline in enumerate(sheets_lines):
        sk = _norm_code_loose(sline.stok_kodu)
        if not sk:
            continue
        for j, (idx, eline) in enumerate(remaining):
            if _norm_code_loose(eline.stok_kodu) == sk:
                paired[i] = eline
                remaining.pop(j)
                break

    for i, sline in enumerate(sheets_lines):
        if paired[i] is not None:
            continue
        if not remaining:
            break
        idx, eline = remaining.pop(0)
        paired[i] = eline

    return paired


def merge_excel_into_sheets_lines(
    sheets_lines: list[QuoteLine],
    excel_lines: list[QuoteLine],
    *,
    sheets_istek_no: str = "",
    excel_istek_no: str = "",
) -> MergeResult:
    """
    Sheets master. Excel yalnızca boş alanları doldurur.
    Çelişkide Sheets değeri kalır ve conflict kaydı üretilir.
    """
    conflicts: list[str] = []
    matches: list[str] = []
    warnings: list[str] = []

    s_istek = (sheets_istek_no or "").strip()
    e_istek = (excel_istek_no or "").strip()
    if s_istek and e_istek:
        if s_istek.casefold() == e_istek.casefold():
            matches.append(f"İstek No eşleşti ({s_istek})")
        else:
            conflicts.append(
                f"İstek No çelişkisi — Sheets (Müşteri Teklif No)={s_istek}, "
                f"Excel (dosya adı)={e_istek} (Sheets kullanıldı)."
            )

    n_sheets = len(sheets_lines)
    n_excel = len(excel_lines)
    if n_sheets == n_excel:
        matches.append(f"Satır sayısı eşleşti ({n_sheets})")
    else:
        conflicts.append(
            f"Satır sayısı çelişkisi — Sheets={n_sheets}, "
            f"Excel={n_excel} (Sheets satırları kullanıldı)."
        )

    paired = _pair_excel_lines(sheets_lines, excel_lines)
    out: list[QuoteLine] = []
    aciklama_ok = 0
    aciklama_checked = 0

    for i, sline in enumerate(sheets_lines):
        eline = paired[i]
        data = sline.model_dump()
        row_no = i + 1

        if eline is None:
            warnings.append(
                f"Satır {row_no}: Sheets satırının Import Excel karşılığı yok "
                f"(stok={sline.stok_kodu or '—'})."
            )
            out.append(QuoteLine(**data))
            continue

        # Çelişkiler — Sheets kazanır (fiyat karşılaştırılmaz)
        if sline.adet and eline.adet and sline.adet != eline.adet:
            conflicts.append(
                f"Satır {row_no}: Adet çelişkisi — Sheets={sline.adet}, "
                f"Excel={eline.adet} (Sheets kullanıldı)."
            )
        sc = (sline.ants_is_urun_kodu or "").strip()
        ec = (eline.ants_is_urun_kodu or "").strip()
        if sc and ec and sc.lower() != "na" and ec.lower() != "na" and sc != ec:
            conflicts.append(
                f"Satır {row_no}: Antsis kodu çelişkisi — Sheets={sc}, "
                f"Excel={ec} (Sheets kullanıldı)."
            )
        sa = _aciklama_core(sline, eline.stok_kodu)
        ea = _aciklama_core(eline, sline.stok_kodu)
        if sa and ea:
            aciklama_checked += 1
            if sa == ea:
                aciklama_ok += 1
            else:
                s_show = (sline.stok_aciklama or sline.aciklama or "").split("\n", 1)[0]
                e_show = (eline.stok_aciklama or eline.aciklama or "").split("\n", 1)[0]
                conflicts.append(
                    f"Satır {row_no}: Açıklama çelişkisi — "
                    f"Sheets={s_show}, Excel={e_show} (Sheets kullanıldı)."
                )

        # Boş Sheets alanlarını Excel'den doldur
        if not data.get("stok_kodu") and eline.stok_kodu:
            data["stok_kodu"] = eline.stok_kodu
        if not (data.get("aciklama") or "").strip() and eline.aciklama:
            data["aciklama"] = eline.aciklama
            data["stok_aciklama"] = eline.stok_aciklama or eline.aciklama
        if not data.get("adet") and eline.adet:
            data["adet"] = eline.adet
        if data.get("birim_fiyat", Decimal("0")) == 0 and eline.birim_fiyat:
            data["birim_fiyat"] = eline.birim_fiyat
            data["toplam_fiyat"] = eline.toplam_fiyat or (
                eline.birim_fiyat * Decimal(eline.adet or 0)
            )
        if not (data.get("ants_is_urun_kodu") or "").strip() and ec:
            data["ants_is_urun_kodu"] = ec
        if not (data.get("teslim_suresi_parcasi") or "").strip() and eline.teslim_suresi_parcasi:
            data["teslim_suresi_parcasi"] = eline.teslim_suresi_parcasi
        if data.get("termin_tarihi") is None and eline.termin_tarihi:
            data["termin_tarihi"] = eline.termin_tarihi
        for field_name in (
            "kalite_provizyonlari",
            "teknik_resim_sartname",
            "kalem_revizyon",
        ):
            if not (data.get(field_name) or "").strip() and getattr(eline, field_name):
                data[field_name] = getattr(eline, field_name)

        out.append(QuoteLine(**data))

    if aciklama_checked and aciklama_ok == aciklama_checked:
        matches.append(f"Açıklama eşleşti ({aciklama_ok} satır)")
    elif aciklama_ok:
        matches.append(
            f"Açıklama eşleşti ({aciklama_ok}/{aciklama_checked} satır)"
        )

    unused = len(excel_lines) - sum(1 for p in paired if p is not None)
    if unused > 0:
        warnings.append(
            f"Import Excel'de {unused} fazla satır var; Sheets master olduğu "
            "için eklenmedi."
        )

    return MergeResult(
        quote_lines=out,
        conflicts=conflicts,
        matches=matches,
        warnings=warnings,
    )
