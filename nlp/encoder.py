"""
Encoder arayüzü ve stub implementasyonu.

Gerçek model mevcut değilken karakter n-gram + kosinüs benzerliği
ile çalışan bir stub kullanılır. Gerçek model entegre edildiğinde
sadece _gercek_model_yukle() implementasyonu değişir, arayüz aynı kalır.

Gerçek model için:  MoritzLaurer/mDeBERTa-v3-base-mnli-xnli (~280MB)
Öneri:              sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (~420MB)
"""
import re
import math
from typing import Optional
import numpy as np

# Gerçek model hazır olduğunda True yapılır
_GERCEK_MODEL_URL = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

# Niyet başına referans cümleler — Türkçe örnekler
# Daha fazla örnek eklenirse n-gram benzerliği iyileşir.
_NIYET_REFERANS = {
    "gorev_ekle": [
        "yeni görev ekle oluştur kaydet",
        "hatırlat unutma not al yapılacak",
        "iş ekle planlı görev koy",
        "toplantı randevu etkinlik ekle",
        "rapor teslim sunum hazırla",
        "mail yaz cevapla ara",
    ],
    "gorev_tamamla": [
        "tamamla bitti yaptım hallettim bitirdim",
        "tamam done kapat bitir tamamlandı",
        "görevi tamamla işi bitir hallettim",
    ],
    "gorev_arsivle": [
        "arşivle kaldır sil iptal et",
        "arşivlendi iptal artık gerekmiyor",
    ],
    "gorev_listele": [
        "listele göster tümünü hepsini",
        "ne var neler var görevlerim liste",
        "tüm görevleri göster aktif görevler",
    ],
    "gorev_ara": [
        "ara bul filtrele hangi görev",
        "arama yap belirli görev bul",
        "filtrele öncelikli etiketli",
    ],
}


def _ngram_vektoru(metin: str, n: int = 3) -> dict[str, int]:
    """Karakter n-gramlarını frekans sözlüğü olarak döndürür."""
    metin = re.sub(r"\s+", " ", metin.lower().strip())
    return {metin[i:i+n]: 1 for i in range(len(metin) - n + 1)}


def _kosinüs(a: dict, b: dict) -> float:
    ortak = set(a) & set(b)
    if not ortak:
        return 0.0
    paylasim = sum(a[k] * b[k] for k in ortak)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    return paylasim / (norm_a * norm_b) if norm_a * norm_b > 0 else 0.0


def _stub_siniflandir(girdi: str) -> dict:
    """
    Karakter n-gram benzerliğiyle niyet sınıflandırması (stub).
    Gerçek encoder yokken kullanılır.
    """
    girdi_vek = _ngram_vektoru(girdi)
    skorlar = {}

    for niyet, referanslar in _NIYET_REFERANS.items():
        niyet_skoru = max(
            _kosinüs(girdi_vek, _ngram_vektoru(ref))
            for ref in referanslar
        )
        skorlar[niyet] = niyet_skoru

    en_iyi = max(skorlar, key=skorlar.get)
    max_skor = skorlar[en_iyi]

    # Skoru 0-1 arasında normalize et (max gözlem ~0.4-0.6 civarı)
    guven = round(min(max_skor * 1.8, 0.88), 4)

    return {
        "niyet": en_iyi,
        "guven": guven,
        "skorlar": {k: round(v, 4) for k, v in sorted(skorlar.items(), key=lambda x: -x[1])},
        "mod": "stub",
    }


class Encoder:
    """
    Niyet sınıflandırıcısı.

    Gerçek model yolu verilmezse stub (n-gram benzerlik) kullanır.
    Gerçek model entegre edilince:
        enc = Encoder(model_yolu="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")
    """

    def __init__(self, model_yolu: Optional[str] = None):
        self._model_yolu = model_yolu
        self._pipeline = None
        self._gercek = False

    def _yukle(self) -> bool:
        """Gerçek modeli yüklemeyi dener. Başarısızsa False döner."""
        if self._gercek:
            return True
        if not self._model_yolu:
            return False
        try:
            from transformers import pipeline
            self._pipeline = pipeline(
                "zero-shot-classification",
                model=self._model_yolu,
                device="cpu",
            )
            self._gercek = True
            return True
        except Exception:
            return False

    def _gercek_siniflandir(self, girdi: str) -> dict:
        niyetler = list(_NIYET_REFERANS.keys())
        etiketler = {
            "gorev_ekle": "yeni görev ekleme veya oluşturma",
            "gorev_tamamla": "görevi tamamlama veya bitirme",
            "gorev_arsivle": "görevi arşivleme veya silme",
            "gorev_listele": "görevleri listeleme veya gösterme",
            "gorev_ara": "görev arama veya filtreleme",
        }
        sonuc = self._pipeline(
            girdi,
            list(etiketler.values()),
            hypothesis_template="Bu metin {} içeriyor.",
        )
        etiket_ters = {v: k for k, v in etiketler.items()}
        return {
            "niyet": etiket_ters[sonuc["labels"][0]],
            "guven": round(sonuc["scores"][0], 4),
            "skorlar": {
                etiket_ters[l]: round(s, 4)
                for l, s in zip(sonuc["labels"], sonuc["scores"])
            },
            "mod": "gercek",
        }

    def siniflandir(self, girdi: str) -> dict:
        """
        Girdiyi niyet kategorisine sınıflandırır.
        Gerçek model yüklüyse onu, değilse stub'ı kullanır.
        """
        if self._yukle():
            return self._gercek_siniflandir(girdi)
        return _stub_siniflandir(girdi)

    @property
    def mod(self) -> str:
        return "gercek" if self._gercek else "stub"


# Varsayılan örnek — gerçek model URL'i verilmeden oluşturulur
_varsayilan = Encoder()


def siniflandir(girdi: str) -> dict:
    """Modül seviyesi kısayol."""
    return _varsayilan.siniflandir(girdi)
