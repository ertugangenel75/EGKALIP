# EG\_KALIP — Betonarme Kalıp Metraj Eklentisi

**Sürüm:** v26  
**Platform:** Autodesk Revit 2021 – 2026 · pyRevit 4.8+  
**Dil:** IronPython 2.7 (CPython 3 uyumlu çekirdek)  
**Yazar:** Ertuğan Genel / EGBIM

---

## Genel Bakış

EG\_KALIP, Revit modelindeki taşıyıcı sistem elemanlarının kalıp alanını **imalat sırası mantığıyla** hesaplayan bir pyRevit eklentisidir. Her yüzey yalnızca bir kez sayılır; kesişim bölgelerinde kalıp alanı tekrar edilmez.

Desteklenen eleman kategorileri:

| Kategori | Revit Sınıfı |
|---|---|
| Kolon | Structural Columns |
| Kiriş | Structural Framing |
| Döşeme | Floors |
| Taşıyıcı Duvar | Walls (structural) |
| Temel | Structural Foundations |

---

## Kurulum

```
pyRevit/Extensions/
└── EG_KALIP_V26.extension/
    ├── EG_KALIP.tab/
    │   └── Kalip.panel/
    │       ├── Metraj.pushbutton/
    │       ├── ExcelRapor.pushbutton/
    │       ├── Parametre.pushbutton/
    │       ├── Tani.pushbutton/
    │       └── lib/
    └── README.md
```

1. `EG_KALIP_V26.extension` klasörünü pyRevit `Extensions` dizinine kopyalayın.
2. Revit'i yeniden başlatın veya pyRevit → **Reload** yapın.
3. Revit şeridinde **EG\_KALIP** sekmesi görünecektir.

---

## Butonlar

### Parametre

Projeye kalıp parametrelerini ekler. **İlk kullanımda bir kez çalıştırın.**

Oluşturulan parametreler:

| Parametre | Tür | Açıklama |
|---|---|---|
| `Formwork_Area` | Number (m²) | Hesaplanan kalıp alanı |
| `TR_KalipAlani` | Text | Görüntüleme amaçlı alan |
| `TR_KalipPozNo` | Text | ÇŞB poz kodu |
| `TR_KalipPozAdi` | Text | Poz açıklaması |
| `TR_KalipBirimFiyat` | Number | TL/m² birim fiyat |
| `TR_KalipToplamTutar` | Number | Toplam TL |

---

### Metraj

Modeldeki tüm uygun elemanları tarar, kalıp alanını hesaplar.

**Seçenekler (çoklu seçim):**

- **Döşeme kenar kalıbını dahil et** — Döşemenin açık kenar yüzeyleri hesaba katılır.
- **Hesaplanan değerleri Revit parametrelerine yaz** — `Formwork_Area` ve `TR_Kalip*` parametreleri güncellenir.
- **HTML Rapor oluştur ve aç** — Özet + teknik iz raporu tarayıcıda açılır.

**Çıktı:**

- pyRevit output penceresinde özet tablo
- İsteğe bağlı HTML rapor (geçici dizin)

---

### Excel Rapor

Hesap sonuçlarını **Excel XML** formatında üç sayfalı bir dosya olarak dışa aktarır.

**Seçenek:** Döşeme kenar kalıbını dahil et / hariç tut

**Sayfa düzeni:**

| Sayfa | İçerik | Sütunlar |
|---|---|---|
| **Özet** | Poz bazlı toplam | TR Poz No · TR Poz Açıklaması · Kalıp Alanı (m²) · Birim · Birim Fiyat (TL/m²) · Toplam (TL) |
| **Kat × Kategori** | Çapraz tablo | Kat / Seviye × Kategori |
| **Detay** | Her eleman satırı | No · Tip/Aile · Poz No · Poz Açıklama · Seviye · Kalıp Alanı (m²) · Element Id |

Dosya `.xml` uzantılıdır, Excel'de doğrudan açılır. Format EGCost Dış Import ile uyumludur.

---

### Tanı

Eleman sayımını ve hesap yöntemini ekranda gösterir. Sorun gidermede kullanılır.

Gösterilen bilgiler:

- Kategori bazlı eleman sayıları
- Her kategorinin toplam kalıp alanı
- Genel toplam

---

## Hesap Yöntemi

### Sahiplik Kuralı

Bir yüzey hangi elemana aitse yalnızca o eleman tarafından sayılır. Aynı bölge iki kez hesaplanmaz.

---

### Kolon

**A. Ana gövde**

Kolon alt kotundan en düşük bağlı kiriş alt kotuna (kiriş yoksa döşeme alt kotuna) kadar hesaplanır.

```
A_gövde = 2 × (b + h) × H_gövde
```

**B. Kolon başı**

Kiriş altı ile döşeme altı arasında kalan, açıkta olan kolon yüzleri. Her yön (K/G/D/B) için:

```
A_yüz = dim × head_h  −  kiriş düşümü  −  döşeme düşümü
```

```
A_kolon = A_gövde + A_kolon_başı
```

---

### Kiriş

Üst yüz sayılmaz. Alt yüz ve iki yan yüz brüt olarak alınır.

```
A_brüt = L × (b + 2h)
```

Düşümler:

- Döşeme içinde kalan yan yüzler düşer.
- Tam döşeme altındaysa 2 yan yüz, kenar kirişiyse 1 yan yüz düşer.
- Kiriş–kiriş birleşimlerinde yalnızca ana kiriş (uzun) kesinti uygular; sekonder kirişin kesiti düşülür.
- Kolon / duvar destek bölgelerinde xy örtüşme alanı düşülür.

---

### Döşeme

**A. Döşeme alt yüz**

