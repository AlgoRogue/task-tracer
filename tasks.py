import json
import os

DOSYA = "tasks.json"
GECERLI_ONCELIKLER = ["dusuk", "normal", "yuksek"]


def gorevleri_yukle():
    """Dosyadan görevleri oku. Dosya yoksa veya bozuksa boş liste döndür."""
    if not os.path.exists(DOSYA):
        return []
    with open(DOSYA, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def gorevleri_kaydet(gorevler):
    """Görev listesini dosyaya yaz."""
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
    gorevler = gorevleri_yukle()
    yeni_id = max((g["id"] for g in gorevler), default=0) + 1
    yeni_gorev = {
        "id": yeni_id,
        "baslik": baslik,
        "oncelik": oncelik,
        "tamamlandi": False
    }
    gorevler.append(yeni_gorev)
    gorevleri_kaydet(gorevler)
    return yeni_gorev


def gorev_tamamla(gorev_id):
    """Görevi tamamlandı olarak işaretle."""
    gorevler = gorevleri_yukle()
    for gorev in gorevler:
        if gorev["id"] == gorev_id:
            gorev["tamamlandi"] = True
            gorevleri_kaydet(gorevler)
            return True
    return False  # Görev bulunamadı


def gorev_sil(gorev_id):
    """Görevi listeden çıkar."""
    gorevler = gorevleri_yukle()
    yeni_liste = [g for g in gorevler if g["id"] != gorev_id]
    if len(yeni_liste) == len(gorevler):
        return False  # Silinecek görev bulunamadı
    gorevleri_kaydet(yeni_liste)
    return True
