# SearchPars

SearchPars, Pardus 25 için Apple Spotlight/Intelligence benzeri birleşik yapay
zekâ aramasıdır. Bilgisayardaki dosya ve uygulamaları, güncel web sonuçlarını,
döviz kurlarını ve yerel yapay zekâ cevaplarını tek pencerede birleştirir.

## Özellikler

- Doğal dille dosya arama: “27 Temmuz indirdiğim deb paketini bul”
- Dosya adı, içerik, tür, klasör ve tarihe göre yerel arama
- Uygulama bulma ve “Firefox'u aç” komutuyla doğrudan başlatma
- DuckDuckGo ve Türkçe Wikipedia üzerinden web araması
- TCMB kaynağından dolar, euro ve sterlin alış/satış kuru
- Sağ ayrıntı panelinde uzun yapay zekâ cevabı ve kaynaklar
- Ollama ve `qwen3.5:4b` ile bilgisayarda çalışan yerel yapay zekâ
- TXT, Markdown, kaynak kodu ve PDF içeriğinde arama
- Wi‑Fi, Bluetooth, ses, ekran görüntüsü ve ayarlar için sistem komutları

## Sistem gereksinimi

- Pardus 25 x86_64
- En az 8 GB RAM
- Yapay zekâ modeli için yaklaşık 5 GB boş disk
- İlk yapay zekâ kurulumu ve web sonuçları için internet bağlantısı

## Kurulum

1. [En son SearchPars sürümünü](https://github.com/techasl7585/searchpars/releases/latest)
   açın.
2. **Assets** bölümünden `SearchPars_0.4.4_Pardus.zip` dosyasını indirin.
3. ZIP dosyasına sağ tıklayıp **Buraya çıkart** seçeneğini kullanın.
4. Çıkan klasörde terminal açın.
5. Kurucuyu çalıştırın:

```text
./kur.sh
```

Gerekirse önce dosyaya çalıştırma izni verin:

```text
chmod +x kur.sh
./kur.sh
```

Başka bir paket veya geliştirme aracı kurmanız gerekmez. Kurucu gerekli Pardus
bağımlılıklarını, Ollama'yı ve `qwen3.5:4b` yapay zekâ modelini sırayla kurar.
Model indirme ilerlemesi terminalde görünür ve model doğrulanmadan kurulum
tamamlandı mesajı verilmez. Model yaklaşık 3,4 GB olduğu için ilk kurulum
internet hızına göre zaman alabilir.

Bağlantı kesilirse Ollama program arşivinin tamamlanan bölümü
`/var/cache/searchpars` içinde korunur. Yapay zekâ modeli ise SearchPars'ın
kesintiye dayanıklı indiricisiyle tek ve sıralı bir dosyaya kaydedilir. Her
yeniden bağlantıda mevcut dosya boyutundan HTTP Range ile devam edilir; gerçek
toplam yüzde geriye düşmez. Model dosyaları SHA-256 ile doğrulanmadan Ollama'ya
eklenmez. Kurulum kapatılırsa aşağıdaki komut aynı dosyadan devam eder:

```text
sudo /opt/searchpars/setup-local-ai.sh
```

> GitHub'daki **Code → Download ZIP** kaynak koddur. Son kullanıcı kurulumu için
> Releases bölümündeki `SearchPars_0.4.4_Pardus.zip` dosyasını indirin.

## Kullanım

Uygulamalar menüsünden **SearchPars**'ı açın. Örnek sorgular:

```text
Bilgisayarımdaki deb kurulum paketini bul
27 Temmuz indirdiğim deb paketini bul
Firefox'u aç
Bugünkü dolar kuru
Ali Koç kimdir?
Pardus 25 ile ilgili güncel haberler
Bu ay hazırladığım kod dosyalarını göster
Bluetooth'u aç
```

## Güncelleme

Yeni sürümün ZIP dosyasını Releases bölümünden indirip çıkartın ve kurucuyu
yeniden çalıştırın:

```text
./kur.sh
```

Kişisel arama indeksi güncelleme sırasında korunur.

## Kaldırma

```text
sudo /opt/searchpars/uninstall.sh
```

Bu işlem yerel dosya indeksini ve başka uygulamaların da kullanabileceği Ollama
kurulumunu silmez. SearchPars verilerini de tamamen kaldırmak için:

```bash
rm -rf ~/.local/share/searchpars ~/.config/searchpars
```

## Kaynaktan geliştirme

Kaynak ZIP'i kurulum paketi değildir. Geliştirme ve test için:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 -m searchpars.app --rebuild
PYTHONPATH=. python3 -m searchpars.app --cli "Pardus PDF dosyalarını bul"
```

Son kullanıcı ZIP paketini üretmek için:

```bash
chmod +x scripts/build-zip.sh
./scripts/build-zip.sh
```

ZIP paketi ve SHA256 doğrulama dosyası `dist/` klasöründe oluşturulur.

## İnternet servisleri ve gizlilik

Dosya indeksi `~/.local/share/searchpars/index.db` içinde tutulur. Yerel dosya
içerikleri web arama sağlayıcılarına gönderilmez. Genel web sorgusu DuckDuckGo
ve Türkçe Wikipedia'ya, döviz sorgusu TCMB'ye gönderilir. Ollama ile oluşturulan
cevaplar bilgisayarda işlenir.

## Sorun giderme

Yapay zekâ modelini yeniden kurmak veya doğrulamak için:

```text
sudo /opt/searchpars/setup-local-ai.sh
```

Uygulamayı terminalden başlatıp hata çıktısını görmek için:

```bash
searchpars
```

Geliştirici: [techasl7585](https://github.com/techasl7585)
