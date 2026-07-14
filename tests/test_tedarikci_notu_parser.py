from teklif_hazirlama.core.tedarikci_notu_parser import (
    append_aciklama_eki,
    build_teslim_tarihi_text,
    parse_tedarikci_notu,
)


def test_parse_urun_kodu_with_extra_spaces():
    text = "Teslim Süreleri :   ANT-DVI-ENC-623F - 29 adet T0+34 Hafta T0: Sipariş Onay Tarihi"
    result = parse_tedarikci_notu(text)
    assert result.urun_kodu == "ANT-DVI-ENC-623F"


def test_aciklama_eki():
    base = "ali ata bak / 002525"
    text = "Teslim Süreleri : X - 1 adet T0+1 Hafta T0: Sipariş Onay Tarihi K ve P pizisyonları fiyata dahil değildir."
    parsed = parse_tedarikci_notu(text)
    result = append_aciklama_eki(base, parsed.aciklama_eki)
    assert "K ve P" in result and "fiyata dahil" in result
    assert result.startswith(f"{base}\n( ")


def test_teslim_tarihi_birlestirme():
    parcalar = [
        "ANT-DVI-ENC-hfkaha - 29 adet T0+34 Hafta",
        "GSHG - 9 adet T0+12 Hafta",
    ]
    text = build_teslim_tarihi_text(parcalar)
    assert "T0: Sipariş Onay Tarihi" in text
    assert text.strip().endswith("T0: Sipariş Onay Tarihi")
    assert text.count("T0: Sipariş Onay Tarihi") == 1
    # Her ürün kodu kendi satırında
    assert "Hafta\nGSHG" in text
    assert "Hafta\nT0: Sipariş Onay Tarihi" in text


def test_teslim_tarihi_keeps_segments_on_one_line_per_code():
    parcalar = [
        "ANT5306 - 3 adet T0+14 Hafta, 2 adet T0+15 Hafta",
    ]
    text = build_teslim_tarihi_text(parcalar)
    assert "ANT5306 - 3 adet T0+14 Hafta, 2 adet T0+15 Hafta" in text
    assert "Hafta\n2 adet" not in text
    assert "T0: Sipariş Onay Tarihi" in text


def test_teslim_tarihi_rejoins_broken_multiline_same_code():
    parcalar = [
        "ANT5306 - 3 adet T0+14 Hafta\n2 adet T0+15 Hafta",
    ]
    text = build_teslim_tarihi_text(parcalar)
    assert "ANT5306 - 3 adet T0+14 Hafta, 2 adet T0+15 Hafta" in text
