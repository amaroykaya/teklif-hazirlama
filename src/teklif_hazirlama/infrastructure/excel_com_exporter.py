from __future__ import annotations

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
        """
        Önce üretilmiş Excel'i açar; sayfa ayarını
        genişlik=1 sayfa × yükseklik=1 sayfa yapıp PDF'e aktarır.
        """
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
            excel.ScreenUpdating = False
            wb = excel.Workbooks.Open(xlsx)
            ws = self._resolve_worksheet(wb, sheet_name)
            self._configure_fit_one_page(excel, ws)
            # 0 = xlTypePDF; IgnorePrintAreas=False → print area kullanılır
            ws.ExportAsFixedFormat(
                Type=0,
                Filename=pdf,
                Quality=0,
                IncludeDocProperties=True,
                IgnorePrintAreas=False,
                OpenAfterPublish=False,
            )
            wb.Close(False)
        finally:
            if excel is not None:
                try:
                    excel.ScreenUpdating = True
                except Exception:
                    pass
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

    def _configure_fit_one_page(self, excel, ws) -> None:
        """
        Zoom kapalı + FitToPages 1×1.
        PrintCommunication olmadan Excel COM bu ayarları sık sık yok sayar.
        """
        ps = ws.PageSetup

        # Print area: yoksa UsedRange (en az A:H)
        existing = (ps.PrintArea or "").strip()
        if not existing:
            used = ws.UsedRange
            last_row = used.Row + used.Rows.Count - 1
            last_col = max(8, used.Column + used.Columns.Count - 1)
            end_col = self._col_letter(last_col)
            print_area = f"$A$1:${end_col}${last_row}"
        else:
            print_area = existing

        try:
            excel.PrintCommunication = False
        except Exception:
            pass

        try:
            ps.PrintArea = print_area
            for attr, inches in (
                ("LeftMargin", 0.25),
                ("RightMargin", 0.25),
                ("TopMargin", 0.35),
                ("BottomMargin", 0.25),
                ("HeaderMargin", 0.15),
                ("FooterMargin", 0.15),
            ):
                try:
                    setattr(ps, attr, excel.InchesToPoints(inches))
                except Exception:
                    pass

            try:
                ps.Orientation = 1  # xlPortrait
            except Exception:
                pass
            try:
                ps.PaperSize = 9  # xlPaperA4
            except Exception:
                pass

            # Kritik: Zoom False olmadan FitToPages yok sayılır
            ps.Zoom = False
            ps.FitToPagesWide = 1
            ps.FitToPagesTall = 1
        finally:
            try:
                excel.PrintCommunication = True
            except Exception:
                pass

        # Doğrulama — COM bazen Zoom'u geri alır; ikinci kez zorla
        try:
            excel.PrintCommunication = False
            ps.Zoom = False
            ps.FitToPagesWide = 1
            ps.FitToPagesTall = 1
        finally:
            try:
                excel.PrintCommunication = True
            except Exception:
                pass

    @staticmethod
    def _col_letter(col: int) -> str:
        result = []
        while col > 0:
            col, rem = divmod(col - 1, 26)
            result.append(chr(65 + rem))
        return "".join(reversed(result))
