# SearchPars v0.4.3

Kararsız internet bağlantıları için kurulum dayanıklılığı geliştirildi.

- Ollama arşivi `/var/cache/searchpars` altında indirilir.
- Bağlantı kesilirse tamamlanan bölüm silinmez.
- İndirme otomatik olarak 10 defaya kadar tekrar denenir.
- Kurucu yeniden çalıştırıldığında Ollama indirmesi kaldığı yerden sürer.
- Yapay zekâ modeli indirmesi de 10 defaya kadar tekrar denenir.
- İndirme tamamlanmadan veya model doğrulanmadan başarı mesajı verilmez.
