from datetime import date
from pathlib import Path

from teklif_hazirlama.core.import_parser import ImportParseError, ImportParser
from teklif_hazirlama.infrastructure.excel_import_reader import (
    FIELD_ALIASES,
    normalize_header,
    resolve_field_columns,
)


def test_gereksinim_tarihi_alias():
    headers = [
        "Teklifte Bulun",
        "Stok Kodu",
        "Stok Tanımı",
        "Miktar",
        "Gereksinim Tarihi",
        "Fiyat",
        "Satır Toplamı",
        "Kalite Provizyonları",
        "Teknik Resim/Şartname",
        "Kalem Revizyon",
    ]
    cols = resolve_field_columns(headers, aliases=FIELD_ALIASES)
    assert cols["termin_tarihi"] == 4
    assert cols["kalite_provizyonlari"] == 7
    assert cols["teknik_resim_sartname"] == 8
    assert cols["kalem_revizyon"] == 9
    assert normalize_header("Gereksinim Tarihi") == "gereksinim tarihi"


def test_parse_tr_month_date():
    parser = ImportParser()
    assert parser._to_date("Ağu 10, 2026") == date(2026, 8, 10)
    assert parser._to_date("Oca 01, 2027") == date(2027, 1, 1)
    assert parser._to_date("Tem 01, 2026") == date(2026, 7, 1)


def test_parse_new_quote_supplier_excel():
    path = Path(r"C:\Users\Asus.DESKTOP-9F6EQVL\Desktop\KLDHDh\Quote Supplier Datatable (1).xlsx")
    if not path.exists():
        return
    lines, errors = ImportParser().parse(path, mode="istek")
    assert not errors
    assert len(lines) >= 5
    first = lines[0]
    assert first.stok_kodu == "348339"
    assert first.termin_tarihi == date(2026, 8, 10)
    assert "GP2" in first.kalite_provizyonlari
    assert first.teknik_resim_sartname == "N"
    assert first.ants_is_urun_kodu == "ANT-USS-863D"

    # Teklif formu eski Excel modelini kullanır; yeni dosya bu moda uygun değil
    try:
        ImportParser().parse(path, mode="teklif")
        assert False, "yeni excel teklif modunda kabul edilmemeli"
    except ImportParseError:
        pass
