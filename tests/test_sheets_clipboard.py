from datetime import date
from decimal import Decimal
from pathlib import Path

from teklif_hazirlama.application.quote_workflow import QuoteRequest, QuoteWorkflow
from teklif_hazirlama.core.models import CustomerConfig, QuoteHeader, QuoteLine
from teklif_hazirlama.core.sheets_clipboard import (
    build_istek_sheets_tsv,
    build_sheets_tsv,
    format_money_plain,
    format_year_month_tr,
    hazirlayan_initials,
    hazirlayan_initials_spaced,
)


def test_hazirlayan_initials():
    assert hazirlayan_initials("Alican Uzun") == "au"
    assert hazirlayan_initials("İrem Su") == "is"
    assert hazirlayan_initials("Kerem Özsoy") == "ko"
    assert hazirlayan_initials_spaced("Alican Uzun") == "a u"
    assert hazirlayan_initials_spaced("Kerem Özsoy") == "k o"


def test_format_year_month_tr():
    assert format_year_month_tr(date(2026, 7, 11)) == "2026 Temmuz"


def test_generate_teklif_no_roketsan():
    from teklif_hazirlama.core.sheets_clipboard import generate_teklif_no

    assert generate_teklif_no("roketsan", date(2026, 7, 11)) == "RKTSN-2607-11"
    assert generate_teklif_no("aselsan", date(2026, 7, 11)) == ""


def test_format_teklif_no_with_revizyon():
    from teklif_hazirlama.core.sheets_clipboard import format_teklif_no_with_revizyon

    assert format_teklif_no_with_revizyon("ant2526", "2") == "ant2526-R2"
    assert format_teklif_no_with_revizyon("ant2526", "R2") == "ant2526-R2"
    assert format_teklif_no_with_revizyon("ant2526", "") == "ant2526"


def test_next_revizyon_for_copy():
    from teklif_hazirlama.core.sheets_clipboard import next_revizyon_for_copy

    assert next_revizyon_for_copy("1") == "2"
    assert next_revizyon_for_copy("2") == "3"
    assert next_revizyon_for_copy("3") == "4"
    assert next_revizyon_for_copy("R2") == "3"
    assert next_revizyon_for_copy("") == ""


def test_format_money_plain_no_dollar():
    assert format_money_plain(Decimal("2025")) == "2.025,00"
    assert "$" not in format_money_plain(Decimal("12.5"))


def test_build_sheets_tsv_columns():
    customer = CustomerConfig(
        code="roketsan",
        name="Roketsan Uzun Unvan A.Ş.",
        gecerlilik_gun=30,
        firma={"unvan": "Roketsan", "adres_satirlari": [], "telefon": ""},
    )
    header = QuoteHeader(
        teklif_no="RKTSN-1",
        tarih=date(2026, 7, 11),
        hitap_kisi="İremsu Yazıcı",
        hazirlayan="Alican Uzun",
        teslimat="Yurtiçi",
        teslimat_sekli="Kapı",
        odeme_sekli="Peşin",
        istek_no="QR075313",
        revizyon="R3",
    )
    lines = [
        QuoteLine(
            row_number=3,
            adet=29,
            ants_is_urun_kodu="ANT-1",
            aciklama="VIDEO / 002",
            birim_fiyat=Decimal("2025"),
            toplam_fiyat=Decimal("58725"),
            stok_aciklama="VIDEO ENCODER / 00239277",
            termin_tarihi=date(2026, 6, 1),
        )
    ]
    text = build_sheets_tsv(customer, header, lines)
    cols = text.split("\t")
    assert cols[0] == ""  # A
    assert cols[1] == ""  # B
    assert cols[2] == "roketsan"  # C
    assert cols[3] == "VIDEO ENCODER / 00239277"  # D
    assert cols[4] == "29"  # E
    assert cols[5] == "11.07.2026"  # F
    assert cols[6] == "RKTSN-1"  # G
    assert cols[7] == "QR075313"  # H
    assert cols[8] == "01.06.2026"  # I
    assert cols[9] == "2.025,00"  # J
    assert cols[10] == "58.725,00"  # K
    assert cols[11] == "4"  # L — girilen R3 → kopyada 4
    assert cols[12] == "au"  # M
    assert cols[13] == ""  # N
    assert cols[14] == ""  # O
    assert cols[15] == "Sorumlusu : İremsu Yazıcı"  # P


