from decimal import Decimal

from teklif_hazirlama.core.models import QuoteLine, SheetsRow
from teklif_hazirlama.core.sheets_quote_mapper import (
    apply_sheets_rows,
    merge_excel_into_sheets_lines,
    sheets_row_to_quote_line,
)


def test_sheets_row_to_quote_line_basic():
    sheet = SheetsRow(
        musteri_stok_kodu="002525",
        antsis_urun_kodu="ANT5307",
        teklif_sevk_tarihi="2 x 23 hafta\n3 x 30 hafta",
        birim_fiyat="100,50",
        kalemdeki_ozel_sartlar="K dahil değil",
        adet="5",
        proje_tanimi="Urun A",
        raw={
            "aciklama": "BU-V-KULLANILMAMALI",
            "toplam fiyat": "502,50",
            "antsis teklif no": "RKTSN-2607-13",
            "musteri teklif numarasi": "QR075313",
        },
    )
    line = sheets_row_to_quote_line(sheet, 1)
    assert line.adet == 5
    assert line.ants_is_urun_kodu == "ANT5307"
    assert line.birim_fiyat == Decimal("100.50")
    assert line.toplam_fiyat == Decimal("502.50")
    assert "ANT5307" in line.teslim_suresi_parcasi
    assert "T0+30" in line.teslim_suresi_parcasi
    # Açıklama = F Proje Tanımı (+ isteğe U); V ve stok kodu yok
    assert line.aciklama == "Urun A\n( K dahil değil )"
    assert "002525" not in line.aciklama
    assert "BU-V-KULLANILMAMALI" not in line.aciklama


def test_apply_sheets_fills_teslim_istek_and_teklif_no():
    rows = [
        SheetsRow(
            musteri_stok_kodu="1",
            antsis_urun_kodu="A1",
            teklif_sevk_tarihi="1 x 10 hafta",
            birim_fiyat="10",
            adet="1",
            proje_tanimi="Proje X",
            raw={
                "antsis teklif no": "RKTSN-1",
                "musteri teklif numarasi": "ISTEK-99",
            },
        )
    ]
    result = apply_sheets_rows(rows)
    assert len(result.quote_lines) == 1
    assert result.quote_lines[0].aciklama == "Proje X"
    assert "A1" in result.teslim_tarihi_text
    assert result.teklif_no == "RKTSN-1"
    assert result.istek_no == "ISTEK-99"
    assert result.enrich_sheets_rows == rows
    assert not hasattr(result, "ozel_sartlar") or not getattr(result, "ozel_sartlar", None)


def test_apply_sheets_revise_pairs_by_stok_and_prices():
    r1 = SheetsRow(
        musteri_stok_kodu="00354911",
        antsis_urun_kodu="ANT5307",
        teklif_sevk_tarihi="1 x 10 hafta",
        birim_fiyat="100,00",
        adet="2",
        proje_tanimi="Eski aciklama",
        raw={"revizyonu": "1", "musteri teklif numarasi": "QR1"},
    )
    r2 = SheetsRow(
        musteri_stok_kodu="00354911",
        antsis_urun_kodu="ANT5307",
        teklif_sevk_tarihi="2 x 20 hafta",
        birim_fiyat="80,00",
        adet="5",
        proje_tanimi="Yeni urun",
        kalemdeki_ozel_sartlar="Not",
        raw={
            "revizyonu": "2",
            "antsis teklif no": "RKTSN-R",
            "musteri teklif numarasi": "QR1",
        },
    )
    result = apply_sheets_rows([r1, r2], revise=True)
    assert len(result.quote_lines) == 1
    line = result.quote_lines[0]
    assert line.adet == 5
    assert line.birim_fiyat == Decimal("100.00")
    assert line.indirimli_birim_fiyat == Decimal("80.00")
    assert line.toplam_fiyat == Decimal("400.00")  # 80 * 5
    assert "Yeni urun" in line.aciklama
    assert "T0+20" in line.teslim_suresi_parcasi
    assert result.form_revizyon == "1"
    assert len(result.enrich_sheets_rows) == 1
    assert result.enrich_sheets_rows[0] is r2
    # İndirim % = 1 - 80/100 = 0.20
    assert (Decimal("1") - (line.indirimli_birim_fiyat / line.birim_fiyat)) == Decimal(
        "0.2"
    )


