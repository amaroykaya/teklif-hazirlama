from teklif_hazirlama.core.sevk_tarihi_parser import (
    build_tedarikci_notu,
    compute_temin_gun,
    parse_sevk_tarihi,
    parse_week_entries,
    resolve_teslim_entries_for_line,
    round_up_to_ten,
)


def test_parse_week_entries_multiline():
    text = "01.11.2026\n5 x 10 hafta\n5 x 24 hafta\n10 x 35 hafta"
    entries = parse_week_entries(text)
    assert [(e.adet, e.hafta) for e in entries] == [
        (5, 10),
        (5, 24),
        (10, 35),
    ]


def test_temin_35_weeks_to_250():
    entries = parse_week_entries("10 x 35 hafta")
    assert compute_temin_gun(entries) == 250


def test_temin_24_weeks_to_170():
    entries = parse_week_entries("5 x 24 hafta")
    assert compute_temin_gun(entries) == 170


def test_round_up_to_ten():
    assert round_up_to_ten(245) == 250
    assert round_up_to_ten(168) == 170
    assert round_up_to_ten(210) == 220  # 30*7 tam onluk → bir üst
    assert round_up_to_ten(250) == 260


def test_temin_30_weeks_to_220():
    from teklif_hazirlama.core.sevk_tarihi_parser import parse_t0_adet_entries

    entries = parse_t0_adet_entries(
        "ANT5307 - 2 adet T0+23 Hafta 3 adet T0+30 Hafta"
    )
    assert [(e.adet, e.hafta) for e in entries] == [(2, 23), (3, 30)]
    assert compute_temin_gun(entries) == 220


def test_build_tedarikci_notu_with_ozel():
    entries = parse_week_entries("5 x 10 hafta\n5 x 24 hafta\n10 x 35 hafta")
    text = build_tedarikci_notu(
        "ANT-DVI-ENC-hfkaha",
        entries,
        "K ve P pozisyonları fiyata dahil değildir.",
    )
    assert text.startswith("Teslim süresi : ANT-DVI-ENC-hfkaha - ")
    assert "5 adet T0+10 Hafta, 5 adet T0+24 Hafta, 10 adet T0+35 Hafta" in text
    assert text.endswith(
        "T0: Sipariş Onay Tarihi K ve P pozisyonları fiyata dahil değildir."
    )


def test_build_tedarikci_notu_without_ozel():
    entries = parse_week_entries("2 x 6 hafta")
    text = build_tedarikci_notu("ANT-0426", entries, "")
    assert text.endswith("T0: Sipariş Onay Tarihi")
    assert "T0: Sipariş Onay Tarihi " not in text + "X"  # no trailing space content


def test_parse_sevk_no_pattern_warns():
    result = parse_sevk_tarihi("01.11.2026")
    assert result.temin_gun is None
    assert result.warning


def test_resolve_teslim_same_code_two_lines_by_index():
    teslim = (
        "ANT-DUP - 5 adet T0+12 Hafta\n"
        "ANT-DUP - 5 adet T0+26 Hafta\n"
        "T0: Sipariş Onay Tarihi"
    )
    e0 = resolve_teslim_entries_for_line(teslim, "ANT-DUP", line_index=0)
    e1 = resolve_teslim_entries_for_line(teslim, "ANT-DUP", line_index=1)
    assert [(e.adet, e.hafta) for e in e0] == [(5, 12)]
    assert [(e.adet, e.hafta) for e in e1] == [(5, 26)]
    assert compute_temin_gun(e0) == 90
    assert compute_temin_gun(e1) == 190
