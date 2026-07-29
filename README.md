# SearchPars

SearchPars, Pardus Gnome için  yapay
zekâ destekli arama uygulamasıdır. Bu Uygulamadaki Amaç Popüler İşletim Sistemlerinde macOS Apple Spotlight, Windows spotlight recall projelerinde olduğu gibi  Pardus Bilgisayrındaki aramayı yapay zeka ile çok daha kolaylaştırmak ve yapay zeka sayesinde aramada ciddi seviyede daha çok bilgiye ulaşmaktır. 

## Not

- İlerleyen Sürümlerde Yapay Zeka desteğinin Geliştirilmesiyle Arama Üzerinde Ciddi Gelişmeler Kaydedilebilir Ve Arama Tutarlılığı Arttırılabilir.

## Özellikler

- Yapay Zeka Sayesinde Gelişmiş Dosya Arama 
- Dahili web araması
- Sağ ayrıntı panelinde uzun yapay zekâ cevabı ve kaynaklar
- Ollama ve `qwen3.5:4b` ile bilgisayarda çalışan yerel yapay zekâ
- TXT, Markdown, kaynak kodu ve PDF içeriğinde arama
- Wi‑Fi, Bluetooth, ses, ekran görüntüsü ve ayarlar için sistem komutları

## Sistem gereksinimi

- Pardus 25 x86_64 Gnome
- İlk yapay zekâ kurulumu ve web sonuçları için internet bağlantısı

## Kurulum

1. En son SearchPars sürümünü [Relases kısmından](https://github.com/techasl7585/searchpars/releases/latest)
   açın.
2. En Son Sürüm `SearchPars_Pardus.zip` dosyasını indirin.
3. ZIP dosyasına sağ tıklayıp **Buraya çıkart** seçeneğini kullanın.
4. Çıkan klasörde terminal açın.
5. Kurmak İçin Aşağıdaki Kodları Girin:

```text
chmod +x kur.sh
./kur.sh
```

Başka bir paket veya geliştirme aracı kurmanız gerekmez. Kurucu gerekli Pardus
bağımlılıklarını, Ollama'yı ve `qwen3.5:4b` yapay zekâ modelini sırayla kurar.
Model indirme ilerlemesi terminalde görünür ve model doğrulanmadan kurulum
tamamlandı mesajı verilmez. Model yaklaşık 3,4 GB olduğu için ilk kurulum
internet hızına göre zaman alabilir.


## Kullanım

Uygulamalar menüsünden **SearchPars**'ı açın. Örnek sorgular:

```text
19:19 da çektiğim ekran görüntüsü
teknofest
Bluetooth aç
Bugünkü dolar kuru
Ali Koç 
```
