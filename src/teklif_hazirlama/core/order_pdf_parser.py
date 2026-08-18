from __future__ import annotations

import re
from pathlib import Path

from teklif_hazirlama.core.models import OrderPdfHeader, OrderPdfLine

DATE_SLASH_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
DATE_DOT_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
SS_RE = re.compile(r"\bSS\s*(\d+)\b", re.IGNORECASE)
SS_LINE_RE = re.compile(r"^SS\s*(\d+)\s+(.*)$", re.IGNORECASE)
PO_RE = re.compile(r"\b(PO[- ]*\d+)\b", re.IGNORECASE)
QUALITY_CODE_RE = re.compile(r"^[A-Z]{1,4}\d{0,2}$", re.IGNORECASE)
REV_TOKEN_RE = re.compile(r"^[A-Z]\d{2}$", re.IGNORECASE)
PART_NO_RE = re.compile(r"^\d{5,}$")
SV_TOKEN_RE = re.compile(r"^SV\d+", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"[ \t]+")
# Yapışık açıklama ayırırken bilinen kodlar (MMNETHERNET → MMN, MMNE değil)
KNOWN_QUALITY_CODES = frozenset(
    {
        "C",
        "CC",
        "D",
        "DD",
        "DKG",
        "G",
        "GP2",
        "GT",
        "H",
        "HM",
        "J",
        "K",
        "L",
        "M",
        "MM",
        "MMN",
        "N",
        "O",
        "P",
        "Q",
        "R",
        "SW",
        "T",
        "TR",
        "V",
        "XX",
    }
)


class OrderPdfParseError(Exception):
    pass


class OrderPdfParser:
    def parse(self, pdf_path: str | Path) -> tuple[OrderPdfHeader, dict[str, OrderPdfLine]]:
        text = extract_pdf_text(pdf_path)
        if not text.strip():
            raise OrderPdfParseError("PDF içeriği okunamadı.")
        return parse_order_pdf_text(text)


def extract_pdf_text(pdf_path: str | Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(Path(pdf_path)))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def parse_order_pdf_text(text: str) -> tuple[OrderPdfHeader, dict[str, OrderPdfLine]]:
    cleaned = _normalize_text(text)
    lines = cleaned.splitlines()
    header = OrderPdfHeader(
        siparis_tarihi=_extract_labeled_date(lines),
        siparis_numarasi=_extract_labeled_po(lines),
        buyer=_extract_labeled_value(
            lines,
            "SATIN ALMA SORUMLUSU/ BUYER",
        ),
    )
    ss_lines = _extract_ss_lines(lines)
    return header, ss_lines


def _normalize_text(text: str) -> str:
    normalized_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = line.replace("#", " ").replace("\x06", " ").replace("\uFFFD", " ")
        line = (
            line.replace("İ", "I")
            .replace("ı", "i")
            .replace("Ş", "S")
            .replace("ş", "s")
            .replace("Ğ", "G")
            .replace("ğ", "g")
            .replace("Ü", "U")
            .replace("ü", "u")
            .replace("Ö", "O")
            .replace("ö", "o")
            .replace("Ç", "C")
            .replace("ç", "c")
        )
        line = WHITESPACE_RE.sub(" ", line)
        normalized_lines.append(line)
    return "\n".join(normalized_lines)


def _extract_labeled_value(
    lines: list[str],
    label: str,
) -> str:
    for index, line in enumerate(lines):
        if label.casefold() not in line.casefold():
            continue
        trailing = line.split(label, 1)[1].strip(" :-")
        candidate = trailing
        if candidate:
            return candidate.strip()
        for probe in lines[index + 1:index + 6]:
            probe = probe.strip()
            if probe:
                return probe
    return ""


def _extract_labeled_date(lines: list[str]) -> str:
    for index in _indexes_for_any_label(lines, ["SIPARIS TARIHI/", "PO DATE"]):
        window = " ".join(lines[index:index + 10])
        value = _format_any_date(window)
        if value:
            return value
    return ""


def _extract_labeled_po(lines: list[str]) -> str:
    for index in _indexes_for_any_label(lines, ["SIPARIS EMRI NO/", "PURCHASE ORDER NO"]):
        window = " ".join(lines[index:index + 8])
        match = PO_RE.search(window)
        if match:
            return match.group(1).replace(" ", "").upper()
        number_match = re.search(r"\b(\d{6,})\b", window)
        if number_match:
            return number_match.group(1)
    return ""


def _indexes_for_any_label(lines: list[str], labels: list[str]) -> list[int]:
    results: list[int] = []
    lowered = [label.casefold() for label in labels]
    for index, line in enumerate(lines):
        hay = line.casefold()
        if any(label in hay for label in lowered):
            results.append(index)
    return results


