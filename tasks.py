import json
import os
from datetime import datetime

# Her zaman bu script'in bulunduğu klasördeki tasks.json'u kullan
_KLASOR = os.path.dirname(os.path.abspath(__file__))
DOSYA = os.path.join(_KLASOR, "tasks.json")

GECERLI_ONCELIKLER = ["dusuk", "normal", "yuksek"]


def _simdi():
    return datetime.now().isoformat(timespec="seconds")


def gorevleri_yukle():
    """Aktif ve tamamlanmış görevleri döndür (arşivlenenler hariç)."""
    if not os.path.exists(DOSYA):
        return []
    with open(DOSYA, "r", encoding="utf-8") as f:
        try:
            gorevler = json.load(f)
        except json.JSONDecodeError:
            return []
    return [g for g in gorevler if g.get("durum", "aktif") != "arsivlendi"]


def arsivi_yukle():
    """Sadece arşivlenmiş görevleri döndür."""
    if not os.path.exists(DOSYA):
        return []
    with open(DOSYA, "r", encoding="utf-8") as f:
        try:
            gorevler = json.load(f)
        except json.JSONDecodeError:
            return []
    return [g for g in gorevler if g.get("durum") == "arsivlendi"]


def _tum_gorevleri_yukle():
    """Tüm görevleri döndür (iç kullanım için)."""
    if not os.path.exists(DOSYA):
        return []
    with open(DOSYA, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _tum_gorevleri_kaydet(gorevler):
    with open(DOSYA, "w", encoding="utf-8") as f:
        json.dump(gorevler, f, ensure_ascii=False, indent=2)


def gorev_ekle(baslik, oncelik="normal"):
    """Yeni görev ekle ve kaydet."""
    if not baslik or not baslik.strip():
        raise ValueError("Görev başlığı boş olamaz.")
    if len(baslik) > 200:
        raise ValueError("Görev başlığı 200 karakterden uzun olamaz.")
    if oncelik not in GECERLI_ONCELIKLER:
        raise ValueError(f"Geçersiz öncelik: '{oncelik}'. Seçenekler: {GECERLI_ONCELIKLER}")
    gorevler = _tum_gorevleri_yukle()
    yeni_id = max((g["id"] for g in gorevler), default=0) + 1
    yeni_gorev = {
        "id": yeni_id,
        "baslik": baslik,
        "oncelik": oncelik,
        "durum": "aktif",
        "olusturulma": _simdi(),
        "tamamlanma": None,
        "arsivlenme": None,
    }
    gorevler.append(yeni_gorev)
    _tum_gorevleri_kaydet(gorevler)
    return yeni_gorev


def gorev_tamamla(gorev_id):
    """Görevi tamamlandı olarak işaretle."""
    gorevler = _tum_gorevleri_yukle()
    for gorev in gorevler:
        if gorev["id"] == gorev_id:
            gorev["durum"] = "tamamlandi"
            gorev["tamamlandi"] = True
            gorev.setdefault("tamamlanma", None)
            gorev["tamamlanma"] = _simdi()
            _tum_gorevleri_kaydet(gorevler)
            return True
    return False


def gorev_arsivle(gorev_id):
    """Görevi arşivle (soft delete)."""
    gorevler = _tum_gorevleri_yukle()
    for gorev in gorevler:
        if gorev["id"] == gorev_id:
            gorev["durum"] = "arsivlendi"
            gorev.setdefault("arsivlenme", None)
            gorev["arsivlenme"] = _simdi()
            _tum_gorevleri_kaydet(gorevler)
            return True
    return False


def gorev_aktife_al(gorev_id):
    """Tamamlanmış veya arşivlenmiş görevi tekrar aktife çeker."""
    gorevler = _tum_gorevleri_yukle()
    for gorev in gorevler:
        if gorev["id"] == gorev_id:
            gorev["durum"] = "aktif"
            gorev["tamamlanma"] = None
            gorev["arsivlenme"] = None
            _tum_gorevleri_kaydet(gorevler)
            return True
    return False
