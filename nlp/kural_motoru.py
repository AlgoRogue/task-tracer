"""Türkçe görev yönetimi komutları için kural tabanlı NLU motoru."""
import re
from datetime import date, timedelta
import calendar

# --- sabitler ---

_GUNLER_TR = {
    "pazartesi": 0, "salı": 1, "çarşamba": 2,
    "perşembe": 3, "cuma": 4, "cumartesi": 5, "pazar": 6,
}

_SAYI_KELIMELERI = {
    "bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5,
    "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10,
    "on bir": 11, "on iki": 12, "on beş": 15, "yirmi": 20, "otuz": 30,
}

# Sıra önemli: uzun/özgül desenler kısa/genel desenlerden önce gelmeli.
_ONCELIK_KURALLARI = [
    ("çok acil", "yuksek"),
    ("en acil", "yuksek"),
    ("çok önemli", "yuksek"),
    ("yüksek öncelikli", "yuksek"),
    ("düşük öncelikli", "dusuk"),  # "öncelikli"den önce gelmeli
    ("az önemli", "dusuk"),
    ("fırsatta", "dusuk"),
    ("bekleyebilir", "dusuk"),
    ("acil", "yuksek"),
    ("önemli", "yuksek"),
    ("öncelikli", "yuksek"),
    ("urgent", "yuksek"),
    ("düşük", "dusuk"),  # "düşük öncelikli"den sonra gelmeli
    ("normal", "normal"),
    ("orta", "normal"),
    ("standart", "normal"),
]

_NIYET_TAMAMLA = [
    "tamamlandı", "tamamla", "bitti", "yaptım", "hallettim",
    "bitirdim", "tamam", "done", "bitir", "kapat",
]
_NIYET_ARSIVLE = ["arşivlendi", "arşivle", "iptal et", "iptal", "kaldır"]
_NIYET_LISTELE = [
    "tümünü göster", "hepsini göster", "listele", "göster",
    "liste", "ne var", "neler var",
]
_NIYET_ARA = ["filtrele", "search", "hangi", "bul", "ara"]
_NIYET_EKLE = ["ekle", "oluştur", "hatırlat", "unutma", "not al", "kaydet", "yap"]


# --- yardımcı fonksiyonlar ---

def _sayi_cevir(s: str) -> int:
    try:
        return int(s)
    except ValueError:
        return _SAYI_KELIMELERI.get(s.strip().lower(), 1)


def _sonraki_gun(ref: date, hedef_gun: int) -> date:
    """Verilen haftanın gününün bir sonraki tarihini döndürür (min 1 gün ilerisi)."""
    fark = (hedef_gun - ref.weekday()) % 7
    if fark == 0:
        fark = 7
    return ref + timedelta(days=fark)


def _tarih_cikart(metin_lower: str, ref: date):
    """(YYYY-MM-DD, eşleşen_metin) veya None döndürür."""

    # ISO: 2026-05-01
    m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', metin_lower)
    if m:
        return (m.group(1), m.group(0))

    # TR format: 01.05.2026 veya 01/05/2026
    m = re.search(r'\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b', metin_lower)
    if m:
        try:
            resolved = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return (str(resolved), m.group(0))
        except ValueError:
            pass

    # Bugün
    if re.search(r'\b(bugün|bu gün)\b', metin_lower):
        return (str(ref), "bugün")

    # Yarın
    if re.search(r'\byarın\b', metin_lower):
        return (str(ref + timedelta(days=1)), "yarın")

    # Öbür gün
    if re.search(r'\b(öbür gün|öbürgün)\b', metin_lower):
        return (str(ref + timedelta(days=2)), "öbür gün")

    # N gün sonra
    sayi_desen = r'(\d+|bir|iki|üç|dört|beş|altı|yedi|sekiz|dokuz|on)'
    m = re.search(sayi_desen + r'\s*gün\s*sonra', metin_lower)
    if m:
        return (str(ref + timedelta(days=_sayi_cevir(m.group(1)))), m.group(0))

    # N hafta sonra
    m = re.search(sayi_desen + r'\s*hafta\s*sonra', metin_lower)
    if m:
        return (str(ref + timedelta(weeks=_sayi_cevir(m.group(1)))), m.group(0))

    # Hafta sonu → Cumartesi
    if re.search(r'\b(hafta sonu|haftasonu)\b', metin_lower):
        return (str(_sonraki_gun(ref, 5)), "hafta sonu")

    # Gelecek hafta / önümüzdeki hafta → gelecek Pazartesi
    if re.search(r'\b(gelecek hafta|önümüzdeki hafta)\b', metin_lower):
        return (str(ref + timedelta(days=7 - ref.weekday())), "gelecek hafta")

    # Bu hafta → bu haftanın Cuması
    if re.search(r'\b(bu hafta|bu haftaya kadar|bu hafta içinde)\b', metin_lower):
        fark = (4 - ref.weekday()) % 7 or 7
        return (str(ref + timedelta(days=fark)), "bu hafta")

    # Ay sonu
    if re.search(r'\b(ay sonu|ayın sonu|ay sonunda)\b', metin_lower):
        son_gun = calendar.monthrange(ref.year, ref.month)[1]
        return (str(date(ref.year, ref.month, son_gun)), "ay sonu")

    # Gün adları (uzun → kısa sıralamayla çakışmayı önle)
    for gun_adi in sorted(_GUNLER_TR.keys(), key=len, reverse=True):
        if re.search(rf'\b{gun_adi}\b', metin_lower):
            return (str(_sonraki_gun(ref, _GUNLER_TR[gun_adi])), gun_adi)

    return None


