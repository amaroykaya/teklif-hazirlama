from openpyxl import Workbook, load_workbook

from teklif_hazirlama.core.excel_enricher import ExcelEnricher
from teklif_hazirlama.core.import_parser import ImportParser
from teklif_hazirlama.core.models import SheetsRow
from teklif_hazirlama.core.tedarikci_notu_parser import parse_tedarikci_notu


def _make_erp_workbook(path):
    wb = Workbook()
    ws = wb.active
    ws.append(["meta"])
    ws.append(
        [
            "Sıra",
            "Teklifte Bulun",
            "Stok Kodu",
            "Stok Tanımı",
            "Miktar",
            "Fiyat",
            "Satır Toplamı",
            "Tedarikçi Notu",
            "Temin Süresi (Takvim Günü)",
            "Garanti Süresi (Yıl)",
        ]
    )
    ws.append(
        [
            1,
            "Y",
            "002525",
            "Urun A",
            10,
            None,
            None,
            None,
            None,
            None,
        ]
    )
    ws.append(
        [
            2,
            "Y",
            "999999",
            "Only Excel",
            1,
            1,
            1,
            "Teslim Süreleri : OLD - 1 adet T0+1 Hafta T0: Sipariş Onay Tarihi",
            7,
            1,
        ]
    )
    wb.save(path)
    wb.close()


def test_enrich_fills_by_row_order(tmp_path):
    src = tmp_path / "QR075313.xlsx"
    _make_erp_workbook(src)
    sheets = [
        SheetsRow(
            musteri_stok_kodu="herhangi",
            antsis_urun_kodu="ANT-DVI-ENC-hfkaha",
            teklif_sevk_tarihi="5 x 10 hafta\n10 x 35 hafta",
            birim_fiyat="100,50",
            kalemdeki_ozel_sartlar="K ve P dahil değil.",
        ),
        SheetsRow(
            musteri_stok_kodu="na",
            antsis_urun_kodu="na",
            teklif_sevk_tarihi="na",
            birim_fiyat="na",
        ),
    ]
    out = tmp_path / "out"
    result = ExcelEnricher().enrich(src, sheets, output_dir=out)
    assert result.matched == 2

    wb = load_workbook(result.enriched_path, data_only=True)
    ws = wb.active
    assert ws.cell(3, 6).value == 100.5  # 1. satır Fiyat
    assert ws.cell(3, 9).value == 250
    assert ws.cell(3, 10).value == 1.0
    assert "Teslim süresi : ANT-DVI-ENC-hfkaha" in ws.cell(3, 8).value
    # 2. satır na
    assert ws.cell(4, 6).value == "na"
    assert ws.cell(4, 8).value == "na"
    assert ws.cell(4, 9).value == "na"
    wb.close()

    lines, errors = ImportParser().parse(result.enriched_path)
    assert errors == []
    assert lines[0].ants_is_urun_kodu == "ANT-DVI-ENC-hfkaha"
    assert lines[1].ants_is_urun_kodu == "na"


def test_enrich_extra_excel_rows_get_na(tmp_path):
    src = tmp_path / "QR1.xlsx"
    _make_erp_workbook(src)
    sheets = [
        SheetsRow(
            musteri_stok_kodu="x",
            antsis_urun_kodu="ANT-X",
            teklif_sevk_tarihi="1 x 10 hafta",
            birim_fiyat="9,00",
        )
    ]
    result = ExcelEnricher().enrich(src, sheets, output_dir=tmp_path / "o")
    assert result.matched == 1
    assert any("fazla satır" in w for w in result.warnings)
    wb = load_workbook(result.enriched_path, data_only=True)
    assert wb.active.cell(4, 6).value == "na"
    wb.close()


def test_parse_tedarikci_notu_accepts_singular_sure():
    text = (
        "Teslim süresi : ANT-DVI-ENC-hfkaha - 5 adet T0+10 Hafta, 10 adet T0+35 Hafta "
        "T0: Sipariş Onay Tarihi K ve P pozisyonları fiyata dahil değildir."
    )
    result = parse_tedarikci_notu(text)
    assert result.urun_kodu == "ANT-DVI-ENC-hfkaha"
    assert "5 adet T0+10 Hafta" in result.teslim_suresi_parcasi
    assert "K ve P" in result.aciklama_eki
