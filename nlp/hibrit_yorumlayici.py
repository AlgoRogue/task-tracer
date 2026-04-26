"""
Hibrit yorumlayıcı: kural motoru + encoder birlikte çalışır.

Karar mantığı:
  - Encoder güveni > kural güveni VE farklı niyet → encoder kazanır
  - İkisi aynı niyette → güven ortalaması alınır (hafifçe artış)
  - Encoder düşük güven → kural motoru sonucu korunur
"""
from nlp import kural_motoru
from nlp.encoder import Encoder

_ENCODER_ESIGI = 0.45   # Encoder bu eşiğin altındaysa göz ardı edilir
_varsayilan_encoder = Encoder()


def yorumla(girdi: str, encoder: Encoder = None, _bugun=None) -> dict:
    """
    Kural motoru + encoder çıktısını birleştirerek nihai yorumu döndürür.
    Dönen dict kural_motoru.yorumla() ile aynı formattadır + '_encoder' alanı.
    """
    enc = encoder or _varsayilan_encoder

    # 1. Kural motoru
    kural = kural_motoru.yorumla(girdi, _bugun=_bugun)

    # 2. Encoder
    try:
        enc_sonuc = enc.siniflandir(girdi)
    except Exception:
        return {**kural, "_encoder": None}

    enc_niyet = enc_sonuc["niyet"]
    enc_guven = enc_sonuc["guven"]

    # 3. Birleştirme
    kural_niyet = kural["niyet"]
    kural_guven = kural["guven"]

    if enc_guven < _ENCODER_ESIGI:
        # Encoder çok belirsiz — kural motoru kazanır
        nihai_niyet = kural_niyet
        nihai_guven = kural_guven
        karar = "kural"

    elif enc_niyet == kural_niyet:
        # İkisi aynı niyette — güven hafifçe artar
        nihai_niyet = kural_niyet
        nihai_guven = round(min(kural_guven + (enc_guven * 0.1), 0.95), 4)
        karar = "uyusma"

    elif enc_guven > kural_guven + 0.15:
        # Encoder belirgin biçimde daha güvenli ve farklı niyet → encoder kazanır
        nihai_niyet = enc_niyet
        nihai_guven = round((kural_guven + enc_guven) / 2, 4)
        karar = "encoder"

    else:
        # Yakın güven ama farklı niyet — kural motorunu koru
        nihai_niyet = kural_niyet
        nihai_guven = kural_guven
        karar = "kural"

    return {
        **kural,
        "niyet": nihai_niyet,
        "guven": nihai_guven,
        "_encoder": {
            "niyet": enc_niyet,
            "guven": enc_guven,
            "mod": enc_sonuc.get("mod", "?"),
            "karar": karar,
        },
    }
