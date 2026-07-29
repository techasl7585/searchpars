# SearchPars v0.3.0

Pardus 25 x86_64 için yapay zekâ destekli birleşik masaüstü araması.

## Son kullanıcı kurulumu

1. Aşağıdaki **Assets** bölümünden `SearchPars_0.3.0_amd64.deb` dosyasını indirin.
2. Dosyaya çift tıklayın.
3. Pardus Paket Kurucu açıldığında **Kur** seçeneğini kullanın.

Terminal seçeneği:

```bash
cd ~/İndirilenler
sudo apt install ./SearchPars_0.3.0_amd64.deb
```

Kullanıcının Python, GTK, Ollama veya yapay zekâ modelini ayrı ayrı kurması
gerekmez. Pardus bağımlılıkları paket yöneticisi tarafından kurulur. Ollama ve
`qwen3.5:4b` modeli kurulumdan sonra arka planda otomatik hazırlanır.

## Gereksinimler

- Pardus 25 x86_64
- En az 8 GB RAM önerilir
- Yapay zekâ modeli için yaklaşık 5 GB boş disk
- İlk model kurulumu ve web araması için internet

## Öne çıkanlar

- Doğal dille dosya, içerik, tür, klasör ve tarih araması
- Uygulama bulma ve doğrudan başlatma
- DuckDuckGo ve Türkçe Wikipedia web sonuçları
- TCMB üzerinden güncel döviz bilgisi
- Sağ panelde ayrıntılı, kaynaklı yapay zekâ cevapları
- Ollama ile bilgisayarda çalışan yerel yapay zekâ

> **Code → Download ZIP** kaynak koddur. Son kullanıcı kurulumu için
> Releases bölümündeki `.deb` dosyasını indirin.
