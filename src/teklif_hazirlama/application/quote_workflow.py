from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from teklif_hazirlama.core.excel_enricher import ExcelEnrichError, ExcelEnricher
from teklif_hazirlama.core.excel_ui_sync import sync_quote_lines_to_import_excel
from teklif_hazirlama.core.import_parser import ImportParser
from teklif_hazirlama.core.models import QuoteHeader, QuoteLine, SheetsRow
from teklif_hazirlama.core.quote_engine import QuoteEngine
from teklif_hazirlama.core.sheets_clipboard import (
    build_istek_sheets_tsv,
    build_sheets_tsv,
    format_teklif_no_with_revizyon,
)
from teklif_hazirlama.core.sheets_quote_mapper import (
    SheetsApplyResult,
    apply_sheets_rows,
    merge_excel_into_sheets_lines,
)
from teklif_hazirlama.core.template_filler import TemplateFiller, output_basename
from teklif_hazirlama.core.tedarikci_notu_parser import build_teslim_tarihi_text
from teklif_hazirlama.infrastructure.excel_com_exporter import ExcelComExporter
from teklif_hazirlama.infrastructure.storage import CustomerRepository, LocalStore


def preview_dir() -> Path:
    path = (
        Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
        / "TeklifHazirlama"
        / "preview"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def cleanup_preview_files(*, keep: Path | None = None) -> None:
    """Önizleme klasöründeki Excel'leri sil (Excel açıksa kilitli olan kalabilir)."""
    directory = preview_dir()
    keep_resolved = keep.resolve() if keep is not None else None
    for path in directory.glob("*.xlsx"):
        if keep_resolved is not None and path.resolve() == keep_resolved:
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


@dataclass
class QuoteRequest:
    customer_code: str
    teklif_no: str
    hitap_kisi: str
    hitap_adres_satirlari: list[str]
    hitap_telefon: str
    hazirlayan: str
    teslimat: str
    teslimat_sekli: str
    odeme_sekli: str
    import_excel_path: str
    ozel_sartlar: list[str]
    output_dir: str
    sartlar: list[str] | None = None
    tarih: date | None = None
    revizyon: str = ""
    # Orijinal ERP dosya adı (İstek No); dolu Excel farklı klasörde olabilir
    source_excel_path: str = ""
    sheets_rows: list[SheetsRow] = field(default_factory=list)
    is_revise: bool = False
    # UI'dan gelen / import sonrası doldurulan; boşsa dosya adından türetilir
    istek_no: str = ""
    teslim_tarihi_text: str = ""
    # UI tablosundan gelen satırlar; doluysa generate bunları kullanır
    quote_lines: list[QuoteLine] = field(default_factory=list)


@dataclass
class QuoteResult:
    document_path: Path
    pdf_path: Path | None
    warnings: list[str]
    enriched_excel_path: Path | None = None
    original_excel_path: Path | None = None
    output_folder: Path | None = None


@dataclass
class EnrichImportResult:
    enriched_path: Path
    warnings: list[str]
    filled_rows: int
    istek_no: str = ""
    teslim_tarihi_text: str = ""
    quote_lines: list[QuoteLine] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    matches: list[str] = field(default_factory=list)
    form_revizyon: str = ""


class QuoteWorkflow:
    def __init__(self):
        self.customers = CustomerRepository()
        self.store = LocalStore()
        self.import_parser = ImportParser()
        self.engine = QuoteEngine()
        self.filler = TemplateFiller()
        self.exporter = ExcelComExporter()
        self.enricher = ExcelEnricher()

    def apply_sheets(
        self, sheets_rows: list[SheetsRow], *, revise: bool = False
    ) -> SheetsApplyResult:
        """Sheets yapıştırılınca UI'yi doldur (master kaynak)."""
        return apply_sheets_rows(sheets_rows, revise=revise)

    def enrich_import(
        self,
        source_excel: str | Path,
        sheets_rows: list[SheetsRow],
        *,
        revise: bool = False,
    ) -> EnrichImportResult:
        """
        Import Excel: doldurulmuş kopya üretir; UI satırları Sheets master +
        Excel eksik doldurma ile birleştirilir. Çelişkide Sheets kazanır.
        """
        if not sheets_rows:
            raise ValueError(
                "Önce Google satırlarını yapıştırın; Excel seçilince eksikler "
                "tamamlanır ve karşılaştırma yapılır."
            )

        sheets_applied = apply_sheets_rows(sheets_rows, revise=revise)
        enrich_rows = sheets_applied.enrich_sheets_rows or list(sheets_rows)

        dest_dir = (
            Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
            / "TeklifHazirlama"
            / "enrich_cache"
        )
        dest_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = self.enricher.enrich(
                source_excel, enrich_rows, output_dir=dest_dir
            )
        except ExcelEnrichError as exc:
            raise ValueError(str(exc)) from exc

        warnings = list(result.warnings)
        warnings.extend(sheets_applied.warnings)
        warnings.insert(
            0,
            f"{result.matched} satır için doldurulmuş Excel üretildi "
            "(Fiyat, Temin, Tedarikçi Notu, Garanti).",
        )

        excel_lines: list[QuoteLine] = []
        try:
            excel_lines, parse_warnings = self.import_parser.parse(
                source_excel, mode="istek"
            )
            warnings.extend(parse_warnings)
        except Exception as exc:
            warnings.append(f"Orijinal Excel satırları okunamadı: {exc}")

        excel_istek_no = self.import_parser.istek_no_from_path(source_excel)
        merged = merge_excel_into_sheets_lines(
            sheets_applied.quote_lines,
            excel_lines,
            sheets_istek_no=sheets_applied.istek_no,
            excel_istek_no=excel_istek_no,
        )
        warnings.extend(merged.warnings)

        # Revize: Excel birleştirmesi indirimli/eski birim fiyatı silmesin.
        # Aynı stok birden fazla satırda olabilir → satır sırasıyla eşle (stok dict değil).
        if revise:
            fixed: list[QuoteLine] = []
            for i, line in enumerate(merged.quote_lines):
                data = line.model_dump()
                if i < len(sheets_applied.quote_lines):
                    src = sheets_applied.quote_lines[i]
                    if src.indirimli_birim_fiyat is not None:
                        data["indirimli_birim_fiyat"] = src.indirimli_birim_fiyat
                    if src.birim_fiyat > 0:
                        data["birim_fiyat"] = src.birim_fiyat
                    indirimli = data.get("indirimli_birim_fiyat")
                    if indirimli is not None and data.get("adet"):
                        data["toplam_fiyat"] = (
                            Decimal(str(indirimli)) * Decimal(data["adet"])
                        ).quantize(Decimal("0.01"))
                fixed.append(QuoteLine(**data))
            merged_lines = fixed
        else:
            merged_lines = merged.quote_lines

        istek_no = sheets_applied.istek_no
        if not istek_no:
            istek_no = excel_istek_no
        teslim_text = sheets_applied.teslim_tarihi_text
        if not teslim_text.strip():
            teslim_text = build_teslim_tarihi_text(
                [line.teslim_suresi_parcasi for line in merged_lines]
            )

        return EnrichImportResult(
            enriched_path=result.enriched_path,
            warnings=warnings,
            filled_rows=result.matched,
            istek_no=istek_no,
            teslim_tarihi_text=teslim_text,
            quote_lines=merged_lines,
            conflicts=merged.conflicts,
            matches=merged.matches,
            form_revizyon=sheets_applied.form_revizyon,
        )

    def generate(
        self,
        request: QuoteRequest,
        create_pdf: bool = True,
        *,
        preview: bool = False,
    ) -> QuoteResult:
        if not request.teklif_no.strip():
            raise ValueError("Teklif No zorunludur")

        # İstek No: UI değeri öncelikli, yoksa dosya adından
        source_for_name = (request.source_excel_path or request.import_excel_path or "").strip()
        istek_no = (request.istek_no or "").strip()
        if not istek_no and source_for_name:
            istek_no = self.import_parser.istek_no_from_path(source_for_name)
        if not istek_no:
            istek_no = "manuel"
        form_teklif_no = format_teklif_no_with_revizyon(
            request.teklif_no, request.revizyon
        )
        base = output_basename(istek_no, form_teklif_no)

        if preview:
            create_pdf = False
            package_dir = preview_dir()
            cleanup_preview_files()
            original_excel_path = None
            enriched_excel_path = None
            # Önizlemede doldurulmuş Excel varsa sync için kullan (pakete kopyalama)
            sync_excel: Path | None = None
            if request.import_excel_path:
                enriched_src = Path(request.import_excel_path)
                if enriched_src.exists():
                    sync_excel = enriched_src
        else:
            parent = Path(request.output_dir)
            parent.mkdir(parents=True, exist_ok=True)
            package_dir = parent / base
            package_dir.mkdir(parents=True, exist_ok=True)

            original_excel_path = None
            enriched_excel_path = None
            source_path = Path(source_for_name) if source_for_name else None
            if source_path and source_path.exists():
                original_excel_path = self._copy_file(
                    source_path, package_dir / source_path.name
                )
            sync_excel = None
            if request.import_excel_path:
                enriched_src = Path(request.import_excel_path)
                if enriched_src.exists() and source_path:
                    filled_name = f"{source_path.stem}-doldurulmuş{source_path.suffix}"
                    enriched_excel_path = self._copy_file(
                        enriched_src, package_dir / filled_name
                    )
                elif enriched_src.exists():
                    enriched_excel_path = self._copy_file(
                        enriched_src, package_dir / enriched_src.name
                    )
                sync_excel = enriched_excel_path

        customer = self.customers.load(request.customer_code)
        warnings: list[str] = []
        if request.quote_lines:
            lines = list(request.quote_lines)
        elif sync_excel:
            lines, parse_warnings = self.import_parser.parse(sync_excel)
            warnings = list(parse_warnings)
        else:
            lines = []
        if not lines:
            raise ValueError(
                "Ürün satırı yok. Tablodan satır ekleyin veya Import Excel seçin."
            )

        # Arayüzdeki son ürün satırlarını doldurulmuş Excel'e yansıt
        if sync_excel and request.quote_lines and not preview:
            try:
                sync_warnings = sync_quote_lines_to_import_excel(
                    sync_excel,
                    lines,
                    teslim_tarihi_text=request.teslim_tarihi_text or "",
                )
                warnings.extend(sync_warnings)
            except Exception as exc:
                warnings.append(f"Doldurulmuş Excel güncellenemedi: {exc}")

        header = QuoteHeader(
            teklif_no=form_teklif_no,
            tarih=request.tarih or date.today(),
            hitap_kisi=request.hitap_kisi.strip(),
            hitap_adres_satirlari=list(request.hitap_adres_satirlari),
            hitap_telefon=request.hitap_telefon.strip(),
            hazirlayan=request.hazirlayan.strip(),
            teslimat=request.teslimat.strip(),
            teslimat_sekli=request.teslimat_sekli.strip(),
            odeme_sekli=request.odeme_sekli.strip(),
            istek_no=istek_no,
            revizyon=request.revizyon.strip(),
        )

        document = self.engine.build_document(
            customer=customer,
            header=header,
            lines=lines,
            sartlar=request.sartlar if request.sartlar is not None else [],
            ozel_sartlar=request.ozel_sartlar,
        )
        if (request.teslim_tarihi_text or "").strip():
            document.teslim_tarihi_text = request.teslim_tarihi_text.strip()

        if preview:
            # Tek dosya: yer kaplamasın diye hep aynı isim
            xlsx_path = package_dir / "onizleme.xlsx"
            try:
                if xlsx_path.exists():
                    xlsx_path.unlink()
            except OSError:
                # Önceki önizleme Excel'de açıksa yeni isimle yaz
                xlsx_path = package_dir / f"onizleme_{os.getpid()}.xlsx"
        else:
            xlsx_path = package_dir / f"{base}.xlsx"
        filler = TemplateFiller(revise=request.is_revise)
        filler.fill(document, xlsx_path)

        if not preview:
            self.store.remember_quote_fields(
                {
                    "hazirlayan": header.hazirlayan,
                    "teslimat": header.teslimat,
                    "teslimat_sekli": header.teslimat_sekli,
                }
            )
            for sart in request.ozel_sartlar:
                self.store.add_unique("ozel_sartlar", sart)

        pdf_path = None
        if create_pdf:
            if not self.exporter.is_available():
                warnings.append(
                    "PDF için pywin32 veya Microsoft Excel bulunamadı; "
                    "yalnızca Excel çıktısı üretildi."
                )
            else:
                try:
                    pdf_path = self.exporter.export_pdf(
                        xlsx_path,
                        package_dir / f"{base}.pdf",
                        sheet_name=(
                            "Revize Teklif" if request.is_revise else "Teklif"
                        ),
                    )
                except Exception as exc:
                    warnings.append(f"PDF üretilemedi: {exc}")

        return QuoteResult(
            document_path=xlsx_path,
            pdf_path=pdf_path,
            warnings=warnings,
            enriched_excel_path=enriched_excel_path,
            original_excel_path=original_excel_path,
            output_folder=package_dir,
        )

    @staticmethod
    def _copy_file(src: Path, dest: Path) -> Path:
        if src.resolve() == dest.resolve():
            return dest
        try:
            shutil.copy2(src, dest)
            return dest
        except PermissionError:
            alt = dest.with_name(f"{dest.stem}_kopya{dest.suffix}")
            shutil.copy2(src, alt)
            return alt

    def build_sheets_clipboard_text(self, request: QuoteRequest) -> str:
        customer = self.customers.load(request.customer_code)
        if request.quote_lines:
            lines = list(request.quote_lines)
        elif request.import_excel_path:
            lines, _ = self.import_parser.parse(Path(request.import_excel_path))
        else:
            lines = []
        if not lines:
            raise ValueError(
                "Ürün satırı yok. Tablodan satır ekleyin veya Import Excel seçin."
            )

        source_for_name = (request.source_excel_path or request.import_excel_path or "").strip()
        istek_no = (request.istek_no or "").strip()
        if not istek_no and source_for_name:
            istek_no = self.import_parser.istek_no_from_path(source_for_name)
        if not istek_no:
            istek_no = "manuel"
        header = QuoteHeader(
            teklif_no=request.teklif_no.strip(),
            tarih=request.tarih or date.today(),
            hitap_kisi=request.hitap_kisi.strip(),
            hitap_adres_satirlari=[],
            hitap_telefon=request.hitap_telefon.strip(),
            hazirlayan=request.hazirlayan.strip(),
            teslimat=request.teslimat.strip(),
            teslimat_sekli=request.teslimat_sekli.strip(),
            odeme_sekli=request.odeme_sekli.strip(),
            istek_no=istek_no,
            revizyon=request.revizyon.strip(),
        )
        if not header.teklif_no:
            raise ValueError("Teklif No zorunludur")
        return build_sheets_tsv(customer, header, lines)

    def build_istek_clipboard_text(
        self,
        *,
        customer_code: str,
        hazirlayan: str,
        import_excel_path: str,
        teklif_no: str,
        musteri_teklif_no: str,
        hitap_kisi: str,
        tarih: date | None = None,
    ) -> str:
        customer = self.customers.load(customer_code)
        try:
            lines, _warnings = self.import_parser.parse(
                import_excel_path, mode="istek"
            )
        except Exception as exc:
            raise ValueError(str(exc)) from exc
        if not lines:
            raise ValueError("Import Excel'de işlenecek satır bulunamadı.")
        if not hazirlayan.strip():
            raise ValueError("Hazırlayan zorunludur")
        if not teklif_no.strip():
            raise ValueError("Teklif No zorunludur")
        if not musteri_teklif_no.strip():
            raise ValueError("Müşteri Teklif No zorunludur")
        if not hitap_kisi.strip():
            raise ValueError("Hitap kişisi zorunludur")
        return build_istek_sheets_tsv(
            customer,
            lines,
            hazirlayan=hazirlayan,
            teklif_no=teklif_no,
            musteri_teklif_no=musteri_teklif_no,
            hitap_kisi=hitap_kisi,
            tarih=tarih,
        )
