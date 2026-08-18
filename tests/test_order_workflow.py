from openpyxl import Workbook

from teklif_hazirlama.application.order_workflow import OrderWorkflow, build_aciklama_text
from teklif_hazirlama.core.order_clipboard import (
    build_order_sheets_html,
    build_order_sheets_tsv,
)
from teklif_hazirlama.core.quality_highlight import (
    format_quality_html,
    is_highlight_quality_code,
)
from teklif_hazirlama.core.order_excel_parser import (
    OrderExcelParser,
    extract_antsis_parca_no,
    normalize_uretim_yeri,
    siparis_satir_no_to_ss,
)
from teklif_hazirlama.core.order_pdf_parser import parse_order_pdf_text


def test_order_excel_parser_and_workflow(tmp_path):
    path = tmp_path / "siparis.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(
        [
            "Satır No",
            "Stok Kodu",
            "Stok Tanımı",
            "Miktar",
            "Birim Fiyat",
            "Teknik Resim",
            "Ürün Revizyonu",
            "Proje Kodu",
            "Üretim Yeri",
        ]
    )
    ws.append(
        [
            "5-1",
            "236425",
            "Govde ANT-ABC-01",
            3,
            12.5,
            "TR-01",
            "R2",
            "PRJ-9",
            "161 - Roketsan Elmadağ",
        ]
    )
    wb.save(path)

    pdf_text = """
    SIPARIS TARIHI/ PO DATE
    19/12/2025
    SIPARIS EMRI NO / PURCHASE ORDER NO
    PO-7788
    SATIN ALMA SORUMLUSU/ BUYER
    Ada Lovelace
    SS5 23/01/2026 K1 K2
    """
    parser = OrderExcelParser()
    rows = parser.parse(path)
    assert len(rows) == 1
    assert rows[0].stok_kodu == "236425"

    header, pdf_lines = parse_order_pdf_text(pdf_text)
    assert header.siparis_tarihi == "19.12.2025"
    assert header.siparis_numarasi == "PO-7788"
    assert pdf_lines["SS5"].planlanan_sevk_tarihi == "23.01.2026"

    workflow = OrderWorkflow()
    workflow.pdf_parser.parse = lambda _path: (header, pdf_lines)  # type: ignore[method-assign]
    merged = workflow.build_rows(excel_path=path, pdf_path="dummy.pdf", firma="Roketsan")
    assert len(merged) == 1
    row = merged[0]
    assert row.antsis_parca_no == "ANT-ABC-01"
    assert row.musteri_parca_no == "00236425"
    assert row.proje.endswith("SS5")
    assert row.siparis_tarihi == "19.12.2025"
    assert row.planlanan_sevk_tarihi == "23.01.2026"
    assert row.aciklama == build_aciklama_text(
        buyer="Ada Lovelace",
        kalite_provizyonlari="",
        sevk_yeri="Elmadağ",
    )
    tsv = build_order_sheets_tsv(merged)
    assert '"Sorumlu: Ada Lovelace\nKalite Provizyonları: \nSevk yeri : Elmadağ"' in tsv


def test_helpers_normalize_location_and_ss():
    assert normalize_uretim_yeri("161 - Roketsan Elmadağ") == "Elmadağ"
    assert siparis_satir_no_to_ss("13-1") == "SS13"


def test_extract_antsis_parca_no_underscore_and_hyphen():
    assert (
        extract_antsis_parca_no("RF COMPONENT, DIRECTIVE AIRBORNE ANTENNA, ANT_1029")
        == "ANT_1029"
    )
    assert extract_antsis_parca_no("BLADE AIRBORNE ANTENNA, ANT_0822") == "ANT_0822"
    assert extract_antsis_parca_no("Govde ANT-ABC-01") == "ANT-ABC-01"
    assert extract_antsis_parca_no("ANTENNA only") == ""


def test_pdf_quality_with_and_without_rev():
    """REV varsa 5. alan, yoksa parça no sonrası kalite; açıklama kalite olmaz."""
    with_rev = """
    SIPARIS TARIHI/ PO DATE
    19/12/2025
    SIPARIS EMRI NO / PURCHASE ORDER NO
    PO341614
    SATIN ALMA SORUMLUSU/ BUYER
    Ada Lovelace
    SS5 SV1 00236425 D01 GP2,L,V,G,GT,C,CC,M
    M,P,K
    IHA PLATFORMU
    2 Adet 1.600,000 USD 3.200,00 23/01/2026 Elmadag
    """
    _, lines = parse_order_pdf_text(with_rev)
    assert lines["SS5"].kalite_provizyonlari == "GP2,L,V,G,GT,C,CC,M M,P,K"
    assert lines["SS5"].planlanan_sevk_tarihi == "23.01.2026"

    without_rev = """
    SIPARIS TARIHI/ PO DATE
    13/08/2026
    SIPARIS EMRI NO / PURCHASE ORDER NO
    PO383369
    KALITE GUVENCE SARTLARI/ QUALITY ASSURANCE PROVISIONS
    SS1 SV1 00354911 GP2,L,V,G,XX
    RF COMPONENT,
    DIRECTIVE AIRBORNE ANTENNA, ANT_1029
    PLM:00354911 Rev. -
    5 Adet 1.680,000 USD 8.400,00 12/09/2026 Elmadag
    SS3 SV1 00354909 GP2,L,V,G,XX
    RF COMPONENT, BLADE
    AIRBORNE ANTENNA,
    5 Adet 1.680,000 USD 8.400,00 02/09/2026 Elmadag
    """
    _, lines2 = parse_order_pdf_text(without_rev)
    assert lines2["SS1"].kalite_provizyonlari == "GP2,L,V,G,XX"
    assert "RF" not in lines2["SS1"].kalite_provizyonlari
    assert lines2["SS1"].planlanan_sevk_tarihi == "12.09.2026"
    assert lines2["SS3"].kalite_provizyonlari == "GP2,L,V,G,XX"
    assert "BLADE" not in lines2["SS3"].kalite_provizyonlari


def test_pdf_quality_glued_to_description():
    """PDF extract bazen kaliteyi açıklamaya yapıştırır (MMNETHERNET)."""
    text = """
    SIPARIS TARIHI/ PO DATE
    19/12/2025
    SIPARIS EMRI NO / PURCHASE ORDER NO
    PO341614
    SS11 SV1 00228546 D01 GP2,GT,L,V,G,K,MMNETHERNET
    10 Adet 1.800,000 USD 18.000,00 03/04/2026 Elmadag
    """
    _, lines = parse_order_pdf_text(text)
    assert lines["SS11"].kalite_provizyonlari == "GP2,GT,L,V,G,K,MMN"


def test_highlight_quality_codes():
    assert is_highlight_quality_code("C")
    assert is_highlight_quality_code("DKG")
    assert is_highlight_quality_code("tr")
    assert not is_highlight_quality_code("GP2")
    assert not is_highlight_quality_code("CC")
    assert not is_highlight_quality_code("GT")

    html = format_quality_html("GP2,L,V,G,GT,C,CC,M,P,K")
    assert '<span style="color:#cc0000;font-weight:bold">C</span>' in html
    assert '<span style="color:#cc0000;font-weight:bold">P</span>' in html
    assert '<span style="color:#cc0000;font-weight:bold">K</span>' in html
    assert "CC</span>" not in html  # CC kritik listede değil
    assert "GP2" in html and "font-weight:bold\">GP2" not in html

    sheet_html = build_order_sheets_html([])
    assert "<table" in sheet_html
