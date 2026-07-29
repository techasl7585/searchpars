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
2. **Assets** bölümünden `SearchPars_0.3.0_amd64.deb` dosyasını indirin.
3. Dosyaya çift tıklayıp Pardus Paket Kurucu ile **Kur** seçeneğini kullanın.

Terminalden kurmak isterseniz:

```bash
cd ~/İndirilenler
sudo apt install ./SearchPars_0.3.0_amd64.deb
```

Başka bir paket veya geliştirme aracı kurmanız gerekmez. Pardus gerekli sistem
bağımlılıklarını otomatik kurar. Ollama ve yapay zekâ modeli de kurulumdan sonra
arka planda hazırlanır. Modelin ilk indirilmesi internet hızına göre birkaç
dakika sürebilir; bu sırada dosya, uygulama ve web araması kullanılabilir.

> GitHub'daki **Code → Download ZIP** seçeneği kaynak koddur ve son kullanıcı
> kurulumu değildir. Kurulum için Releases bölümündeki `.deb` dosyasını kullanın.

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

Yeni sürümün `.deb` dosyasını Releases bölümünden indirip aynı komutla kurun:

```bash
sudo apt install ./SearchPars_YENI_SURUM_amd64.deb
```

Kişisel arama indeksi güncelleme sırasında korunur.

## Kaldırma

```bash
sudo apt remove searchpars
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

Kurulabilir `.deb` üretmek için:

```bash
chmod +x scripts/build-deb.sh
./scripts/build-deb.sh
```

Paket `dist/` klasöründe oluşturulur.

## İnternet servisleri ve gizlilik

Dosya indeksi `~/.local/share/searchpars/index.db` içinde tutulur. Yerel dosya
içerikleri web arama sağlayıcılarına gönderilmez. Genel web sorgusu DuckDuckGo
ve Türkçe Wikipedia'ya, döviz sorgusu TCMB'ye gönderilir. Ollama ile oluşturulan
cevaplar bilgisayarda işlenir.

## Sorun giderme

Yapay zekâ ilk kurulumunun durumunu görmek için:

```bash
systemctl status searchpars-ai-setup.service
sudo tail -n 50 /var/log/searchpars-ai-setup.log
```

Uygulamayı terminalden başlatıp hata çıktısını görmek için:

```bash
searchpars
```

Geliştirici: [techasl7585](https://github.com/techasl7585)
