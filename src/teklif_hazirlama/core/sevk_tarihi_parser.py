from __future__ import annotations

import re
from dataclasses import dataclass

# Örn: "5 x 10 hafta", "10x35 hafta"
WEEK_PATTERN = re.compile(
    r"(\d+)\s*[x×]\s*(\d+)\s*hafta",
    re.IGNORECASE,
)
# Örn: "2 adet T0+23 Hafta"
T0_ADET_PATTERN = re.compile(
    r"(\d+)\s*adet\s*T0\+(\d+)\s*Hafta",
    re.IGNORECASE,
)
T0_MARKER_LINE = re.compile(r"^T0:\s*Sipari[sş]\s*Onay\s*Tarihi", re.IGNORECASE)


@dataclass
class WeekEntry:
    adet: int
    hafta: int


@dataclass
class SevkParseResult:
    entries: list[WeekEntry]
    temin_gun: int | None
    t0_segments: str
    warning: str = ""


def parse_week_entries(text: str | None) -> list[WeekEntry]:
    if not text or not str(text).strip():
        return []
    entries: list[WeekEntry] = []
    for match in WEEK_PATTERN.finditer(str(text)):
        entries.append(WeekEntry(adet=int(match.group(1)), hafta=int(match.group(2))))
    return entries


def parse_t0_adet_entries(text: str | None) -> list[WeekEntry]:
    """Teslim Tarihi / Tedarikçi Notu: 'N adet T0+H Hafta'."""
    if not text or not str(text).strip():
        return []
    return [
        WeekEntry(adet=int(m.group(1)), hafta=int(m.group(2)))
        for m in T0_ADET_PATTERN.finditer(str(text))
    ]


def round_up_to_ten(value: int) -> int:
    """
    Bir sonraki (üst) onluğa yuvarla.
    245 → 250; 168 → 170; 210 → 220 (tam onluk da bir üste gider).
    """
    if value <= 0:
        return 0
    return (value // 10 + 1) * 10


def compute_temin_gun(entries: list[WeekEntry]) -> int | None:
    if not entries:
        return None
    max_hafta = max(e.hafta for e in entries)
    return round_up_to_ten(max_hafta * 7)


def format_t0_segments(entries: list[WeekEntry]) -> str:
    """5 adet T0+10 Hafta, 5 adet T0+24 Hafta, ..."""
    parts = [f"{e.adet} adet T0+{e.hafta} Hafta" for e in entries]
    return ", ".join(parts)


def build_tedarikci_notu(
    antsis_urun_kodu: str,
    entries: list[WeekEntry],
    ozel_sartlar: str = "",
) -> str:
    """
    Teslim süresi : {D} - {N adet T0+H Hafta, ...} T0: Sipariş Onay Tarihi {U}
    """
    code = (antsis_urun_kodu or "").strip()
    segments = format_t0_segments(entries)
    base = f"Teslim süresi : {code} - {segments} T0: Sipariş Onay Tarihi"
    extra = (ozel_sartlar or "").strip()
    if extra:
        return f"{base} {extra}"
    return base


def parse_sevk_tarihi(text: str | None) -> SevkParseResult:
    entries = parse_week_entries(text)
    if not entries:
        return SevkParseResult(
            entries=[],
            temin_gun=None,
            t0_segments="",
            warning="Teklif Sevk Tarihi içinde 'N x H hafta' deseni bulunamadı.",
        )
    return SevkParseResult(
        entries=entries,
        temin_gun=compute_temin_gun(entries),
        t0_segments=format_t0_segments(entries),
    )


def split_teslim_tarihi_by_code(text: str | None) -> dict[str, str]:
    """
    Teslim Tarihi metnini ürün koduna göre böler (sıra korunur).
    Örn. 'ANT5307 - 2 adet T0+23 Hafta 3 adet T0+30 Hafta'
    """
    return dict(_iter_teslim_segments(text))


def _iter_teslim_segments(text: str | None) -> list[tuple[str, str]]:
    if not text or not str(text).strip():
        return []
    # En/em dash vb. → normal tire
    normalized = (
        str(text)
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .replace("\xa0", " ")
    )
    segments: list[tuple[str, str]] = []
    current: str | None = None
    parts: list[str] = []

    def flush() -> None:
        nonlocal current, parts
        if current is not None:
            segments.append((current, " ".join(parts).strip()))
        current = None
        parts = []

    for raw_line in normalized.splitlines():
        line = " ".join(raw_line.split()).strip()
        if not line or T0_MARKER_LINE.match(line):
            continue
        # "KOD - ..." veya "KOD- ..."
        m = re.match(r"^(.+?)\s*-\s+(.+)$", line)
        if m:
            left = m.group(1).strip()
            right = m.group(2).strip()
            if left and not left[0].isdigit():
                flush()
                current = left
                parts = [right]
                continue
        if current is not None:
            parts.append(line)
        else:
            # Kod yok; anonim blok
            if not segments and not current:
                current = ""
                parts = [line]
            elif current is not None:
                parts.append(line)
    flush()
    return segments


def _codes_match(a: str, b: str) -> bool:
    na = re.sub(r"[^A-Za-z0-9]", "", (a or "")).upper()
    nb = re.sub(r"[^A-Za-z0-9]", "", (b or "")).upper()
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


def resolve_teslim_entries_for_code(
    teslim_tarihi_text: str | None, code: str
) -> list[WeekEntry]:
    """Ürün koduna ait T0 dilimlerini bul; yoksa tüm metinden dene."""
    code = (code or "").strip()
    segments = _iter_teslim_segments(teslim_tarihi_text)
    if code:
        for seg_code, body in segments:
            if _codes_match(code, seg_code):
                entries = parse_t0_adet_entries(body)
                if entries:
                    return entries
                # gövdede yoksa "kod - gövde" birleşik dene
                entries = parse_t0_adet_entries(f"{seg_code} - {body}")
                if entries:
                    return entries
    if len(segments) == 1:
        seg_code, body = segments[0]
        entries = parse_t0_adet_entries(body) or parse_t0_adet_entries(
            f"{seg_code} - {body}" if seg_code else body
        )
        if entries:
            return entries
    # Son çare: tüm Teslim Tarihi metni (UI'daki son hali)
    return parse_t0_adet_entries(teslim_tarihi_text)


def resolve_teslim_entries_for_line(
    teslim_tarihi_text: str | None,
    code: str,
    *,
    line_index: int = 0,
) -> list[WeekEntry]:
    """Satır indeksine göre de eşlemeyi dener (çoklu ürün)."""
    entries = resolve_teslim_entries_for_code(teslim_tarihi_text, code)
    if entries:
        return entries
    segments = _iter_teslim_segments(teslim_tarihi_text)
    if 0 <= line_index < len(segments):
        seg_code, body = segments[line_index]
        return parse_t0_adet_entries(body) or parse_t0_adet_entries(
            f"{seg_code} - {body}" if seg_code else body
        )
    return []
