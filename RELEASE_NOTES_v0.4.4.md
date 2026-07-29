# SearchPars v0.4.4

Bu sürüm, kararsız ve ölçülü internet bağlantılarında yapay zekâ modeli
kurulumunu güvenilir hâle getirir.

## Düzeltilenler

- Model indirme işlemi artık `ollama pull` ilerleme döngüsüne bırakılmaz.
- Her blob tek ve sıralı bir `.searchpars-part` dosyasına indirilir.
- Bağlantı kesilirse mevcut dosya silinmeden HTTP Range ile aynı bayttan devam
  edilir.
- Terminalde sıfırlanmayan gerçek toplam model yüzdesi gösterilir.
- İndirilen her dosyanın boyutu ve SHA-256 özeti doğrulanır.
- Model zaten kuruluysa yeniden indirilmez.

Ollama program arşivi için kullanılan devam edebilen indirme yöntemi de
korunmuştur.
