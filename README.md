# Teklif Hazırlama

Antsis müşteri bazlı teklif formu üretim uygulaması (Windows masaüstü).

## Kurulum

```bash
pip install -e ".[dev]"
```

## Çalıştırma

```bash
python -m teklif_hazirlama.main
```

veya

```bash
teklif-hazirlama
```

## Gereksinimler

- Windows 10/11
- Python 3.11+
- Microsoft Excel (PDF çıktısı için)

## Kullanım

1. Müşteri seçin
2. Teklif bilgilerini doldurun
3. Import Excel dosyasını seçin
4. **Excel Oluştur** veya **Excel + PDF Oluştur**

Çıktı adı: `teklif-{İstekNo}-{TeklifNo}.xlsx`

## Test

```bash
pytest
```
