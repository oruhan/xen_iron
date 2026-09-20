# TS101 OLED simge kaynakları

Bu klasördeki `.pbm` dosyaları firmware simgelerinin kaynak dosyalarıdır. Her
dosya tek bir simge veya tek bir animasyon karesidir. `P1` PBM biçiminde `1`
yanan, `0` sönük piksel anlamına gelir.

## Piksel düzenleme

`editor.html` dosyasını tarayıcıda açın, **PBM aç** ile bir simge seçin ve
piksellere tıklayarak çizin. **PBM indir** dosyanın düzenlenmiş halini indirir;
orijinal dosyanın üzerine koyun.

Ardından firmware dizininde:

```sh
python3 tools/oled_assets.py generate
python3 tools/oled_assets.py check
```

İlk komut `source/core/drivers/OLEDAssets.generated.h` dosyasını ve `previews/`
altındaki PNG önizlemelerini yeniler. Oluşturulan C++ dosyasını elle
düzenlemeyin.

## Yeni simge ekleme

Boş bir 16x16 simge örneği:

```sh
python3 tools/oled_assets.py new yeni_simge 16 16 YeniSimge
```

Bu komut `custom/yeni_simge.pbm` dosyasını oluşturur, `manifest.json` içine
ekler ve firmware dizisini `YeniSimge` adıyla üretir. Simgenin ekranda nerede
çizileceğini ilgili C++ arayüz kodunda `OLED::drawArea(...)` ile belirleyin.

## Klasörler

- `static/`: sabit ana ekran, uyarı ve durum simgeleri
- `symbols/`: 12x16 sembol fontundaki her simge
- `settings/`: ayarlar menüsündeki her simgenin 3 ayrı karesi
- `animations/`: ana ekran animasyonlarının 8’er ayrı karesi
- `custom/`: sonradan eklenen simgeler
- `previews/`: otomatik üretilen, 8 kat büyütülmüş PNG görüntüler

Açılış logosu bu koleksiyona dahil değildir; cihazın ayrılmış logo flash
alanından yüklenir ve kendi animasyon biçimine sahiptir.
