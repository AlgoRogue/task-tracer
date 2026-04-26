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
    (2, """
        CREATE TABLE IF NOT EXISTS bildirimler (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            gorev_id    INTEGER,
            tur         TEXT NOT NULL,
            mesaj       TEXT NOT NULL,
            olusturulma TEXT NOT NULL,
            goruldu_mu  INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (gorev_id) REFERENCES gorevler(id) ON DELETE SET NULL
        )
    """),
    (3, """
        CREATE TABLE IF NOT EXISTS skor_gecmisi (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih             TEXT NOT NULL UNIQUE,
            tamamlanan_sayi   INTEGER NOT NULL DEFAULT 0,
            toplam_aktif_sayi INTEGER NOT NULL DEFAULT 0,
            zamaninda_sayi    INTEGER NOT NULL DEFAULT 0,
            gec_tamamlanan    INTEGER NOT NULL DEFAULT 0,
            tamamlanma_orani  REAL    NOT NULL DEFAULT 0.0,
            zamaninda_orani   REAL    NOT NULL DEFAULT 0.0,
            seri              INTEGER NOT NULL DEFAULT 0,
            hesaplanma        TEXT NOT NULL
        )
    """),
    (4, """
        CREATE TABLE IF NOT EXISTS ajan_olaylari (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ajan_adi    TEXT NOT NULL,
            olay_turu   TEXT NOT NULL,
            mesaj       TEXT NOT NULL,
            meta        TEXT,
            olusturulma TEXT NOT NULL
        )
    """),
    (5, """
        CREATE TABLE IF NOT EXISTS desen_hafizasi (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ham_girdi    TEXT NOT NULL,
            niyet        TEXT NOT NULL,
            onay_sayisi  INTEGER NOT NULL DEFAULT 0,
            red_sayisi   INTEGER NOT NULL DEFAULT 0,
            guven        REAL NOT NULL DEFAULT 0.5,
            son_kullanim TEXT NOT NULL
        )
    """),
    (6, """
        CREATE TABLE IF NOT EXISTS session_context (
            anahtar      TEXT PRIMARY KEY,
            deger        TEXT NOT NULL,
            son_guncell  TEXT NOT NULL,
            oturum_mu    INTEGER NOT NULL DEFAULT 0
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

        # Eski şema uyumluluğu: gorevler tablosu etiketler sütunu olmadan
        # oluşturulmuşsa (v1 IF NOT EXISTS nedeniyle atlandıysa) ekle.
        mevcut = {r[1] for r in con.execute("PRAGMA table_info(gorevler)").fetchall()}
        if "etiketler" not in mevcut:
            con.execute("ALTER TABLE gorevler ADD COLUMN etiketler TEXT")


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


# --- bildirimler ---

def bildirim_ekle(gorev_id, tur, mesaj):
    _init_db()
    with _baglan() as con:
        cur = con.execute(
            "INSERT INTO bildirimler (gorev_id, tur, mesaj, olusturulma) VALUES (?, ?, ?, ?)",
            (gorev_id, tur, mesaj, _simdi())
        )
    return cur.lastrowid


def _bildirim_var_mi(gorev_id, tur):
    _init_db()
    with _baglan() as con:
        row = con.execute(
            "SELECT id FROM bildirimler WHERE gorev_id = ? AND tur = ? AND olusturulma LIKE ?",
            (gorev_id, tur, f"{_bugun()}%")
        ).fetchone()
    return row is not None


def bildirimleri_yukle(tur=None, goruldu_mu=None):
    _init_db()
    kosullar, parametreler = [], []
    if tur is not None:
        kosullar.append("tur = ?")
        parametreler.append(tur)
    if goruldu_mu is not None:
        kosullar.append("goruldu_mu = ?")
        parametreler.append(goruldu_mu)
    sorgu = "SELECT * FROM bildirimler"
    if kosullar:
        sorgu += " WHERE " + " AND ".join(kosullar)
    sorgu += " ORDER BY olusturulma DESC"
    with _baglan() as con:
        rows = con.execute(sorgu, parametreler).fetchall()
    return [dict(r) for r in rows]


def bildirimi_goruldu_isaretle(bildirim_id):
    _init_db()
    with _baglan() as con:
        etkilenen = con.execute(
            "UPDATE bildirimler SET goruldu_mu = 1 WHERE id = ?",
            (bildirim_id,)
        ).rowcount
    return etkilenen > 0


# --- skor_gecmisi ---

def gunluk_skor_kaydet(tarih, tamamlanan_sayi, toplam_aktif_sayi,
                        zamaninda_sayi, gec_tamamlanan,
                        tamamlanma_orani, zamaninda_orani, seri):
    _init_db()
    with _baglan() as con:
        con.execute(
            """INSERT OR REPLACE INTO skor_gecmisi
               (tarih, tamamlanan_sayi, toplam_aktif_sayi, zamaninda_sayi,
                gec_tamamlanan, tamamlanma_orani, zamaninda_orani, seri, hesaplanma)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tarih, tamamlanan_sayi, toplam_aktif_sayi, zamaninda_sayi,
             gec_tamamlanan, tamamlanma_orani, zamaninda_orani, seri, _simdi())
        )


