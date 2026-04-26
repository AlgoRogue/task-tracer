"""Kullanıcı onaylı desenleri saklar ve benzer girdiler için güven günceller."""
import json
from difflib import SequenceMatcher
import tasks


_ESLESME_ESIGI = 0.55  # bu değerin altındaki benzerlik skorları göz ardı edilir


def _benzerlik(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def en_iyi_eslesmesi_bul(girdi: str) -> dict | None:
    """
    Desen hafızasında en çok benzeyen girdiyi bulur.
    Benzerlik skoru _ESLESME_ESIGI'nin altındaysa None döner.
    Dönen dict: desen kaydı + 'benzerlik' alanı.
    """
    desenleri = tasks.desen_listele()
    if not desenleri:
        return None

    en_iyi = None
    en_yuksek = 0.0
    for d in desenleri:
        skor = _benzerlik(girdi, d["ham_girdi"])
        if skor > en_yuksek:
            en_yuksek = skor
            en_iyi = d

    if en_yuksek < _ESLESME_ESIGI:
        return None

    return {**en_iyi, "benzerlik": round(en_yuksek, 4)}


def kural_ile_birlestir(girdi: str, kural_yorumu: dict) -> dict:
    """
    Kural motoru çıktısını desen hafızasıyla zenginleştirir.

    Arbitrasyon kuralı:
      benzerlik >= 0.9  → desen hafızası kazanır
      0.55 <= ben < 0.9 → güven ortalaması alınır
      ben < 0.55        → kural motoru sonucu aynen döner
    """
    eslesme = en_iyi_eslesmesi_bul(girdi)
    if eslesme is None:
        return kural_yorumu

    ben = eslesme["benzerlik"]
    desen_guven = eslesme["guven"]
    desen_niyet = json.loads(eslesme["niyet"])

    kural_niyet = kural_yorumu.get("niyet")
    desen_niyet_str = desen_niyet.get("niyet")

    if ben >= 0.9 and desen_niyet_str == kural_niyet:
        # Yüksek benzerlik ve aynı niyet → desen hafızası kazanır
        return {
            **kural_yorumu,
            **desen_niyet,
            "guven": min(desen_guven * ben, 0.97),
            "ham_girdi": kural_yorumu["ham_girdi"],
            "_desen_id": eslesme["id"],
        }

    if desen_niyet_str == kural_niyet:
        # Orta benzerlik, aynı niyet → güven ortalaması alınır
        karisik_guven = round((kural_yorumu["guven"] + desen_guven * ben) / 2, 4)
        return {
            **kural_yorumu,
            "guven": karisik_guven,
            "_desen_id": eslesme["id"],
        }

    # Niyet farklı → kural motoru sonucu korunur, desen_id eklenir
    return {**kural_yorumu, "_desen_id": eslesme["id"]}
