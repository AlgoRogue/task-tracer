"""
Encoder arayüzü ve stub implementasyonu.

Gerçek model mevcut değilken karakter n-gram + kosinüs benzerliği
ile çalışan bir stub kullanılır. Gerçek model yüklendiğinde
sentence-transformers ile embedding tabanlı benzerlik hesaplanır.

Model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (~420MB)
"""
import re
import math
import numpy as np
from typing import Optional


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
        "görevi arşivle arşive taşı kaldır",
        "artık gerekmiyor arşive al devre dışı",
        "iptal et vazgeç arşivle bitir",
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
    girdi_vek = _ngram_vektoru(girdi)
    skorlar = {}

    for niyet, referanslar in _NIYET_REFERANS.items():
        niyet_skoru = max(
            _kosinüs(girdi_vek, _ngram_vektoru(ref))
            for ref in referanslar
        )
        skorlar[niyet] = niyet_skoru

    en_iyi = max(skorlar, key=skorlar.get)
    guven = round(min(skorlar[en_iyi] * 1.8, 0.88), 4)

    return {
        "niyet": en_iyi,
        "guven": guven,
        "skorlar": {k: round(v, 4) for k, v in sorted(skorlar.items(), key=lambda x: -x[1])},
        "mod": "stub",
    }


def _kosinüs_np(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a (1D vektör) ile b (2D matris) satırları arasında kosinüs benzerliği."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b, axis=1)
    if norm_a == 0:
        return np.zeros(len(b))
    return np.dot(b, a) / (norm_b * norm_a + 1e-10)


class Encoder:
    """
    Niyet sınıflandırıcısı.

    Model yüklenirse sentence-transformers ile embedding benzerliği kullanır,
    yoksa karakter n-gram stub'a düşer.

        enc = Encoder(model_yolu="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    """

    def __init__(self, model_yolu: Optional[str] = None):
        self._model_yolu = model_yolu
        self._model = None
        self._ref_embeddings: dict[str, np.ndarray] = {}
        self._gercek = False

    def _yukle(self) -> bool:
        """Modeli yüklemeyi dener, referans embedding'leri önceden hesaplar."""
        if self._gercek:
            return True
        if not self._model_yolu:
            return False
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_yolu)
            self._ref_embeddings = {
                niyet: self._model.encode(referanslar, convert_to_numpy=True)
                for niyet, referanslar in _NIYET_REFERANS.items()
            }
            self._gercek = True
            return True
        except Exception:
            return False

    def _gercek_siniflandir(self, girdi: str) -> dict:
        girdi_emb = self._model.encode(girdi, convert_to_numpy=True)
        skorlar = {
            niyet: float(_kosinüs_np(girdi_emb, ref_embs).max())
            for niyet, ref_embs in self._ref_embeddings.items()
        }
        en_iyi = max(skorlar, key=skorlar.get)
        return {
            "niyet": en_iyi,
            "guven": round(min(skorlar[en_iyi], 0.95), 4),
            "skorlar": {k: round(v, 4) for k, v in sorted(skorlar.items(), key=lambda x: -x[1])},
            "mod": "gercek",
        }

    def siniflandir(self, girdi: str) -> dict:
        """Girdiyi niyet kategorisine sınıflandırır."""
        if self._yukle():
            return self._gercek_siniflandir(girdi)
        return _stub_siniflandir(girdi)

    @property
    def mod(self) -> str:
        return "gercek" if self._gercek else "stub"


from nlp import model_ayar as _ma
_varsayilan = Encoder(model_yolu=_ma.model_yolu_bul())


def siniflandir(girdi: str) -> dict:
    """Modül seviyesi kısayol."""
    return _varsayilan.siniflandir(girdi)