def gunluk_skor_getir(tarih=None):
    _init_db()
    hedef = tarih or _bugun()
    with _baglan() as con:
        row = con.execute(
            "SELECT * FROM skor_gecmisi WHERE tarih = ?", (hedef,)
        ).fetchone()
    return dict(row) if row else None


def skor_gecmisini_getir(limit=30):
    _init_db()
    with _baglan() as con:
        rows = con.execute(
            "SELECT * FROM skor_gecmisi ORDER BY tarih DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# --- ajan_olaylari ---

def ajan_olayi_kaydet(ajan_adi, olay_turu, mesaj, meta=None):
    import json
    _init_db()
    meta_str = json.dumps(meta, ensure_ascii=False) if meta is not None else None
    with _baglan() as con:
        con.execute(
            "INSERT INTO ajan_olaylari (ajan_adi, olay_turu, mesaj, meta, olusturulma) VALUES (?, ?, ?, ?, ?)",
            (ajan_adi, olay_turu, mesaj, meta_str, _simdi())
        )


def ajan_olaylarini_getir(ajan_adi=None, limit=50):
    _init_db()
    if ajan_adi:
        with _baglan() as con:
            rows = con.execute(
                "SELECT * FROM ajan_olaylari WHERE ajan_adi = ? ORDER BY olusturulma DESC LIMIT ?",
                (ajan_adi, limit)
            ).fetchall()
    else:
        with _baglan() as con:
            rows = con.execute(
                "SELECT * FROM ajan_olaylari ORDER BY olusturulma DESC LIMIT ?",
                (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


# --- desen_hafizasi ---

def desen_ekle(ham_girdi, niyet_dict, guven=0.5):
    import json
    _init_db()
    with _baglan() as con:
        cur = con.execute(
            "INSERT INTO desen_hafizasi (ham_girdi, niyet, onay_sayisi, red_sayisi, guven, son_kullanim) VALUES (?, ?, 0, 0, ?, ?)",
            (ham_girdi.strip().lower(), json.dumps(niyet_dict, ensure_ascii=False), guven, _simdi())
        )
    return cur.lastrowid


def desen_listele(limit=200):
    _init_db()
    with _baglan() as con:
        rows = con.execute(
            "SELECT * FROM desen_hafizasi ORDER BY guven DESC, onay_sayisi DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def desen_onayla(desen_id):
    _init_db()
    with _baglan() as con:
        row = con.execute("SELECT onay_sayisi, red_sayisi FROM desen_hafizasi WHERE id = ?", (desen_id,)).fetchone()
        if row is None:
            return False
        onay = row["onay_sayisi"] + 1
        red = row["red_sayisi"]
        yeni_guven = round(onay / (onay + red + 1e-9), 4)
        con.execute(
            "UPDATE desen_hafizasi SET onay_sayisi = ?, guven = ?, son_kullanim = ? WHERE id = ?",
            (onay, yeni_guven, _simdi(), desen_id)
        )
    return True


def desen_reddet(desen_id):
    _init_db()
    with _baglan() as con:
        row = con.execute("SELECT onay_sayisi, red_sayisi FROM desen_hafizasi WHERE id = ?", (desen_id,)).fetchone()
        if row is None:
            return False
        onay = row["onay_sayisi"]
        red = row["red_sayisi"] + 1
        yeni_guven = round(onay / (onay + red + 1e-9), 4)
        con.execute(
            "UPDATE desen_hafizasi SET red_sayisi = ?, guven = ?, son_kullanim = ? WHERE id = ?",
            (red, yeni_guven, _simdi(), desen_id)
        )
    return True


def desen_bul(desen_id: int):
    _init_db()
    with _baglan() as con:
        row = con.execute("SELECT * FROM desen_hafizasi WHERE id = ?", (desen_id,)).fetchone()
    return dict(row) if row else None


# --- session_context ---

def session_degerini_kaydet(anahtar, deger, oturum_mu=False):
    import json
    _init_db()
    with _baglan() as con:
        con.execute(
            "INSERT OR REPLACE INTO session_context (anahtar, deger, son_guncell, oturum_mu) VALUES (?, ?, ?, ?)",
            (anahtar, json.dumps(deger, ensure_ascii=False), _simdi(), 1 if oturum_mu else 0)
        )


def session_degeri_al(anahtar, ttl_saat=None):
    import json
    from datetime import datetime, timedelta
    _init_db()
    with _baglan() as con:
        row = con.execute(
            "SELECT deger, son_guncell FROM session_context WHERE anahtar = ?",
            (anahtar,)
        ).fetchone()
    if row is None:
        return None
    if ttl_saat is not None:
        son_guncell = datetime.fromisoformat(row["son_guncell"])
        if datetime.now() - son_guncell > timedelta(hours=ttl_saat):
            session_anahtarini_sil(anahtar)
            return None
    return json.loads(row["deger"])


def session_anahtarini_sil(anahtar):
    _init_db()
    with _baglan() as con:
        con.execute("DELETE FROM session_context WHERE anahtar = ?", (anahtar,))


def session_oturumu_temizle():
    _init_db()
    with _baglan() as con:
        con.execute("DELETE FROM session_context WHERE oturum_mu = 1")
