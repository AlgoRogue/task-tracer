# Task-Tracer — Geliştirme Notu

## Projeye Genel Bakış

Task-Tracer, Türkçe doğal dil girdisiyle çalışan, tamamen yerel bir görev yönetimi uygulamasıdır. Kullanıcı "yarın sabah toplantı var, acil" gibi serbest metin girerek görev oluşturabilir; sistem bu girdiyi yapısal veriye dönüştürür, kaydeder ve akıllı hatırlatmalar üretir.

**Temel tasarım kararları:**
- Tüm veri kullanıcının cihazında kalır (SQLite, sıfır bulut bağımlılığı)
- Harici API veya LLM servisi kullanılmaz
- Model inference CPU'da çalışır, GPU gerektirmez
- Test güdümlü geliştirme (TDD) — her özellik önce testleriyle yazılır

---

## Tamamlanan Geliştirmeler

### Temel Katman (main branch)

Projenin ilk altı özelliği tamamlanmış ve main'e alınmış durumdadır:

| Özellik | Açıklama |
|---------|----------|
| Görev CRUD | Oluşturma, düzenleme, tamamlama, arşivleme, kalıcı silme |
| Etiket sistemi | `#kelime` formatıyla etiketleme ve filtreleme |
| Arama | Başlık, öncelik ve etikete göre filtreleme |
| Web arayüzü | FastAPI + Jinja2 tabanlı HTML arayüzü |
| CLI çıktısı | Colorama ile renkli terminal görünümü |
| Validasyon & refactoring | Edge-case yönetimi, DB migration altyapısı |

---

### Phase 1 — Çok-Ajanlı Mimari

**Amaç:** Sistem gözlemlemeyi, bildirim üretmeyi ve periyodik hesaplamaları merkezi bir döngüden değil, birbirinden bağımsız, sorumlulukları net ayrılmış ajanlardan yönetmek.

**Mimari:**
```
Kullanıcı (CLI / Web / API)
        │
        ▼
  Orkestratör — agents/__init__.py
        │
   ┌────┼─────────────────┐
   ▼    ▼    ▼    ▼       ▼
Giriş Skor  Hat. Takvim Öncelik
        │
    tasks.py → SQLite
```

Ajanlar **durumsuz**; tüm durum veritabanında tutulur. Ajanlar birbirini doğrudan çağırmaz.

**Eklenen bileşenler:**

| Bileşen | Görev |
|---------|-------|
| `agents/base.py` | Tüm ajanların türediği soyut temel sınıf |
| `agents/giris.py` | Görev başlığı, öncelik ve etiket normalizasyonu |
| `agents/skor.py` | Günlük tamamlanma oranı ve seri hesabı |
| `agents/hatirlatma.py` | Gecikmiş / bugün / yarın bildirim üretimi (tekrar önlemeli) |
| `agents/takvim.py` | Aynı güne düşen çakışma tespiti ve günlük iş yükü skoru |
| `agents/oncelik.py` | Deadline'a kalan süreye göre aciliyet skoru |
| `agents/__init__.py` | `run_all_agents()` ve tekil ajan çalıştırma |

**Yeni DB tabloları:** `bildirimler` (v2), `skor_gecmisi` (v3), `ajan_olaylari` (v4)

**Yeni API endpoint'leri:** `/bildirimler`, `/bildirimler/{id}/goruldu`, `/skor`, `/skor/gecmis`, `/ajanlar/calistir`, `/ajanlar/olaylar`

---

### Phase 2a — Kural Tabanlı NLU Katmanı

**Amaç:** Kullanıcının serbest metin girdisini yapısal göreve dönüştürmek; sistem önceki onaylardan öğrenerek zamanla daha doğru yorumlar yapmak.

**Pipeline:**
```
Girdi
  │
  ▼
KuralMotoru         → regex tabanlı niyet/tarih/öncelik çıkarımı
  │
  ▼
DesenhafizasiKontrol → kullanıcının geçmiş onaylarıyla eşleşme
  │
  ▼
BaglamCozucu        → "tamamla" gibi referanssız komutları session'dan tamamla
  │
  ▼
GuvenKapisi
  ≥ 0.9  →  direkt uygula
  0.6–0.9 → "bunu mu demek istediniz?" sor
  < 0.6  →  kullanıcıdan netleştirme iste
```

**Eklenen bileşenler:**

| Bileşen | Görev |
|---------|-------|
| `nlp/kural_motoru.py` | Türkçe regex motoru — tarih (15+ format), öncelik, niyet |
| `nlp/desen_hafizasi.py` | difflib tabanlı bulanık eşleşme; onay/red ile güven güncelleme |
| `nlp/session_context.py` | Oturum bağlamı — `son_gorev_id` 24s TTL ile SQLite'a yazılır |
| `nlp/baglam_cozucu.py` | Eksik hedef referansını SessionContext'ten otomatik doldurur |
| `nlp/guven_kapisi.py` | Güven eşiği mantığı ve "did you mean?" mesaj üretimi |

**Yeni DB tabloları:** `desen_hafizasi` (v5), `session_context` (v6)

**Öğrenme mekanizması:** Kullanıcı bir yorumu onayladığında `desen_hafizasi` tablosundaki güven skoru artar; reddedince düşer. Yeterli güven biriken desenleri sistem bir sonraki benzer girdide doğrudan uygular.

---

### Phase 2b — Encoder Model Altyapısı

