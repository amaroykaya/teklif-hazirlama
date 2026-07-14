# Teklif Hazırlama — İsterler

Bu belge, konuşmalar boyunca verilen iş isterlerinin güncel (son karar) hâlidir.

---

## 1. Amaç ve kapsam

- Müşteri teklifleri şu an büyük ölçüde manuel hazırlanıyor; müşteriye göre format ve kurallar değişiyor. Uygulama bu süreci standartlaştırıp otomatikleştirmeli.
- v1 odağı: doğru teklif formunun (ve teklif isteği kopyasının) otomatik hazırlanması.
- Sistemi tek kişi kullanır (rol / yetki yok).
- Platform: Windows masaüstü uygulaması.
- Müşteri kuralları (geçerlilik, para birimi, firma bilgisi vb.) kodun içine gömülmeden yönetilebilir olmalı.
- v1 dışında: geçmiş arşiv, raporlar, web, e-posta gönderimi, ERP/CRM entegrasyonu.

---

## 2. Açılış ve genel arayüz

- Uygulama açılınca iki seçenek sunulur:
  1. **Teklif İsteği**
  2. **Teklif Formu Hazırlama**
- Her iki ekrandan ana menüye dönülebilmeli.
- Pencereler gereksiz yere büyük açılmamalı (dar / kısa).
- Kayıt klasörü varsayılanı: **Masaüstü**.
- Ödeme şekli ve özel şart alanları kullanılabilir boyutta kalsın (küçültülmesin).

---

## 3. Müşteri / firma

- Önce müşteri seçilir; seçilen firmaya göre kurallar uygulanır.
- Başlangıç müşterisi: **Roketsan** (ileride başka firmalar eklenebilir).
- Firma **eklenebilmeli, düzenlenebilmeli, silinebilmeli** (mevcut Roketsan dahil).
- Firma kısa adı (kopyalama vb. için): uzun resmi ünvan değil, örn. `roketsan`.
- Firma adres bilgisi firma düzeyinde sabittir; hitap kişisine göre değişmez.
- Roketsan kuralları:
  - Geçerlilik: teklif tarihi **+30 gün**
  - Para birimi: her zaman **USD**
- KDV oranı her zaman **%20**.

---

## 4. Hitap kişisi

- Formda hitap edilecek kişi seçilir; bir kez girilince hafızada kalır.
- Formda hitap: `Sayın {ad}`.
- Hitap kişisinde tutulacaklar: **ad + telefon** (adres firmadan gelir; hitap eklerken adres satırları istenmez).
- Hitap kişisi **eklenebilmeli, düzenlenebilmeli, silinebilmeli**.
- Hitap seçilince ilgili bilgiler forma otomatik gelsin.

---

## 5. Seçim listeleri (ekle / düzenle / sil)

Aşağıdakiler listeden seçilebilmeli; yeni değerler eklenebilmeli, düzenlenebilmeli, silinebilmeli:

- Firma
- Hitap kişisi
- Hazırlayan
- Teslimat (örn. `Yurtiçi Kargo`)
- Teslimat Şekli (örn. `Kapı Teslim`)

---

## 6. Teklif formu üst bilgileri

| Alan | Kural |
|------|--------|
| Tarih | Varsayılan: bugün |
| Teklif No | Roketsan için otomatik (aşağıda); elle de değiştirilebilir |
| Revizyon | Teklif No altında ayrı alan |
| Geçerlilik | Müşteri kuralına göre (Roketsan: +30 gün) |
| Hazırlayan | Listeden seçim |
| Hitap | Listeden seçim |
| İstek No | Yüklenen import Excel dosya adından (uzantısız). Örn. `QR075313.xlsx` → `QR075313` |
| Teslimat / Teslimat Şekli | Listeden seçim |
| Ödeme Şekli | Çok satırlı metin; örn.: |

```
Peşin VEYA
Fatura sonrası 21 Gün Vade
Ödeme Günü USD Kuru ile
```

- **Özel şart:** doğrudan alana yazılır (ayrı ekle/sil butonu gerekmez). Varsa şartlardaki ürün kodlarının hemen altına yazılır.

---

## 7. Teklif No ve revizyon

### Roketsan otomatik teklif no