def _oncelik_cikart(metin_lower: str):
    """(oncelik_degeri, eşleşen_metin | None) döndürür."""
    for kw, deger in _ONCELIK_KURALLARI:
        if re.search(rf'\b{re.escape(kw)}\b', metin_lower):
            return (deger, kw)
    return ("normal", None)


def _niyet_cikart(metin_lower: str):
    """(niyet, eşleşen_metin | None) döndürür."""
    for liste, niyet in [
        (_NIYET_TAMAMLA, "gorev_tamamla"),
        (_NIYET_ARSIVLE, "gorev_arsivle"),
        (_NIYET_LISTELE, "gorev_listele"),
        (_NIYET_ARA, "gorev_ara"),
        (_NIYET_EKLE, "gorev_ekle"),
    ]:
        for kw in sorted(liste, key=len, reverse=True):
            if re.search(rf'\b{re.escape(kw)}\b', metin_lower):
                return (niyet, kw)
    return ("gorev_ekle", None)


def _etiket_cikart(metin: str):
    """#kelime formatındaki etiketleri çıkarır."""
    return re.findall(r'#(\w+)', metin)


def _metni_maskele(metin: str, cikartilan: str) -> str:
    """Metinden belirli bir ifadeyi kaldırır, çoklu boşlukları temizler."""
    if not cikartilan:
        return metin
    temiz = re.sub(re.escape(cikartilan), ' ', metin, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', temiz).strip()


def _guven_hesapla(niyet: str, tarih, oncelik_acik: bool,
                   niyet_acik: bool, baslik: str) -> float:
    if niyet in ("gorev_listele", "gorev_ara"):
        return 0.90

    if niyet in ("gorev_tamamla", "gorev_arsivle"):
        return 0.70

    # gorev_ekle
    guven = 0.55
    if niyet_acik:
        guven += 0.15
    if tarih:
        guven += 0.10
    if oncelik_acik:
        guven += 0.10
    if baslik and len(baslik) > 2:
        guven += 0.10
    return min(round(guven, 2), 0.95)


# --- ana fonksiyon ---

def yorumla(girdi: str, _bugun: date = None) -> dict:
    """
    Türkçe doğal dil girdisini yapısal göreve dönüştürür.

    Dönen dict:
        niyet       : gorev_ekle | gorev_tamamla | gorev_arsivle | gorev_listele | gorev_ara
        baslik      : str | None
        tarih       : YYYY-MM-DD | None
        oncelik     : dusuk | normal | yuksek
        etiketler   : list[str]
        guven       : float  (0.0 – 1.0)
        ham_girdi   : str
    """
    ref = _bugun or date.today()
    metin = girdi.strip()
    kalanlar = metin

    # 1. Etiketler (#kelime)
    etiketler = _etiket_cikart(metin)
    for e in etiketler:
        kalanlar = re.sub(rf'#\w*{re.escape(e)}\w*', ' ', kalanlar)
    kalanlar = re.sub(r'\s+', ' ', kalanlar).strip()

    # 2. Tarih
    tarih_sonuc = _tarih_cikart(kalanlar.lower(), ref)
    tarih = None
    if tarih_sonuc:
        tarih, tarih_eslesme = tarih_sonuc
        kalanlar = _metni_maskele(kalanlar, tarih_eslesme)

    # 3. Öncelik
    oncelik, oncelik_eslesme = _oncelik_cikart(kalanlar.lower())
    oncelik_acik = oncelik_eslesme is not None
    if oncelik_acik:
        kalanlar = _metni_maskele(kalanlar, oncelik_eslesme)

    # 4. Niyet
    niyet, niyet_eslesme = _niyet_cikart(kalanlar.lower())
    niyet_acik = niyet_eslesme is not None
    if niyet_acik:
        kalanlar = _metni_maskele(kalanlar, niyet_eslesme)

    # 5. Başlık = kalan metin
    baslik = re.sub(r'\s+', ' ', kalanlar).strip() or None

    # 6. Güven
    guven = _guven_hesapla(niyet, tarih, oncelik_acik, niyet_acik, baslik or "")

    return {
        "niyet": niyet,
        "baslik": baslik,
        "tarih": tarih,
        "oncelik": oncelik,
        "etiketler": etiketler,
        "guven": guven,
        "ham_girdi": girdi,
    }
