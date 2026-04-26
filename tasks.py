import sqlite3
import os
from datetime import datetime, date

_KLASOR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(_KLASOR, "tasks.db")

GECERLI_ONCELIKLER = ["dusuk", "normal", "yuksek"]
_ETIKET_MAX_UZUNLUK = 50

# Şema geçmişi: her entry (versiyon, SQL) çiftinden oluşur.
# Yeni sütun/değişiklik eklemek için buraya satır ekle, başka bir yere dokunma.
_MIGRASYONLAR = [
    (1, """
        CREATE TABLE IF NOT EXISTS gorevler (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            baslik      TEXT    NOT NULL,
            oncelik     TEXT    NOT NULL DEFAULT 'normal',
            durum       TEXT    NOT NULL DEFAULT 'aktif',
            olusturulma TEXT,
            tamamlanma  TEXT,
            arsivlenme  TEXT,
            son_tarih   TEXT,
            etiketler   TEXT
        )
    """),
]


def _simdi():
    return datetime.now().isoformat(timespec="seconds")


def _bugun():
    return str(date.today())


def _baglan():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def _init_db():
    with _baglan() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS __migrasyon__ (
                versiyon INTEGER PRIMARY KEY
            )
        """)
        uygulananlar = {r[0] for r in con.execute("SELECT versiyon FROM __migrasyon__").fetchall()}
        for versiyon, sql in _MIGRASYONLAR:
            if versiyon not in uygulananlar:
                con.executescript(sql)
                con.execute("INSERT INTO __migrasyon__ (versiyon) VALUES (?)", (versiyon,))


def db_versiyonu():
    """Uygulanmış en yüksek migrasyon versiyonunu döndürür."""
    _init_db()
    with _baglan() as con:
        row = con.execute("SELECT MAX(versiyon) FROM __migrasyon__").fetchone()
    return row[0] or 0


# --- validasyon yardımcıları ---

def _tarih_dogrula(tarih):
    """YYYY-MM-DD formatında geçerli bir tarih olmalı; None geçerlidir."""
    if tarih is None:
        return
    try:
        datetime.strptime(tarih, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Geçersiz tarih formatı: '{tarih}'. Beklenen: YYYY-MM-DD")


def _etiket_dogrula_ve_temizle(etiketler):
    """Boşlukları filtreler, uzunluk ve virgül kısıtlarını kontrol eder."""
    if not etiketler:
        return None
    temiz = [e.strip() for e in etiketler if e.strip()]
    for e in temiz:
        if len(e) > _ETIKET_MAX_UZUNLUK:
            raise ValueError(f"Etiket çok uzun (max {_ETIKET_MAX_UZUNLUK} karakter): '{e}'")
        if "," in e:
            raise ValueError(f"Etiket içinde virgül kullanılamaz: '{e}'")
    return ",".join(temiz) if temiz else None


def _like_kac(metin):
    """LIKE sorgusunda % ve _ karakterlerini literal olarak eşleştirmek için kaçırır."""
    return metin.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# --- public API ---

def gorevleri_yukle():
    """Aktif ve tamamlanmış görevleri döndür (arşivlenenler hariç)."""
    _init_db()
    with _baglan() as con:
        rows = con.execute(
            "SELECT * FROM gorevler WHERE durum != 'arsivlendi' ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


def arsivi_yukle():
    """Sadece arşivlenmiş görevleri döndür."""
    _init_db()
    with _baglan() as con:
        rows = con.execute(
            "SELECT * FROM gorevler WHERE durum = 'arsivlendi' ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


def bugunun_gorevleri():
    """son_tarih bugün olan aktif/tamamlanmış görevler."""
    _init_db()
    with _baglan() as con:
        rows = con.execute(
            "SELECT * FROM gorevler WHERE son_tarih = ? AND durum != 'arsivlendi' ORDER BY id",
            (_bugun(),)
        ).fetchall()
    return [dict(r) for r in rows]


def gecmis_gorevler():
    """son_tarihi geçmiş ve henüz tamamlanmamış görevler."""
    _init_db()
    with _baglan() as con:
        rows = con.execute(
            "SELECT * FROM gorevler WHERE son_tarih < ? AND durum = 'aktif' ORDER BY son_tarih",
            (_bugun(),)
        ).fetchall()
    return [dict(r) for r in rows]


def yaklasan_gorevler(gun=7):
    """Bugünden itibaren N gün içinde bitmesi gereken aktif görevler."""
    _init_db()
    from datetime import timedelta
    bitis = str(date.today() + timedelta(days=gun))
    with _baglan() as con:
        rows = con.execute(
            """SELECT * FROM gorevler
               WHERE son_tarih >= ? AND son_tarih <= ?
               AND durum = 'aktif'
               ORDER BY son_tarih""",
            (_bugun(), bitis)
        ).fetchall()
    return [dict(r) for r in rows]


def gorev_ekle(baslik, oncelik="normal", son_tarih=None, etiketler=None):
    """Yeni görev ekle ve kaydet."""
    if not baslik or not baslik.strip():
        raise ValueError("Görev başlığı boş olamaz.")
    if len(baslik) > 200:
        raise ValueError("Görev başlığı 200 karakterden uzun olamaz.")
    if oncelik not in GECERLI_ONCELIKLER:
        raise ValueError(f"Geçersiz öncelik: '{oncelik}'. Seçenekler: {GECERLI_ONCELIKLER}")
    _tarih_dogrula(son_tarih)
    etiket_str = _etiket_dogrula_ve_temizle(etiketler)
    _init_db()
    with _baglan() as con:
        cur = con.execute(
            "INSERT INTO gorevler (baslik, oncelik, durum, olusturulma, son_tarih, etiketler) VALUES (?, ?, 'aktif', ?, ?, ?)",
            (baslik, oncelik, _simdi(), son_tarih, etiket_str)
        )
        row = con.execute("SELECT * FROM gorevler WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def gorev_tamamla(gorev_id):
    """Görevi tamamlandı olarak işaretle."""
    _init_db()
    with _baglan() as con:
        etkilenen = con.execute(
            "UPDATE gorevler SET durum = 'tamamlandi', tamamlanma = ? WHERE id = ?",
            (_simdi(), gorev_id)
        ).rowcount
    return etkilenen > 0


def gorev_arsivle(gorev_id):
    """Görevi arşivle (soft delete)."""
    _init_db()
    with _baglan() as con:
        etkilenen = con.execute(
            "UPDATE gorevler SET durum = 'arsivlendi', arsivlenme = ? WHERE id = ?",
            (_simdi(), gorev_id)
        ).rowcount
    return etkilenen > 0


def gorev_aktife_al(gorev_id):
    """Tamamlanmış veya arşivlenmiş görevi tekrar aktife çeker."""
    _init_db()
    with _baglan() as con:
        etkilenen = con.execute(
            "UPDATE gorevler SET durum = 'aktif', tamamlanma = NULL, arsivlenme = NULL WHERE id = ?",
            (gorev_id,)
        ).rowcount
    return etkilenen > 0


def gorev_ara(q=None, oncelik=None, etiket=None):
    """Başlık, öncelik ve etiket kombinasyonuyla görev ara (arşivlenenler hariç)."""
    _init_db()
    kosullar = ["durum != 'arsivlendi'"]
    parametreler = []
    if q:
        kosullar.append("baslik LIKE ? ESCAPE '\\'")
        parametreler.append(f"%{_like_kac(q)}%")
    if oncelik:
        kosullar.append("oncelik = ?")
        parametreler.append(oncelik)
    if etiket:
        kosullar.append("(',' || etiketler || ',' LIKE ? ESCAPE '\\')")
        parametreler.append(f"%,{_like_kac(etiket)},%")
    sorgu = "SELECT * FROM gorevler WHERE " + " AND ".join(kosullar) + " ORDER BY id"
    with _baglan() as con:
        rows = con.execute(sorgu, parametreler).fetchall()
    return [dict(r) for r in rows]


def etiketlere_gore_filtrele(etiket):
    """Belirli etikete sahip aktif/tamamlanmış görevleri döndür."""
    _init_db()
    with _baglan() as con:
        rows = con.execute(
            """SELECT * FROM gorevler
               WHERE durum != 'arsivlendi'
               AND (',' || etiketler || ',' LIKE ? ESCAPE '\\')
               ORDER BY id""",
            (f"%,{_like_kac(etiket)},%",)
        ).fetchall()
    return [dict(r) for r in rows]


def gorev_duzenle(gorev_id, baslik=None, oncelik=None, son_tarih=None, etiketler=None):
    """Görevin alanlarını kısmen güncelle. Güncellenmiş görevi döndürür; ID bulunamazsa None."""
    if baslik is not None:
        if not baslik or not baslik.strip():
            raise ValueError("Görev başlığı boş olamaz.")
        if len(baslik) > 200:
            raise ValueError("Görev başlığı 200 karakterden uzun olamaz.")
    if oncelik is not None and oncelik not in GECERLI_ONCELIKLER:
        raise ValueError(f"Geçersiz öncelik: '{oncelik}'. Seçenekler: {GECERLI_ONCELIKLER}")
    if son_tarih is not None:
        _tarih_dogrula(son_tarih)
    _init_db()
    with _baglan() as con:
        row = con.execute("SELECT * FROM gorevler WHERE id = ?", (gorev_id,)).fetchone()
        if row is None:
            return None
        yeni_baslik    = baslik    if baslik    is not None else row["baslik"]
        yeni_oncelik   = oncelik   if oncelik   is not None else row["oncelik"]
        yeni_tarih     = son_tarih if son_tarih is not None else row["son_tarih"]
        yeni_etiketler = _etiket_dogrula_ve_temizle(etiketler) if etiketler is not None else row["etiketler"]
        con.execute(
            "UPDATE gorevler SET baslik = ?, oncelik = ?, son_tarih = ?, etiketler = ? WHERE id = ?",
            (yeni_baslik, yeni_oncelik, yeni_tarih, yeni_etiketler, gorev_id)
        )
        updated = con.execute("SELECT * FROM gorevler WHERE id = ?", (gorev_id,)).fetchone()
    return dict(updated)


def gorev_sil(gorev_id):
    """Arşivlenmiş görevi kalıcı olarak sil. Aktif/tamamlanan görevler silinemez."""
    _init_db()
    with _baglan() as con:
        row = con.execute("SELECT durum FROM gorevler WHERE id = ?", (gorev_id,)).fetchone()
        if row is None:
            return False
        if row["durum"] != "arsivlendi":
            raise ValueError("Sadece arşivlenmiş görevler kalıcı olarak silinebilir.")
        con.execute("DELETE FROM gorevler WHERE id = ?", (gorev_id,))
    return True
