from __future__ import annotations

import html
import re

# Tam eşleşen kalite kodları — kırmızı + kalın
HIGHLIGHT_QUALITY_CODES = frozenset(
    {
        "C",
        "D",
        "DD",
        "DKG",
        "H",
        "HM",
        "J",
        "K",
        "N",
        "O",
        "P",
        "Q",
        "R",
        "SW",
        "T",
        "TR",
    }
)

_QUALITY_TOKEN_RE = re.compile(r"([^,\s]+)|([,\s]+)")
_KALITE_LINE_RE = re.compile(
    r"^(Kalite Provizyonları:\s*)(.*)$",
    re.IGNORECASE | re.DOTALL,
)

HIGHLIGHT_SPAN_STYLE = "color:#cc0000;font-weight:bold"


def is_highlight_quality_code(token: str) -> bool:
    return token.strip().upper() in HIGHLIGHT_QUALITY_CODES


def format_quality_html(text: str) -> str:
    """Kalite metninde kritik kodları kırmızı+kalın HTML span yapar."""
    if not text:
        return ""
    parts: list[str] = []
    for match in _QUALITY_TOKEN_RE.finditer(text):
        token, sep = match.group(1), match.group(2)
        if sep is not None:
            parts.append(html.escape(sep))
            continue
        assert token is not None
        escaped = html.escape(token)
        if is_highlight_quality_code(token):
            parts.append(f'<span style="{HIGHLIGHT_SPAN_STYLE}">{escaped}</span>')
        else:
            parts.append(escaped)
    return "".join(parts)


def format_aciklama_html(text: str) -> str:
    """Açıklama satırlarında kalite kodlarını vurgular; satır sonlarını <br> yapar."""
    if not text:
        return ""
    lines: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        match = _KALITE_LINE_RE.match(line)
        if match:
            prefix, values = match.group(1), match.group(2)
            lines.append(f"{html.escape(prefix)}{format_quality_html(values)}")
        else:
            lines.append(html.escape(line))
    return "<br>".join(lines)
