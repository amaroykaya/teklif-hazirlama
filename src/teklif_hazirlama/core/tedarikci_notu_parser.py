from __future__ import annotations

import re
from dataclasses import dataclass

T0_MARKER = "T0: Sipariş Onay Tarihi"
# FR-29: "Teslim süresi :"; eski metinler: "Teslim Süreleri :"
TESLIM_PATTERN = re.compile(r"Teslim\s*S[uü]re(?:si|leri)\s*:", re.IGNORECASE)
T0_PATTERN = re.compile(r"T0:\s*Sipari[sş]\s*Onay\s*Tarihi", re.IGNORECASE)


def _normalize_text(text: str) -> str:
    tr_map = str.maketrans(
        {
            "ı": "i",
            "İ": "i",
            "ğ": "g",
            "Ğ": "g",
            "ü": "u",
            "Ü": "u",
            "ş": "s",
            "Ş": "s",
            "ö": "o",
            "Ö": "o",
            "ç": "c",
            "Ç": "c",
        }
    )
    return text.translate(tr_map)


@dataclass
class TedarikciNotuParseResult:
    urun_kodu: str
    teslim_suresi_parcasi: str
    aciklama_eki: str


def parse_tedarikci_notu(text: str | None) -> TedarikciNotuParseResult:
    if not text or not str(text).strip():
        return TedarikciNotuParseResult("", "", "")

    raw = str(text).strip()
    normalized = _normalize_text(raw)
    urun_kodu = ""
    teslim_parcasi = ""
    aciklama_eki = ""

    match = TESLIM_PATTERN.search(normalized)
    if not match:
        return TedarikciNotuParseResult("", "", "")

    after_marker = normalized[match.end() :].strip()
    t0_match = T0_PATTERN.search(after_marker)
    if t0_match:
        before_t0 = after_marker[: t0_match.start()].strip()
        after_t0 = after_marker[t0_match.end() :].strip()
        teslim_parcasi = before_t0
        aciklama_eki = after_t0
        urun_kodu = extract_urun_kodu(before_t0)
    else:
        urun_kodu = extract_urun_kodu(after_marker)
        teslim_parcasi = after_marker.strip()

    return TedarikciNotuParseResult(urun_kodu, teslim_parcasi, aciklama_eki)


def extract_urun_kodu(segment: str) -> str:
    segment = segment.strip()
    if " - " in segment:
        return segment.split(" - ", 1)[0].strip()
    match = re.match(r"^(.+?)\s+-\s+\d+\s+adet", segment, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return segment.strip()


def build_teslim_tarihi_text(parcalar: list[str]) -> str:
    """
    Her ürün kodu tek satır: 'KOD - N adet T0+H Hafta, ...'
    Satır uzunsa Excel/UI wrap ile alta geçer; dilimler ayrı satıra bölünmez.
    """
    lines: list[str] = []
    for parca in parcalar:
        if not parca or not str(parca).strip():
            continue
        lines.append(_normalize_teslim_parca_one_line(str(parca).strip()))
    if not lines:
        return ""
    return "\n".join(lines + [T0_MARKER])


def _normalize_teslim_parca_one_line(text: str) -> str:
    """Yanlışlıkla satırlara bölünmüş dilimleri tekrar tek satırda birleştir."""
    # Hem satır sonu hem 'Hafta ,' ile bölünmüş olabilir
    chunks: list[str] = []
    for piece in re.split(r"[\n\r]+", text):
        piece = piece.strip()
        if not piece:
            continue
        chunks.extend(
            p.strip()
            for p in re.split(r"(?<=Hafta)\s*,\s*(?=\S)", piece, flags=re.IGNORECASE)
            if p.strip()
        )
    if len(chunks) <= 1:
        return text.replace("\n", " ").strip()
    return ", ".join(chunks)


def append_aciklama_eki(base: str, eki: str) -> str:
    if not eki:
        return base
    return f"{base}\n( {eki} )"