def test_apply_sheets_revise_warns_without_r1():
    only_current = SheetsRow(
        musteri_stok_kodu="100",
        antsis_urun_kodu="A",
        teklif_sevk_tarihi="1 x 5 hafta",
        birim_fiyat="50",
        adet="1",
        proje_tanimi="X",
        raw={"revizyonu": "2"},
    )
    result = apply_sheets_rows([only_current], revise=True)
    assert len(result.quote_lines) == 1
    assert result.quote_lines[0].birim_fiyat == Decimal("0")
    assert result.quote_lines[0].indirimli_birim_fiyat == Decimal("50")
    assert any("Revizyonu=1" in w for w in result.warnings)


def test_apply_sheets_revise_five_r1_three_current():
    def row(stok: str, price: str, rev: str, adet: str = "1") -> SheetsRow:
        return SheetsRow(
            musteri_stok_kodu=stok,
            antsis_urun_kodu=f"A-{stok}",
            teklif_sevk_tarihi="1 x 10 hafta",
            birim_fiyat=price,
            adet=adet,
            proje_tanimi=f"P-{stok}-R{rev}",
            raw={"revizyonu": rev},
        )

    rows = [
        row("A", "10", "1"),
        row("B", "20", "1"),
        row("C", "30", "1"),
        row("D", "40", "1"),
        row("E", "50", "1"),
        row("A", "9", "2", adet="2"),
        row("C", "25", "2", adet="3"),
        row("D", "35", "2"),
    ]
    result = apply_sheets_rows(rows, revise=True)
    assert len(result.quote_lines) == 3
    by_stok = {line.stok_kodu: line for line in result.quote_lines}
    assert by_stok["A"].birim_fiyat == Decimal("10")
    assert by_stok["A"].indirimli_birim_fiyat == Decimal("9")
    assert by_stok["A"].adet == 2
    assert by_stok["C"].birim_fiyat == Decimal("30")
    assert by_stok["C"].indirimli_birim_fiyat == Decimal("25")
    assert by_stok["D"].birim_fiyat == Decimal("40")
    assert any("2 satırın güncelde karşılığı yok" in w for w in result.warnings)


def test_apply_sheets_revise_duplicate_stok_by_order():
    rows = [
        SheetsRow(
            musteri_stok_kodu="SAME",
            antsis_urun_kodu="X1",
            teklif_sevk_tarihi="1 x 1 hafta",
            birim_fiyat="100",
            adet="1",
            proje_tanimi="R1-first",
            raw={"revizyonu": "1"},
        ),
        SheetsRow(
            musteri_stok_kodu="SAME",
            antsis_urun_kodu="X2",
            teklif_sevk_tarihi="1 x 1 hafta",
            birim_fiyat="200",
            adet="1",
            proje_tanimi="R1-second",
            raw={"revizyonu": "1"},
        ),
        SheetsRow(
            musteri_stok_kodu="SAME",
            antsis_urun_kodu="Y1",
            teklif_sevk_tarihi="1 x 2 hafta",
            birim_fiyat="80",
            adet="1",
            proje_tanimi="Cur-first",
            raw={"revizyonu": "2"},
        ),
        SheetsRow(
            musteri_stok_kodu="SAME",
            antsis_urun_kodu="Y2",
            teklif_sevk_tarihi="1 x 3 hafta",
            birim_fiyat="150",
            adet="1",
            proje_tanimi="Cur-second",
            raw={"revizyonu": "2"},
        ),
    ]
    result = apply_sheets_rows(rows, revise=True)
    assert len(result.quote_lines) == 2
    assert result.quote_lines[0].birim_fiyat == Decimal("100")
    assert result.quote_lines[0].indirimli_birim_fiyat == Decimal("80")
    assert result.quote_lines[1].birim_fiyat == Decimal("200")
    assert result.quote_lines[1].indirimli_birim_fiyat == Decimal("150")
    assert any("sırayla eşlendi" in w for w in result.warnings)


