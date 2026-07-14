from __future__ import annotations

from datetime import date
from decimal import Decimal

from teklif_hazirlama.core.models import CustomerConfig, QuoteHeader, QuoteLine


def format_money_plain(amount: Decimal) -> str:
    """Dolar işareti olmadan TR format: 1.234,56"""
    q = amount.quantize(Decimal("0.01"))
    text = f"{q:.2f}"
    integer, _, frac = text.partition(".")
    int_with_sep = f"{int(integer):,}".replace(",", ".")
    return f"{int_with_sep},{frac}"


def format_date_tr(value: date | None) -> str:
    if value is None:
        return ""
    return value.strftime("%d.%m.%Y")


# Hazırlayan baş harfleri: Türkçe → ASCII (Özsoy → o, Şahin → s)
_INITIAL_MAP = str.maketrans(
    {
        "İ": "i",
        "I": "i",
        "ı": "i",
        "Ö": "o",
        "ö": "o",
        "Ü": "u",
        "ü": "u",
        "Ş": "s",
        "ş": "s",
        "Ç": "c",
        "ç": "c",
        "Ğ": "g",
        "ğ": "g",
    }
)


def hazirlayan_initials(name: str) -> str:
    """Kerem Özsoy → ko (Türkçe harfler ASCII)."""
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return ""
    initials = []
    for part in parts:
        ch = part[0].translate(_INITIAL_MAP)
        initials.append(ch.casefold())
    return "".join(initials)


def hazirlayan_initials_spaced(name: str) -> str:
    """Alican Uzun → 'a u'"""
    joined = hazirlayan_initials(name)
    return " ".join(joined) if joined else ""


AY_ADLARI = {
    1: "Ocak",
    2: "Şubat",
    3: "Mart",
    4: "Nisan",
    5: "Mayıs",
    6: "Haziran",
    7: "Temmuz",
    8: "Ağustos",
    9: "Eylül",
    10: "Ekim",
    11: "Kasım",
    12: "Aralık",
}


def format_year_month_tr(value: date | None = None) -> str:
    """2026 Temmuz"""
    d = value or date.today()
    return f"{d.year} {AY_ADLARI[d.month]}"


def generate_teklif_no(customer_code: str, tarih: date | None = None) -> str:
    """Roketsan: RKTSN-YYAA-GG (örn. 11.07.2026 → RKTSN-2607-11)."""
    code = (customer_code or "").strip().lower()
    if code != "roketsan":
        return ""
    d = tarih or date.today()
    return f"RKTSN-{d.year % 100:02d}{d.month:02d}-{d.day:02d}"


def short_firma_name(customer: CustomerConfig) -> str:
    return (customer.code or customer.name or "").strip().lower()


def format_teklif_no_with_revizyon(teklif_no: str, revizyon: str) -> str:
    """Formdaki teklif no: ant2526 + 2 → ant2526-R2"""
    base = teklif_no.strip()
    rev = revizyon.strip()
    if not base:
        return ""
    if not rev:
        return base
    if rev.upper().startswith("R"):
        rev = rev[1:].strip() or rev
    return f"{base}-R{rev}"


def next_revizyon_for_copy(revizyon: str) -> str:
    """Kopyalanan metin için revizyon: 1→2, 2→3, R3→4."""
    rev = revizyon.strip()
    if not rev:
        return ""
    text = rev[1:].strip() if rev.upper().startswith("R") else rev
    try:
        return str(int(text) + 1)
    except ValueError:
        return rev


def build_sheets_tsv(
    customer: CustomerConfig,
    header: QuoteHeader,
    lines: list[QuoteLine],
) -> str:
    """Google Sheets A hücresine yapıştırılacak TSV (A..P); A ve B boş."""
    firma = short_firma_name(customer)
    tarih = format_date_tr(header.tarih)
    teklif_no = header.teklif_no.strip()
    istek_no = header.istek_no.strip()
    revizyon = next_revizyon_for_copy(header.revizyon)
    initials = hazirlayan_initials(header.hazirlayan)
    sorumlusu = f"Sorumlusu : {header.hitap_kisi.strip()}"

    rows: list[str] = []
    for line in lines:
        cells = [
            "",  # A
            "",  # B
            firma,  # C
            line.stok_aciklama or line.aciklama.split("\n", 1)[0],  # D
            str(line.adet),  # E
            tarih,  # F
            teklif_no,  # G
            istek_no,  # H
            format_date_tr(line.termin_tarihi),  # I
            format_money_plain(line.birim_fiyat),  # J
            format_money_plain(line.toplam_fiyat),  # K
            revizyon,  # L
            initials,  # M
            "",  # N
            "",  # O
            sorumlusu,  # P
        ]
        rows.append("\t".join(cells))
    return "\n".join(rows)


def build_istek_sheets_tsv(
    customer: CustomerConfig,
    lines: list[QuoteLine],
    *,
    hazirlayan: str,
    teklif_no: str,
    musteri_teklif_no: str,
    hitap_kisi: str,
    tarih: date | None = None,
) -> str:
    """İlk teklif isteği — Google Sheets A hücresine yapıştırılacak TSV (A..W)."""
    bugun = tarih or date.today()
    yil_ay = format_year_month_tr(bugun)
    firma = short_firma_name(customer)
    bugun_text = format_date_tr(bugun)
    initials = hazirlayan_initials(hazirlayan)
    teklif = teklif_no.strip()
    musteri_teklif = musteri_teklif_no.strip()
    hitap = hitap_kisi.strip()

    rows: list[str] = []
    for line in lines:
        stok_kodu = line.stok_kodu.strip()
        stok_aciklama = line.stok_aciklama or line.aciklama.split("\n", 1)[0]
        cells = [
            yil_ay,  # A
            "",  # B
            firma,  # C
            "",  # D
            stok_kodu,  # E
            stok_aciklama,  # F — Stok Tanımı / Stok Kodu
            str(line.adet),  # G
            bugun_text,  # H
            teklif,  # I
            musteri_teklif,  # J — müşteri teklif no (elle)
            format_date_tr(line.termin_tarihi),  # K
            format_money_plain(line.birim_fiyat),  # L
            format_money_plain(line.toplam_fiyat),  # M
            "1",  # N — revizyon
            initials,  # O
            "",  # P
            "",  # Q
            line.kalite_provizyonlari,  # R
            line.teknik_resim_sartname,  # S
            line.kalem_revizyon,  # T
            "",  # U
            "",  # V
            hitap,  # W
        ]
        rows.append("\t".join(cells))
    return "\n".join(rows)