Revit `Area` parametresi (gerçek plan alanı, eğri döşemelerde de doğru) baz alınır.

```
A_alt = A_brüt − A_kolon_temas − A_kiriş_temas − A_duvar_temas
```

**B. Döşeme kenar kalıbı** *(isteğe bağlı)*

```
A_kenar = açık_kenar_uzunluğu × döşeme_kalınlığı
```

Açık kenar: Kolon ve kiriş tarafından kapatılmayan kenarlar. Taşıyıcı duvar bu hesapta kenar kapatmaz.

```
A_döşeme = A_alt + A_kenar
```

---

### Taşıyıcı Duvar

Yalnızca `Structural` olarak işaretlenmiş duvarlar hesaplanır.

```
A_brüt = 2 × L × H
A_duvar = A_brüt − kiriş_birleşimleri − kolon_birleşimleri
```

---

### Temel

```
A_temel = 2 × (b1 + b2) × H − duvar_düşümleri
```

Boyutlar: Revit parametrelerinden (`Foundation Depth`, `Depth`, `Height`) alınır; yoksa BBox'tan hesaplanır.

---

## Poz Tablosu

ÇŞB 2026 birim fiyat listesine göre tanımlı pozlar:

| Poz No | Açıklama | Birim Fiyat (TL/m²) |
|---|---|---|
| 15.180.1001 | Ahşaptan seri kalıp | 267,76 |
| 15.180.1002 | Ahşaptan düz yüzeyli betonarme kalıbı | 705,75 |
| 15.180.1003 | Plywood ile düz yüzeyli betonarme kalıbı | 824,39 |
| 15.180.1004 | Saç ile eğri yüzeyli betonarme kalıbı | 779,49 |
| 15.180.1007 | Tünel kalıp sistemi | 853,36 |

**Varsayılan poz atamaları:**

| Kategori | Varsayılan Poz |
|---|---|
| Kolon, Kiriş, Temel | 15.180.1002 |
| Döşeme, Taşıyıcı Duvar | 15.180.1003 |

Eleman üzerinde `TR_KalipPozNo` parametresi dolu ise varsayılan poz korunmaz; parametre değeri kullanılır.

---

## EGCost Entegrasyonu

Excel Rapor çıktısı (`.xml`) doğrudan **EGCost Dış Import** ile yüklenebilir.

Dış Import `TR Poz No` → `keynote`, `Kalıp Alanı (m²)` → `miktar`, `Birim Fiyat (TL/m²)` → `birim_fiyat` sütunlarını otomatik eşleştirir. EGCost v3.1+ gerektirir.

---

## Dosya Yapısı

```
EG_KALIP_V26.extension/
├── EG_KALIP.tab/
│   └── Kalip.panel/
│       ├── Metraj.pushbutton/
│       │   ├── script.py          — Metraj + HTML rapor launcher
│       │   ├── bundle.yaml
│       │   └── icon.png
│       ├── ExcelRapor.pushbutton/
│       │   ├── script.py          — 3 sayfalı Excel XML üretici
│       │   ├── bundle.yaml
│       │   └── icon.png
│       ├── Parametre.pushbutton/
│       │   ├── script.py          — Revit parametre oluşturucu
│       │   ├── bundle.yaml
│       │   └── icon.png
│       ├── Tani.pushbutton/
│       │   ├── script.py          — Tanı ve hata ayıklama
│       │   ├── bundle.yaml
│       │   └── icon.png
│       └── lib/
│           ├── eg_kalip_core.py       — Hesap koordinatörü, poz tablosu
│           ├── eg_kalip_utils.py      — Birim, BBox, geometri, parametre yardımcıları
│           ├── eg_kalip_beam.py       — Kiriş kalıp hesabı (düz + eğri)
│           ├── eg_kalip_column.py     — Kolon kalıp hesabı (gövde + baş)
│           ├── eg_kalip_floor.py      — Döşeme kalıp hesabı (alt yüz + kenar)
│           ├── eg_kalip_wall.py       — Taşıyıcı duvar kalıp hesabı
│           ├── eg_kalip_foundation.py — Temel kalıp hesabı
│           └── eg_kalip_report.py     — HTML rapor üretici
└── README.md
```

---

## Sürüm Notları

### v26
- Revit 2026 tam destek (`UnitTypeId` API)
- `eg_kalip_core.py` v25b: kategori dispatch dil bağımsız hale getirildi (`BuiltInCategory` int karşılaştırma)
- `intersecting_elements` ile ön-filtreleme: `ElementIntersectsElementFilter` + `BoundingBoxIntersectsFilter` birleşimi, büyük modellerde belirgin hız artışı
- Kolon başı hesabı yeniden yazıldı — her yön bağımsız değerlendiriliyor
- Döşeme kenar kalıbı: açık kenar belirleme algoritması kiriş eğri geometrisine uyumlu hale getirildi
- Excel Rapor: 3 sayfalı SpreadsheetML formatı, EGCost Dış Import uyumlu çıktı

### v25b
- IronPython `BuiltInCategory` dil sorunu düzeltildi
- `intersecting_elements` prefilter eklendi

### v23–v25
- Kiriş–kiriş birleşim mantığı: sekonder/ana ayrımı
- Döşeme BBox fallback kaldırıldı, `Revit.Area` zorunlu hale getirildi
- HTML rapor: teknik iz (trace) gösterimi

---

## Gereksinimler

- Autodesk Revit 2021, 2022, 2023, 2024, 2025 veya 2026
- pyRevit 4.8 veya üzeri
- Modelde `Structural` kategorisi aktif

---

## Lisans

© 2024–2026 Ertuğan Genel / EGBIM. Tüm hakları saklıdır.  
Ticari kullanım için iletişime geçin: [egbim.com](https://egbim.com)