def test_pair_excel_duplicate_stok_by_order():
    sheets = [
        QuoteLine(
            row_number=1,
            adet=1,
            ants_is_urun_kodu="A",
            aciklama="same",
            stok_aciklama="same",
            birim_fiyat=Decimal("1"),
            toplam_fiyat=Decimal("1"),
            stok_kodu="DUP",
        ),
        QuoteLine(
            row_number=2,
            adet=2,
            ants_is_urun_kodu="B",
            aciklama="same",
            stok_aciklama="same",
            birim_fiyat=Decimal("2"),
            toplam_fiyat=Decimal("4"),
            stok_kodu="DUP",
        ),
    ]
    excel = [
        QuoteLine(
            row_number=1,
            adet=1,
            ants_is_urun_kodu="A",
            aciklama="same / DUP",
            stok_aciklama="same / DUP",
            birim_fiyat=Decimal("9"),
            toplam_fiyat=Decimal("9"),
            stok_kodu="DUP",
        ),
        QuoteLine(
            row_number=2,
            adet=2,
            ants_is_urun_kodu="B",
            aciklama="same / DUP",
            stok_aciklama="same / DUP",
            birim_fiyat=Decimal("8"),
            toplam_fiyat=Decimal("16"),
            stok_kodu="DUP",
        ),
    ]
    merged = merge_excel_into_sheets_lines(
        sheets, excel, sheets_istek_no="X", excel_istek_no="X"
    )
    assert merged.quote_lines[0].adet == 1
    assert merged.quote_lines[0].ants_is_urun_kodu == "A"
    assert merged.quote_lines[1].adet == 2
    assert merged.quote_lines[1].ants_is_urun_kodu == "B"
    assert not any("karşılığı yok" in w for w in merged.warnings)


def test_merge_sheets_wins_on_conflict():
    sheets = [
        QuoteLine(
            row_number=1,
            adet=5,
            ants_is_urun_kodu="SHEETS-CODE",
            aciklama="Proje A",
            stok_aciklama="Proje A",
            birim_fiyat=Decimal("100"),
            toplam_fiyat=Decimal("500"),
            stok_kodu="002525",
        )
    ]
    excel = [
        QuoteLine(
            row_number=3,
            adet=10,
            ants_is_urun_kodu="EXCEL-CODE",
            aciklama="Urun A / 002525",
            stok_aciklama="Urun A / 002525",
            birim_fiyat=Decimal("90"),
            toplam_fiyat=Decimal("900"),
            stok_kodu="002525",
        )
    ]
    merged = merge_excel_into_sheets_lines(
        sheets,
        excel,
        sheets_istek_no="QR075313",
        excel_istek_no="QR075999",
    )
    assert merged.quote_lines[0].adet == 5
    assert merged.quote_lines[0].birim_fiyat == Decimal("100")  # fiyat doldurulmaz/çelişmez
    assert merged.quote_lines[0].ants_is_urun_kodu == "SHEETS-CODE"
    assert merged.quote_lines[0].aciklama == "Proje A"  # Sheets kazanır
    kinds = " ".join(merged.conflicts)
    assert "Adet" in kinds
    assert "Antsis" in kinds
    assert "Açıklama" in kinds
    assert "İstek No" in kinds
    assert "Birim fiyat" not in kinds
    assert "Toplam" not in kinds


def test_merge_row_count_conflict():
    sheets = [
        QuoteLine(
            row_number=1,
            adet=1,
            ants_is_urun_kodu="A1",
            aciklama="A",
            birim_fiyat=Decimal("1"),
            toplam_fiyat=Decimal("1"),
            stok_kodu="1",
        ),
        QuoteLine(
            row_number=2,
            adet=1,
            ants_is_urun_kodu="A2",
            aciklama="B",
            birim_fiyat=Decimal("1"),
            toplam_fiyat=Decimal("1"),
            stok_kodu="2",
        ),
    ]
    excel = [
        QuoteLine(
            row_number=1,
            adet=1,
            ants_is_urun_kodu="A1",
            aciklama="A",
            birim_fiyat=Decimal("1"),
            toplam_fiyat=Decimal("1"),
            stok_kodu="1",
        ),
    ]
    merged = merge_excel_into_sheets_lines(sheets, excel)
    assert any("Satır sayısı" in c for c in merged.conflicts)
    assert len(merged.quote_lines) == 2