- Format: `RKTSN-YYAA-GG`
- Örnek (11.07.2026): **`RKTSN-2607-11`**
- Hem **Teklif İsteği** hem **Teklif Formu Hazırlama** ekranında Roketsan seçilince otomatik gelsin.
- Alan düzenlenebilir kalsın.

### Formda görünen teklif no

- Revizyon girildiyse: `{teklif_no}-R{revizyon}`
- Örnek: teklif no `ant2526`, revizyon `2` → **`ant2526-R2`**

### Kopyalamadaki revizyon (L sütunu)

- Formdaki revizyon değerine **+1** yazılır: `1→2`, `2→3`, `R3→4` …

---

## 8. Import Excel

### Yapı

- **2. satır:** sütun adları (başlıklar)
- **3. satırdan itibaren:** veri
- Eşleştirme **sütun harfine göre değil, sütun adına göre** yapılır (dosyadan dosyaya sütun kayabilir).

### Satır filtresi

- Yalnızca **Teklifte Bulun = Y** olan satırlar alınır (`N` / boş alınmaz).
- `Y` benzeri kabul: YES / EVET / 1 / True (uygulama toleransı).

### Alan eşleşmeleri

| Form / kullanım | Import sütunu |
|-----------------|---------------|
| Adet | **Miktar** |
| Birim Fiyat | **Fiyat** |
| Toplam Fiyat | **Satır Toplamı** (yoksa veya 0 ise: adet × birim fiyat) |
| Açıklama | **Stok Tanımı** + ` / ` + **Stok Kodu** (örn. `ali ata bak / 002525`) |
| Antsis Ürün Kodu | **Tedarikçi Notu** içinden çıkarılır |
| Teslim Tarihi (form) | **Tedarikçi Notu** içinden çıkarılır |
| Termin (Sheets kopyası) | **Termin Tarihi** — tarih+saat varsa yalnızca tarih |

### Teklif Formu vs Teklif İsteği

- **Teklif Formu:** Fiyat, Satır Toplamı, Tedarikçi Notu (Antsis ürün kodu) zorunlu.
- **Teklif İsteği:** Fiyat / Satır Toplamı / Tedarikçi Notu zorunlu değil; varsa kullanılır (kopyalamada J/K için fiyatlar gerekir).

### Tedarikçi Notu kuralları

Örnek girdi:

`Teslim Süreleri : ANT-DVI-ENC-hfkaha - 29 adet T0+34 Hafta T0: Sipariş Onay Tarihi`

- Ürün kodu: `ANT-DVI-ENC-hfkaha` (`29 adet` dahil değil).
- **Teslim Tarihi** hücresinde: her satırdan `Teslim Süreleri :` … `T0: Sipariş Onay Tarihi` arası alt alta; en sonda bir kez `T0: Sipariş Onay Tarihi`.
- Her teslim parçası hücre içinde satır satır; “Hafta”dan sonra yeni satır; satırlar arasında boş satır olmasın.
- Wrap Text açık; satır yüksekliği metne göre ayarlansın (metin kesilmesin).
- `T0: Sipariş Onay Tarihi` sonrası metin varsa açıklamaya parantezle eklenir; aynı hücrede **bir alt satırda**:
  - Örn. `( K ve P pizisyonları fiyata dahil değildir. )`

---

## 9. Teklif formu ürün satırları ve finans

Ürün tablosu sütunları:

- Adet | Antsis Ürün Kodu | Açıklama | Birim Fiyat | Toplam Fiyat

- Ara toplam, KDV %20 ve genel toplam hesaplanır.
- Şablon kapasitesinden fazla ürün olursa satır eklenir; alt bloklar kaydırılır.
- Birleşmiş hücreler şartlar / alt blokları kapatmamalı.
- Uzun teklif no hücre içinde kaymasın / okunabilir kalsın.

---

## 10. Şartlar bölümü

- Teklif Formu ekranında **Şartlar** alanı vardır; örnek formdaki `Şartlar:` altı açıklamalar otomatik yüklenir.
- Satırlar düzenlenebilir / silinebilir; boş bırakılan satırlar forma yazılmaz.
- Forma yazım sırası: düzenlenen şartlar → Antsis ürün kodları (virgülle, tekrarsız) → özel şart (varsa).
- Özel şart ayrı alana yazılır; ürün kodlarının / şartların altına eklenir.

