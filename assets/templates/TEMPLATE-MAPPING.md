# Çıktı Şablonu Hücre Eşleşmeleri

**Kaynak:** `ANT-FRM-022 Teklif Dokümanı Yapısı Formu_rev4.xlsx`  
**Proje kopyası:** `teklif_sablonu.xlsx`  
**Sayfa:** `Teklif` (v1 çıktısı bu sayfadan üretilir)

> Önceki `örnek.xlsx` ile sütun konumları farklıdır. Geliştirme bu resmi rev4 şablonuna göre yapılır.

---

## Üst Bilgiler

| Alan | Etiket | Değer Hücresi | Not |
|---|---|---|---|
| Tarih | G8 | H8 | Bugünün tarihi |
| Teklif No | G9 | H9 | Manuel |
| Geçerlilik Süresi | F10 | H10 | Müşteri kuralı |
| Hazırlayan | G11 | H11 | Seçim listesi |
| Sayın [Kişi] | — | A14 | `Sayın {ad}` |
| Müşteri unvan | — | A16 | Kural setinden |
| Müşteri adres 1–3 | — | A17, A18, A19 | Kural setinden |

## Lojistik / Ödeme (R22 başlık, R23 veri)

| Alan | Başlık | Veri Hücresi |
|---|---|---|
| İstek No | A22 | A23 |
| Teslim Tarihi | B22 | B23 (B:D merge) |
| Teslimat | E22 | E23 |
| Teslimat Şekli | F22 | F23 |
| Ödeme Şekli | G22 | G23 (G:H merge) |

## Ürün Tablosu

| Alan | Başlık (R26) | Veri sütunu | Not |
|---|---|---|---|
| Adet | A26 | A27+ | |
| Antsis Ürün Kodu | B26 | B27+ | |
| Açıklama | C26 | C27+ (C:F merge) | |
| Birim Fiyat | G26 | G27+ | |
| Toplam Fiyat | H26 | H27+ | Formül: `=A*G` veya değer yaz |

**Kapasite:** Şablonda yalnızca **2 ürün satırı** (R27–R28) tanımlı. Daha fazla ürün için satır ekleme ve alt blokları (Ara Toplam, Şartlar) aşağı kaydırma zorunlu (FR-19).

## Finansal Özet

| Alan | Etiket | Değer |
|---|---|---|
| Ara Toplam | G29 | H29 (`=SUM(H27:Hn)`) |
| KDV (%20) | G30 | H30 (`=H29*0.2`) |
| Toplam | G31 | H31 (`=H29+H30`) |

## Şartlar Bölümü

| Bölüm | Hücre | İçerik |
|---|---|---|
| Başlık | A35 | `Şartlar:` (sabit) |
| Sabit şartlar | A36–A42 | Şablonda sabit metin |
| Ürün kodları | A43 | `, ` ile ayrılmış Antsis ürün kodları |
| Özel şart(lar) | A44+ | `Özel Şart Ekle` ile girilen metinler |

## Diğer Sayfalar

v1 çıktısı yalnızca `Teklif` sayfasından üretilir. `Revize Teklif` ve `Ek A` sayfaları şablondan kaldırıldı; kapsam dışıdır.

| Sayfa | Durum |
|---|---|
| `Teklif` | v1 çıktı şablonu |
| `adres` | Referans — müşteri adres verisi kaynağı olabilir (çıktıya yazılmaz) |