def test_merge_does_not_conflict_on_price_only():
    sheets = [
        QuoteLine(
            row_number=1,
            adet=5,
            ants_is_urun_kodu="SAME",
            aciklama="Aynı",
            stok_aciklama="Aynı",
            birim_fiyat=Decimal("100"),
            toplam_fiyat=Decimal("500"),
            stok_kodu="002525",
        )
    ]
    excel = [
        QuoteLine(
            row_number=1,
            adet=5,
            ants_is_urun_kodu="SAME",
            aciklama="Aynı / 002525",
            stok_aciklama="Aynı / 002525",
            birim_fiyat=Decimal("1"),
            toplam_fiyat=Decimal("5"),
            stok_kodu="002525",
        )
    ]
    merged = merge_excel_into_sheets_lines(
        sheets, excel, sheets_istek_no="X", excel_istek_no="X"
    )
    assert merged.conflicts == []


def test_merge_aciklama_same_text_no_false_conflict():
    """Sheets proje zaten '… / stok' içerir; Excel aynı metni stok ile birleştirir."""
    desc = "RF COMPONENT, DIRECTIVE AIRBORNE ANTENNA, ANT_1029 / 00354911"
    sheets = [
        QuoteLine(
            row_number=1,
            adet=2,
            ants_is_urun_kodu="ANT5307",
            aciklama=desc,
            stok_aciklama=desc,
            birim_fiyat=Decimal("10"),
            toplam_fiyat=Decimal("20"),
            stok_kodu="00354911",
        )
    ]
    excel = [
        QuoteLine(
            row_number=1,
            adet=2,
            ants_is_urun_kodu="ANT5307",
            aciklama=f"{desc} / 00354911",
            stok_aciklama=f"{desc} / 00354911",
            birim_fiyat=Decimal("10"),
            toplam_fiyat=Decimal("20"),
            stok_kodu="00354911",
        )
    ]
    merged = merge_excel_into_sheets_lines(
        sheets, excel, sheets_istek_no="QR083145", excel_istek_no="QR083145"
    )
    assert not any("Açıklama" in c for c in merged.conflicts)


def test_merge_aciklama_real_difference_still_conflicts():
    sheets = [
        QuoteLine(
            row_number=1,
            adet=1,
            ants_is_urun_kodu="A",
            aciklama="Urun X",
            stok_aciklama="Urun X",
            birim_fiyat=Decimal("1"),
            toplam_fiyat=Decimal("1"),
            stok_kodu="111",
        )
    ]
    excel = [
        QuoteLine(
            row_number=1,
            adet=1,
            ants_is_urun_kodu="A",
            aciklama="Urun Y / 111",
            stok_aciklama="Urun Y / 111",
            birim_fiyat=Decimal("1"),
            toplam_fiyat=Decimal("1"),
            stok_kodu="111",
        )
    ]
    merged = merge_excel_into_sheets_lines(
        sheets, excel, sheets_istek_no="X", excel_istek_no="X"
    )
    assert any("Açıklama" in c for c in merged.conflicts)
    assert any("İstek No eşleşti" in m for m in merged.matches)
    assert any("Satır sayısı eşleşti" in m for m in merged.matches)


def test_merge_reports_matches():
    sheets = [
        QuoteLine(
            row_number=1,
            adet=2,
            ants_is_urun_kodu="A",
            aciklama="Urun A",
            stok_aciklama="Urun A",
            birim_fiyat=Decimal("1"),
            toplam_fiyat=Decimal("2"),
            stok_kodu="100",
        )
    ]
    excel = [
        QuoteLine(
            row_number=1,
            adet=2,
            ants_is_urun_kodu="A",
            aciklama="Urun A / 100",
            stok_aciklama="Urun A / 100",
            birim_fiyat=Decimal("9"),
            toplam_fiyat=Decimal("18"),
            stok_kodu="100",
        )
    ]
    merged = merge_excel_into_sheets_lines(
        sheets, excel, sheets_istek_no="QR1", excel_istek_no="QR1"
    )
    assert merged.conflicts == []
    assert "İstek No eşleşti (QR1)" in merged.matches
    assert "Satır sayısı eşleşti (1)" in merged.matches
    assert any(m.startswith("Açıklama eşleşti") for m in merged.matches)