**Amaç:** Kural motorunun kapsayamadığı serbest biçimli girdiler için makine öğrenmesi tabanlı niyet sınıflandırması; ancak gerçek model hazır olmadan da sistemin çalışmaya devam etmesi.

**Eklenen bileşenler:**

| Bileşen | Görev |
|---------|-------|
| `nlp/encoder.py` | `Encoder` sınıfı — gerçek model yüklüyse onu, yoksa n-gram stub'ı kullanır |
| `nlp/hibrit_yorumlayici.py` | Kural motoru + encoder çıktısını güven arbitrasyonuyla birleştirir |
| `nlp/model_ayar.py` | Model keşif sırası: env var → `models/encoder/` dizini → stub |
| `scripts/model_indir.py` | `python scripts/model_indir.py` ile tek komutla HuggingFace'den model indirir |

**Stub encoder:** Gerçek model olmadan karakter n-gram kosinüs benzerliğiyle çalışır. Doğruluk düşüktür; amacı arayüzü ve pipeline'ı sağlıklı tutmaktır.

**Gerçek model entegrasyonu (sıfır kod değişikliği):**
```bash
# Seçenek A — modeli indirip dizine koy
python scripts/model_indir.py
# Sonraki başlatmada models/encoder/ otomatik keşfedilir

# Seçenek B — env var ile HuggingFace'den canlı yükle
export ENCODER_MODEL_YOLU=MoritzLaurer/mDeBERTa-v3-base-mnli-xnli
```

**Seçilen model:** `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` — çok dilli, zero-shot sınıflandırma, CPU'da ~4s/istek, ~280MB disk.

**Hibrit arbitrasyon kuralı:**
```
encoder güveni > kural güveni + 0.15 → encoder kazanır
ikisi aynı niyette               → güven hafifçe artar
encoder < 0.45 eşiği             → kural motoru korunur
```

---

### Geri Bildirim Döngüsü — API Entegrasyonu

**Amaç:** NLU pipeline'ını API üzerinden erişilebilir hale getirmek ve kullanıcının onay/red kararını `desen_hafizasi`'na yazarak öğrenme döngüsünü kapatmak.

**Eklenen endpoint'ler:**

`POST /nl/yorumla`
```
Girdi:  { "girdi": "yarın saat 10 proje sunumu" }
Çıktı:  {
  "eylem": "onay_iste",
  "mesaj": "Yarın için 'proje sunumu' görevi eklemek mi?",
  "yorum": { "niyet": "gorev_ekle", "tarih": "2026-04-27", ... },
  "desen_id": 42
}
```

`POST /nl/geri-bildirim`
```
Girdi:  { "desen_id": 42, "onay": true }
Çıktı:  { "ok": true, "gorev": { "id": 17, "baslik": "Proje sunumu", ... } }
```

Bu iki endpoint birlikte tam konuşma döngüsünü kapatır: yorumla → kullanıcıya sor → onayla/reddet → uygula & öğren.

---

## Gizlilik Mimarisi

```
Kullanıcı cihazı
  ├── SQLite (gorevler, bildirimler, desen_hafizasi, session_context)
  ├── Encoder model (models/encoder/ — isteğe bağlı, yerel)
  └── NLU pipeline (tümüyle yerel, ağ bağlantısı yok)
```

- Telemetri: sıfır
- Kullanıcı verisi cihazdan çıkmaz
- Model: CPU'da çalışır, GPU gerektirmez
- Desen hafızası: kullanıcıya özel, başkasıyla paylaşılmaz

---

## Test Durumu

```
test_tasks.py   —  görev CRUD, migrasyon, validasyon
test_agents.py  —  5 ajan, orkestratör
test_nlp.py     —  kural motoru, desen hafızası, session, güven kapısı
test_api.py     —  tüm REST endpoint'leri

Toplam: 250 test, tümü geçiyor
```

---

## İlerleyen Süreçte Yapılacaklar

### Kısa Vadeli

**Encoder eğitim verisi üretimi**
Kural motorunun yeterince kapsayamadığı konuşma dili varyasyonları için sentetik eğitim verisi üretilecek:
- `data/uret_sentetik.py` — tarih × öncelik × konu kombinasyonları (~2.000 örnek)
- `data/egit_encoder.py` — fine-tuning pipeline (transformers Trainer API)
- Hedef: stub'ın yerini alacak, %85+ doğrulukla çalışan Türkçe niyet sınıflandırıcısı

### Orta Vadeli

**CLI konuşma modu**
`main.py`'a doğrudan doğal dil girişi; sistem onay ister, kullanıcı `e/h` ile yanıtlar, `desen_hafizasi` otomatik güncellenir.

**Web arayüzüne NL girişi**
Mevcut web arayüzüne `/nl/yorumla` endpoint'ini kullanan serbest metin kutusu eklenmesi; onay ekranı ve geri bildirim butonu.

### Uzun Vadeli

**Gönüllü veri toplama platformu (ayrı proje)**
Gerçek kullanıcı davranışından bağlamsal eğitim verisi toplamak için kurgusal senaryo tabanlı bir web sitesi. Kişisel veri toplanmaz; kullanıcı anonim senaryolar üzerinde çalışır.

---

## Geliştirme Ortamı

```bash
# Bağımlılıklar
pip install -r requirements.txt

# Testler
pytest test_tasks.py test_agents.py test_nlp.py test_api.py -v

# API sunucusu
uvicorn api:app --reload

# Encoder model (isteğe bağlı)
pip install huggingface-hub transformers torch --index-url https://download.pytorch.org/whl/cpu
python scripts/model_indir.py
```
