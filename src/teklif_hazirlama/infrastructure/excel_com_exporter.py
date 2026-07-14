from __future__ import annotations

import re
from pathlib import Path

class ExcelComExporter:
    def is_available(self) -> bool:
        try:
            import win32com.client  # noqa: F401
            return True
        except ImportError:
            return False

    def export_pdf(
        self,
        xlsx_path: str | Path,
        pdf_path: str | Path,
        *,
        sheet_name: str | None = None,
    ) -> Path:
        import pythoncom
        import win32com.client

        xlsx = str(Path(xlsx_path).resolve())
        pdf = str(Path(pdf_path).resolve())
        Path(pdf).parent.mkdir(parents=True, exist_ok=True)

        pythoncom.CoInitialize()
        excel = None
        try:
            excel = win32com.client.DispatchEx("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            wb = excel.Workbooks.Open(xlsx)
            ws = self._resolve_worksheet(wb, sheet_name)
            self._configure_page_setup(ws)
            # 0 = xlTypePDF; IgnorePrintAreas=False → şablondaki print area kullanılır
            ws.ExportAsFixedFormat(
                0,
                pdf,
                0,
                True,
                False,
            )
            wb.Close(False)
        finally:
            if excel is not None:
                excel.Quit()
            pythoncom.CoUninitialize()
        return Path(pdf)

    def _resolve_worksheet(self, wb, sheet_name: str | None = None):
        if sheet_name:
            return wb.Worksheets(sheet_name)
        for name in ("Teklif", "Revize Teklif"):
            try:
                return wb.Worksheets(name)
            except Exception:
                continue
        return wb.Worksheets(1)

    def _configure_page_setup(self, ws) -> None:
        ps = ws.PageSetup
        existing = (ps.PrintArea or "").strip()
        if not existing:
            used = ws.UsedRange
            last_row = used.Row + used.Rows.Count - 1
            last_col = max(8, used.Column + used.Columns.Count - 1)
            end_col = self._col_letter(last_col)
            ps.PrintArea = f"$A$1:${end_col}${last_row}"

        self._autofit_print_area_rows(ws)

        app = ws.Application
        for attr, inches in (
            ("LeftMargin", 0.25),
            ("RightMargin", 0.25),
            ("TopMargin", 0.35),
            ("BottomMargin", 0.25),
            ("HeaderMargin", 0.15),
            ("FooterMargin", 0.15),
        ):
            try:
                setattr(ps, attr, app.InchesToPoints(inches))
            except Exception:
                pass

        # Tek sayfa: 1 genişlik × 1 yükseklik (Zoom kapalı olmalı)
        ps.Zoom = False
        ps.FitToPagesWide = 1
        ps.FitToPagesTall = 1
        try:
            ps.Orientation = 1  # xlPortrait
        except Exception:
            pass

    def _autofit_print_area_rows(self, ws) -> None:
        """PDF'de alt satırlar kesilmesin: print area içinde satır yüksekliklerini güncelle."""
        area = (ws.PageSetup.PrintArea or "").strip()
        if not area:
            return
        # 'Teklif'!$A$1:$H$46 veya $A$1:$H$46
        part = area.split("!")[-1]
        match = re.search(r"\$A\$1:\$H\$(\d+)", part, re.IGNORECASE)
        if not match:
            return
        last_row = int(match.group(1))
        try:
            ws.Range(f"$A$1:$H${last_row}").Rows.AutoFit()
        except Exception:
            pass

    @staticmethod
    def _col_letter(col: int) -> str:
        result = []
        while col > 0:
            col, rem = divmod(col - 1, 26)
            result.append(chr(65 + rem))
        return "".join(reversed(result))