def test_workflow_clipboard_from_real_import():
    real = Path(r"C:\Users\Asus.DESKTOP-9F6EQVL\Desktop\KLDHDh\QR075313.xlsx")
    if not real.exists():
        return
    text = QuoteWorkflow().build_sheets_clipboard_text(
        QuoteRequest(
            customer_code="roketsan",
            teklif_no="TEST-COPY",
            hitap_kisi="İremsu Yazıcı",
            hitap_adres_satirlari=[],
            hitap_telefon="",
            hazirlayan="Alican Uzun",
            teslimat="Yurtiçi",
            teslimat_sekli="Kapı",
            odeme_sekli="Peşin",
            import_excel_path=str(real),
            ozel_sartlar=[],
            output_dir="tests/output",
            tarih=date(2026, 7, 11),
            revizyon="R1",
        )
    )
    rows = text.splitlines()
    assert len(rows) >= 1
    first = rows[0].split("\t")
    assert first[0] == ""
    assert first[1] == ""
    assert first[2] == "roketsan"
    assert " / " in first[3]
    assert first[8]  # termin tarihi
    assert first[12] == "au"
    assert first[15].startswith("Sorumlusu :")


def test_build_istek_sheets_tsv():
    customer = CustomerConfig(
        code="roketsan",
        name="Roketsan Uzun Unvan A.Ş.",
        gecerlilik_gun=30,
        firma={"unvan": "Roketsan", "adres_satirlari": [], "telefon": ""},
    )
    lines = [
        QuoteLine(
            row_number=3,
            adet=29,
            ants_is_urun_kodu="ANT-1",
            aciklama="VIDEO / 002",
            birim_fiyat=Decimal("2025"),
            toplam_fiyat=Decimal("58725"),
            stok_kodu="00239277",
            stok_aciklama="VIDEO ENCODER / 00239277",
            termin_tarihi=date(2026, 6, 1),
            kalite_provizyonlari="KP-1",
            teknik_resim_sartname="TR-9",
            kalem_revizyon="A",
        )
    ]
    text = build_istek_sheets_tsv(
        customer,
        lines,
        hazirlayan="Alican Uzun",
        teklif_no="ANT2526",
        musteri_teklif_no="MUST-99",
        hitap_kisi="İremsu Yazıcı",
        tarih=date(2026, 7, 11),
    )
    cols = text.split("\t")
    assert cols[0] == "2026 Temmuz"  # A
    assert cols[1] == ""  # B
    assert cols[2] == "roketsan"  # C
    assert cols[3] == ""  # D
    assert cols[4] == "00239277"  # E stok kodu
    assert cols[5] == "VIDEO ENCODER / 00239277"  # F
    assert cols[6] == "29"  # G
    assert cols[7] == "11.07.2026"  # H
    assert cols[8] == "ANT2526"  # I
    assert cols[9] == "MUST-99"  # J müşteri teklif no
    assert cols[10] == "01.06.2026"  # K
    assert cols[11] == "2.025,00"  # L
    assert cols[12] == "58.725,00"  # M
    assert cols[13] == "1"  # N
    assert cols[14] == "au"  # O
    assert cols[15] == ""  # P
    assert cols[16] == ""  # Q
    assert cols[17] == "KP-1"  # R
    assert cols[18] == "TR-9"  # S
    assert cols[19] == "A"  # T
    assert cols[20] == ""  # U
    assert cols[21] == ""  # V
    assert cols[22] == "İremsu Yazıcı"  # W