---

## 11. Çıktı (Excel / PDF)

- Çıktı, Antsis antetli şablondan üretilir (`ANT-FRM-022 …` / proje şablonu).
- Yalnızca **Teklif** sayfası kullanılır (`Revize Teklif` ve `Ek A` yok).
- Görünüm şablonla birebir olmalı (antet, font, kenarlık korunur).
- Çıktı hem **Excel** hem **PDF** alınabilmeli.
- Dosya adı: `teklif-{İstekNo}-{TeklifNo}`  
  Örn. `teklif-QBR2525-RKTSN-2606-26-1-R3.xlsx` / `.pdf`
- PDF: genişlik 1 sayfa, yükseklik 1 sayfa; sayfa altı kesilmesin.
- İmza alanı şablondan kaldırıldıysa kod imza yerleştirmesin.

---

## 12. Teklif Formu — “Teklif Kopyala” (Google Sheets)

- Buton panoya TSV kopyalar; dosya yolu seçilmez.
- Yapıştırma: Sheets’te **A** hücresinden (A ve B boş gelir).
- Her ürün bir satırdır.

| Sütun | İçerik |
|-------|--------|
| A | boş |
| B | boş |
| C | Firma kısa adı (örn. `roketsan`) |
| D | Stok tanımı / stok kodu |
| E | Adet |
| F | Teklif tarihi |
| G | Teklif no |
| H | İstek no |
| I | Termin tarihi (yalnız tarih) |
| J | Birim fiyat (`$` olmadan, örn. `2.025,00`) |
| K | Toplam fiyat (`$` olmadan) |
| L | Revizyon (**+1**) |
| M | Hazırlayan baş harfleri (küçük, boşluksuz) |
| N | boş |
| O | boş |
| P | `Sorumlusu : {Hitap ad soyad}` |

---

## 13. Teklif İsteği — “İlk Teklif İsteği Kopyala”

- Ayrı ekran alanları: **Müşteri**, **Hitap Kişisi**, **Teklif No**, **Müşteri Teklif No**, **Hazırlayan**, **Import Excel** (tek dosya).
- Yapıştırma: Sheets’te **A** hücresinden.

### Import Excel — Teklif İsteği (yeni model, tek dosya)
- Başlık **1. satır**, veri **2. satırdan**
- **Gereksinim Tarihi** (eski Termin Tarihi yerine)
- Kullanılan sütunlar: Teklifte Bulun, Stok Kodu, Stok Tanımı, Miktar, Gereksinim Tarihi, Fiyat, Satır Toplamı, Kalite Provizyonları, Teknik Resim/Şartname, Kalem Revizyon
- **Teklifte Bulun = Y** veya **boş** satırlar alınır (`N` alınmaz)

### Import Excel — Teklif Formu Hazırlama (eski model)
- Başlık **2. satır**, veri **3. satırdan**
- Termin Tarihi, Tedarikçi Notu (Antsis ürün kodu / teslim süreleri) zorunlu kurallar eskisi gibi
- Yalnızca **Teklifte Bulun = Y** satırları

### Sheets kolonları (A..W)

| Sütun | İçerik | Kaynak |
|-------|--------|--------|
| A | Yıl + ay adı (örn. `2026 Temmuz`) | Sistem |
| B | boş | — |
| C | Firma kısa adı | Müşteri |
| D | boş | — |
| E | Stok kodu | Excel |
| F | Stok Tanımı / Stok Kodu | Excel |
| G | Miktar | Excel |
| H | Bugünün tarihi | Sistem |
| I | Teklif no | Ekran |
| J | Müşteri teklif no (elle) | Ekran |
| K | Gereksinim / Termin Tarihi (yalnız tarih) | Excel |
| L | Fiyat | Excel |
| M | Satır Toplamı | Excel |
| N | `1` (revizyon) | Sabit |
| O | Hazırlayan baş harfleri | Ekran |
| P, Q | boş | — |
| R | Kalite Provizyonları | Excel |
| S | Teknik Resim/Şartname | Excel |
| T | Kalem Revizyon | Excel |
| U, V | boş | — |
| W | Hitap kişisi ad soyad | Ekran |

