"""
Güven kapısı — yorumun güven skoruna göre ne yapılacağına karar verir.

Eşikler:
  guven >= 0.9  → direkt_uygula
  0.6 <= g < 0.9 → onay_iste  (did you mean?)
  guven < 0.6   → acikla      (anlayamadım)
"""

_ESIK_DIREKT = 0.9
_ESIK_ONAY = 0.6

_NIYET_ETIKET = {
    "gorev_ekle": "Görev ekle",
    "gorev_tamamla": "Tamamla",
    "gorev_arsivle": "Arşivle",
    "gorev_listele": "Listele",
    "gorev_ara": "Ara",
}


def _did_you_mean(yorum: dict) -> str:
    niyet = yorum.get("niyet", "gorev_ekle")
    etiket = _NIYET_ETIKET.get(niyet, niyet)
    parcalar = [etiket]

    if yorum.get("baslik"):
        parcalar.append(f'"{yorum["baslik"]}"')
    if yorum.get("tarih"):
        parcalar.append(yorum["tarih"])
    if yorum.get("oncelik") and yorum["oncelik"] != "normal":
        parcalar.append(yorum["oncelik"])
    if yorum.get("etiketler"):
        parcalar.append(", ".join(f"#{e}" for e in yorum["etiketler"]))

    return " → ".join(parcalar) + " — bunu mu demek istediniz? (e/h)"


def karar_ver(yorum: dict) -> dict:
    """
    Dönen dict:
      eylem   : 'direkt_uygula' | 'onay_iste' | 'acikla'
      yorum   : orijinal yorum (her zaman dahil)
      mesaj   : kullanıcıya gösterilecek metin (onay_iste ve acikla için)
    """
    guven = yorum.get("guven", 0.0)

    if guven >= _ESIK_DIREKT:
        return {"eylem": "direkt_uygula", "yorum": yorum}

    if guven >= _ESIK_ONAY:
        return {
            "eylem": "onay_iste",
            "yorum": yorum,
            "mesaj": _did_you_mean(yorum),
        }

    return {
        "eylem": "acikla",
        "yorum": yorum,
        "mesaj": "Anlayamadım. Ne yapmak istersiniz? (örn: 'yarın toplantı ekle')",
    }
