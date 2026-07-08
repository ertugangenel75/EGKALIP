# EG_KALIP FINAL v14

Bu paket, betonarme kalip metrajini **imalat sirasi mantigi** ile yeniden kurar.

## Temel ilke
Her yuzey yalnizca bir kez sayilir.
Kesisim bolgesinde kalip yoktur.

## Hesap omurgasi

### 1) Kolon
Kolon hesabi iki banda ayrilir:

**A. Ana govde**
- Kolon alt kotundan
- en dusuk bagli kiris alt kotuna kadar
- kiris yoksa doseme alt kotuna kadar

Formul:
- `A_govde = 2 x (b + h) x H_govde`

**B. Kolon basi**
- Kiris alti ile doseme alti arasinda kalan kolon parcasi
- yalnizca **acikta kalan kolon yuzleri** kadar eklenir
- bu kisim doseme kenar kalibi degildir, kolona aittir

Toplam:
- `A_kolon = A_govde + A_kolon_basi`

### 2) Kiris
- Ust yuz sayilmaz
- Alt yuz + iki yan yuz brut olarak alinur

Formul:
- `A_brut = L x (b + 2h)`

Dusum:
- Doseme icinde kalan yan yuzler duser
- Tam doseme altinda ise 2 yan yuz
- Kenar kirisiyse 1 yan yuz

### 3) Doseme
Doseme iki parcadir:

**A. Doseme alt yuz**
- Revit `Area` parametresi brut alan olarak baz alinir
- Bundan su temaslar duser:
  - doseme altina degen kolon
  - doseme altina degen kiris
  - doseme altina degen tasiyici duvar

Formul:
- `A_alt = A_brut - A_kolon_temas - A_kiris_temas - A_duvar_temas`

**B. Doseme kenar kalibi**
- Acik kenar uzunlugu x doseme kalinligi
- Kenari sadece kolon ve kiris kapatir
- Tasiyici duvar, bu pakette doseme kenar kalibini kapatmaz

Toplam:
- `A_doseme = A_alt + A_kenar`

### 4) Tasiyici duvar
Sadece structural duvarlar hesaplanir.

Brut:
- `A_brut = 2 x L x H`

Dusum:
- Kiris birlesimleri
- Kolon birlesimleri

Net:
- `A_duvar = A_brut - A_kiris_birlesimi - A_kolon_birlesimi`

### 5) Temel
- `A_temel = 2 x (b1 + b2) x H - duvar_dusumleri`

## Sahiplik kurali
- Doseme altina degen alanlar dosemeden duser
- Doseme kenari yalnizca dosemenin acik yan yuzudur
- Kolon basi kolona aittir
- Ayni bolge iki kez dusulmez

## Notlar
- Hesap cekirdegi, pyRevit / Revit saha mantigina gore yeniden duzenlenmistir
- Ozellikle kolon-kiris-doseme is sirasi dikkate alinmistir
- Parametreye yazim icin `Formwork_Area` kullanilir

## Butonlar
- **Metraj**: hesap yapar, istenirse `Formwork_Area` parametresine yazar
- **Excel Rapor**: detay + ozet raporu uretir
- **Tani**: paket tanitimi / bilgi


## v14 duzeltmeleri
- Kolon destek seviyesi aramada sadece XY overlap degil, edge-touch / temas da kabul edilir. Bu sayede kolona oturan kiris alt kotu dogru bulunur.
- Kiris doseme yan yuz dusumunde, kenar kirisi durumunda 1 yuz; tam doseme altinda 2 yuz dusulur.
- Kiris yan yuz dusumunde doseme kalinligi baz alinir; tum kiris yuksekligi dusulmez.
- Ornek kontrol: 1x1x3 m kiris, h=1.0, L=3.0, doseme T=0.30 ise tam brut 9.0 m2; bir yan yuz doseme icinde ise net 8.1 m2, iki yan yuz doseme icinde ise net 7.2 m2.
- Ornek kontrol: 1x1 m kolon, kiris alti 2.0 m, doseme alti 3.0 m ise ana govde 8.0 m2; ust bantta 2 acik yuz varsa +2.0 m2, toplam 10.0 m2.


## v15 düzeltmeleri
- Kolon başı ek alanı artık kiriş alt kotundan kolon top kotuna kadar hesaplanır.
- Kiriş kesitinde `b` yatay genişlik, `h` düşey yükseklik olarak okunur; 700x1000 gibi kirişlerde ters okuma düzeltildi.
- Beklenen testler: kenar kiriş 8.10 m², örnek kolon 10.00 m², 700x1000 kiriş 7.20 m².


## v16 duzeltmeleri
- Kiris altina gelen tasiyici duvar / kolon izleri kiris alt yuzunden dusulur.
- Structural ozelligi kaldirilan duvarlar tekrar yazimda Formwork_Area parametresini sifirlar; string parametre ise bosaltir.


## Excel raporu notu
- Excel raporu SpreadsheetML 2003 XML olarak disa aktarilir.
- Dosya uzantisi `.xml` oldugu icin Excel acilisinda bicim/uzanti uyarisı vermez.
- Rapordaki toplamlar formulle degil, Revitten hesaplanip yazilan net degerlerdir.


## v18 notu
- Doseme icindeki bosluklar / shaft aciklari icin, Perimeter parametresindeki ic loop cevresi kenar kalibina eklenir.
- Ornek: 4x3 m doseme icinde 1x1 m bosluk varsa, brut alan 12-1=11 m² olur; kenar kalibi icin 4x0.30=1.20 m² eklenir.