---

## 14. Hazırlayan baş harfleri (ortak kural)

- Ad ve soyadın ilk harfleri, **küçük harf**, arada **boşluk yok**.
- Türkçe karakterler ASCII’ye çevrilir: Ö→o, Ü→u, Ş→s, Ç→c, Ğ→g, İ/I/ı→i.
- Örnekler:
  - `Alican Uzun` → `au`
  - `Kerem Özsoy` → `ko` (**`kö` değil**)

---

## 15. Kapsam dışı / ertelenen

- Geçmiş teklif arşivi ve raporlama
- Çok kullanıcılı yetkilendirme
- Web sürümü
- E-posta ile gönderme
- ERP / CRM entegrasyonu
- Kod ile imza yerleştirme (şablonda imza yoksa)

---

## 16. Yeni teklif formu akışı (Sheets master → Excel tamamlar → form)

```text
1) Google Sheets A–W yapıştır → ürün tablosu / Teslim Tarihi hemen dolar (Sheets master)
2) Import Excel seç → eksik alanlar Excel'den tamamlanır; doldurulmuş Excel üretilir
3) Sheets ↔ Excel karşılaştırılır; çelişkide Sheets kullanılır ve uyarı verilir
4) Teklif formu = ekrandaki son hali
```

### Arayüz

- Ana Teklif Formu ekranında **Google satırlarını yapıştır** (veya benzeri) butonu olur.
- Butona basınca **ayrı bir pencere/ekran** açılır.
- Kullanıcı Google Sheets’ten kopyaladığı A–W içeriğini **yalnızca bu pencereye** yapıştırır (çok satır + başlık).
- Onay / devam sonrası ana akışa dönülür; Excel import ve form üretimi buradan devam eder.

### Sheets başlık satırı (A → W)

| Harf | Sütun adı |
|------|-----------|
| A | ilk rev Zamanı |
| B | No |
| C | Firma |
| D | Antsis Ürün Kodu |
| E | Müşteri Stok Kodu |
| F | Proje Tanımı |
| G | Adet |
| H | Teklif Tarihi |
| I | Antsis Teklif No |
| J | Müşteri Teklif Numarası |
| K | Teklif Sevk Tarihi |
| L | Birim Fiyat |
| M | Toplam Fiyat |
| N | Revizyonu |
| O | Teklifi Hazırlayan |
| P | Beklenen Bilgiler |
| Q | Sipariş alındı mı |
| R | Kalite Provizyonu |
| S | Teknik şartname |
| T | Kalem Revizyon |
| U | Kalemdeki Özel Şartlar |
| V | Açıklama |
| W | Satınalma Sorumlusu |

### Excel’e yazılacak alanlar

| Excel sütunu | Kaynak / kural |
|--------------|----------------|
| **Fiyat** | Sheets **L — Birim Fiyat** |
| **Temin Süresi (Takvim Günü)** | Sheets **K — Teklif Sevk Tarihi** metninden hesaplanır |
| **Tedarikçi Notu** | **D** + **K** + **U**’dan üretilir |
| **Garanti Süresi (Yıl)** | Her satırda sabit **`1.0`** |

### Temin Süresi hesabı

Teklif Sevk Tarihi (K) örnek:

```text
01.11.2026
5 x 10 hafta
5 x 24 hafta
10 x 35 hafta
```

1. Hafta sayılarının **en büyüğü** (ör. `35`)
2. `35 × 7 = 245`
3. **Bir sonraki onluğa** yuvarla → **`250`** (tam onluk da bir üste: `210 → 220`)

### Tedarikçi Notu formatı

`N x H hafta` → `N adet T0+H Hafta` (virgülle yan yana).

```text
Teslim süresi : {D Antsis Ürün Kodu} - 5 adet T0+10 Hafta, 5 adet T0+24 Hafta, 10 adet T0+35 Hafta T0: Sipariş Onay Tarihi {U Kalemdeki Özel Şartlar}
```

- U boşsa `T0: Sipariş Onay Tarihi` ile biter.

### Eşleme

- Sheets **E — Müşteri Stok Kodu** ↔ Excel **Stok Kodu**
