from teklif_hazirlama.core.sheets_tsv_parser import (
    SheetsTsvParseError,
    first_row_is_header,
    parse_clipboard_tsv,
    parse_sheets_tsv,
    rows_from_table_matrix,
)

HEADER = (
    "ilk rev Zamanı\tNo\tFirma\tAntsis Ürün Kodu\tMüşteri Stok Kodu\t"
    "Proje Tanımı\tAdet\tTeklif Tarihi\tAntsis Teklif No\tMüşteri Teklif Numarası\t"
    "Teklif Sevk Tarihi\tBirim Fiyat\tToplam Fiyat\tRevizyonu\tTeklifi Hazırlayan\t"
    "Beklenen Bilgiler\tSipariş alındı mı\tKalite Provizyonu\tTeknik şartname\t"
    "Kalem Revizyon\tKalemdeki Özel Şartlar\tAçıklama\tSatınalma Sorumlusu"
)


def test_parse_sheets_tsv_happy_path():
    sevk = "01.11.2026\n5 x 10 hafta\n10 x 35 hafta"
    row = (
        "\t\troketsan\tANT-DVI-ENC-hfkaha\t002525\t\t10\t\t\t\t"
        f'"{sevk}"\t100,00\t\t\t\t\t\t\t\t\t'
        "K ve P pozisyonları fiyata dahil değildir.\t\t"
    )
    text = HEADER + "\n" + row
    result = parse_sheets_tsv(text)
    assert len(result.rows) == 1
    r = result.rows[0]
    assert r.musteri_stok_kodu == "002525"
    assert r.antsis_urun_kodu == "ANT-DVI-ENC-hfkaha"
    assert "35 hafta" in r.teklif_sevk_tarihi
    assert r.birim_fiyat == "100,00"
    assert "K ve P" in r.kalemdeki_ozel_sartlar


def test_parse_sheets_tsv_empty_raises():
    try:
        parse_sheets_tsv("   ")
        assert False, "expected error"
    except SheetsTsvParseError as exc:
        assert "boş" in str(exc).lower()


def test_parse_sheets_tsv_missing_header():
    # Tanınmayan başlık → A–W konum parse; boşlar na
    text = "A\tB\tC\n1\t2\t3"
    result = parse_sheets_tsv(text)
    assert len(result.rows) == 2
    assert result.rows[0].firma == "C"  # kolon C = indeks 2
    assert result.rows[0].musteri_stok_kodu == "na"
    assert result.rows[1].firma == "3"


def test_skips_empty_rows_in_clipboard():
    text = HEADER + "\n\n\t\troketsan\tANT-X\t111\t\t1\t\t\t\t1 x 2 hafta\t10\n\n"
    matrix = parse_clipboard_tsv(text)
    assert first_row_is_header(matrix[0])
    assert len(matrix) == 2  # header + 1 data (empty skipped)


def test_rows_from_table_matrix_aw_positions():
    # A–W: E=stok, D=ürün, K=sevk, L=fiyat
    row = [""] * 23
    row[3] = "ANT-1"
    row[4] = "STOK1"
    row[10] = "3 x 5 hafta"
    row[11] = "12,00"
    result = rows_from_table_matrix([row, [""] * 23])
    assert len(result.rows) == 1
    assert result.rows[0].musteri_stok_kodu == "STOK1"
    assert result.rows[0].birim_fiyat == "12,00"
    # Boş hücreler na
    assert result.rows[0].firma == "na"


def test_empty_cells_become_na_and_row_kept():
    row = [""] * 23
    row[2] = "roketsan"  # C — yalnızca firma dolu; E boştu → na
    result = rows_from_table_matrix([row])
    assert len(result.rows) == 1
    assert result.rows[0].musteri_stok_kodu == "na"
    assert result.rows[0].antsis_urun_kodu == "na"
    assert result.rows[0].firma == "roketsan"


def test_data_only_paste_without_header():
    row = (
        "\t\troketsan\tANT-DVI\t002525\t\t10\t\t\t\t"
        "5 x 10 hafta\t100,00\t\t\t\t\t\t\t\t\t\t\t"
    )
    result = parse_sheets_tsv(row)
    assert len(result.rows) == 1
    assert result.rows[0].musteri_stok_kodu == "002525"