def _extract_ss_lines(lines: list[str]) -> dict[str, OrderPdfLine]:
    results: dict[str, OrderPdfLine] = {}
    ss_indexes = [index for index, line in enumerate(lines) if SS_RE.search(line)]
    for pos, index in enumerate(ss_indexes):
        line = lines[index]
        ss_match = SS_RE.search(line)
        if not ss_match:
            continue
        ss_no = f"SS{ss_match.group(1)}"
        next_index = ss_indexes[pos + 1] if pos + 1 < len(ss_indexes) else len(lines)
        block = lines[index:next_index]
        planlanan = _first_date_in_text(" ".join(block))
        quality = _extract_quality_from_block(block)

        results[ss_no] = OrderPdfLine(
            ss_no=ss_no,
            planlanan_sevk_tarihi=planlanan,
            kalite_provizyonlari=quality.strip(),
        )
    return results


def _extract_quality_from_block(block: list[str]) -> str:
    """Kalite = QUALITY ASSURANCE PROVISIONS sütunu (REV opsiyonel)."""
    if not block:
        return ""
    quality_parts: list[str] = []
    first = block[0]
    line_match = SS_LINE_RE.match(first)
    if line_match:
        tokens = line_match.group(2).split()
        blob = _quality_blob_from_ss_tokens(tokens)
        if blob:
            quality_parts.append(_normalize_quality_token(blob))
    for line in block[1:4]:
        candidate = line.strip()
        if _is_quality_blob(candidate):
            quality_parts.append(_normalize_quality_token(candidate))
        else:
            break
    return " ".join(quality_parts).strip()


def _quality_blob_from_ss_tokens(tokens: list[str]) -> str:
    """
    SS satırı: SV? + ParçaNo + REV? + KaliteKodları
    REV yoksa kalite doğrudan parça numarasından sonra gelir.
    """
    idx = 0
    if idx < len(tokens) and SV_TOKEN_RE.match(tokens[idx]):
        idx += 1
    if idx < len(tokens) and PART_NO_RE.match(tokens[idx]):
        idx += 1
    if idx >= len(tokens):
        return ""
    # REV varsa atla (D01, P00...); kalite virgüllü kod listesi
    if _is_quality_blob(tokens[idx]):
        return tokens[idx]
    if idx + 1 < len(tokens) and _is_rev_token(tokens[idx]) and _is_quality_blob(
        tokens[idx + 1]
    ):
        return tokens[idx + 1]
    if idx + 1 < len(tokens) and _is_quality_blob(tokens[idx + 1]):
        return tokens[idx + 1]
    return ""


def _is_rev_token(token: str) -> bool:
    text = token.strip()
    if text in {"-", "–", "—"}:
        return True
    return bool(REV_TOKEN_RE.fullmatch(text))


def _is_quality_code(piece: str) -> bool:
    return bool(QUALITY_CODE_RE.fullmatch(piece.strip()))


def _longest_quality_code_prefix(piece: str) -> str:
    """PDF bazen kaliteyi açıklamaya yapıştırır: MMNETHERNET → MMN."""
    text = piece.strip().upper()
    if not text:
        return ""
    if QUALITY_CODE_RE.fullmatch(text):
        return text
    # Bilinen kodlar (uzun önce) — MMNE gibi sahte eşleşmeleri engeller
    for code in sorted(KNOWN_QUALITY_CODES, key=len, reverse=True):
        if not text.startswith(code):
            continue
        remainder = text[len(code) :]
        if remainder and remainder[0].isalpha() and len(remainder) >= 3:
            return code
    best = ""
    for end in range(1, min(len(text), 6) + 1):
        candidate = text[:end]
        remainder = text[end:]
        if (
            QUALITY_CODE_RE.fullmatch(candidate)
            and remainder
            and remainder.isalpha()
            and len(remainder) >= 4
        ):
            # Daha uzun açıklama kalıntısı tercih (M+MNETHERNET yerine MMN+ETHERNET için
            # bilinen kod yolu kullanılır; burası yedek)
            if len(remainder) >= len(text) - len(best):
                best = candidate
    return best


def _is_quality_blob(text: str) -> bool:
    """Roketsan kalite sütunu: virgüllü kısa kod listesi (GP2,L,V,G,XX)."""
    raw = (text or "").strip()
    if not raw or "," not in raw:
        return False
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) < 2:
        return False
    for index, part in enumerate(parts):
        if _is_quality_code(part):
            continue
        # Son parça: kod + yapışık açıklama (MMNETHERNET)
        if index == len(parts) - 1:
            prefix = _longest_quality_code_prefix(part)
            remainder = part[len(prefix) :] if prefix else ""
            if prefix and remainder and remainder[0].isalpha() and len(remainder) >= 3:
                continue
        return False
    return True


def _normalize_quality_token(token: str) -> str:
    parts: list[str] = []
    for segment in token.split(","):
        piece = segment.strip().upper()
        if not piece:
            continue
        if _is_quality_code(piece):
            parts.append(piece)
            continue
        prefix = _longest_quality_code_prefix(piece)
        parts.append(prefix if prefix else piece)
    return ",".join(parts)


def _first_date_in_text(line: str) -> str:
    match = DATE_SLASH_RE.search(line) or DATE_DOT_RE.search(line)
    if not match:
        return ""
    return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"


def _format_any_date(value: str) -> str:
    match = DATE_SLASH_RE.search(value) or DATE_DOT_RE.search(value)
    if not match:
        return ""
    return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
