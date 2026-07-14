from pathlib import Path

from teklif_hazirlama.core.import_parser import ImportParser

REAL_FILE = Path(r"C:\Users\Asus.DESKTOP-9F6EQVL\Desktop\KLDHDh\QR075313.xlsx")


def test_parse_real_roketsan_import_file():
    if not REAL_FILE.exists():
        return
    parser = ImportParser()
    lines, errors = parser.parse(REAL_FILE)
    assert len(lines) >= 1
    assert lines[0].ants_is_urun_kodu == "ANT-DVI-ENC-623F"
    assert lines[0].adet == 29
    assert lines[0].toplam_fiyat > 0
