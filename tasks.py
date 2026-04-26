import sqlite3
import os
from datetime import datetime, date

_KLASOR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(_KLASOR, "tasks.db")

GECERLI_ONCELIKLER = ["dusuk", "normal", "yuksek"]


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
        """)
        for sutun in ("son_tarih TEXT", "etiketler TEXT"):
            try:
                con.execute(f"ALTER TABLE gorevler ADD COLUMN {sutun}")
            except Exception:
                pass


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
    etiket_str = ",".join(etiketler) if etiketler else None
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
        kosullar.append("baslik LIKE ?")
        parametreler.append(f"%{q}%")
    if oncelik:
        kosullar.append("oncelik = ?")
        parametreler.append(oncelik)
    if etiket:
        kosullar.append("(',' || etiketler || ',' LIKE ?)")
        parametreler.append(f"%,{etiket},%")
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
               AND (',' || etiketler || ',' LIKE ? )
               ORDER BY id""",
            (f"%,{etiket},%",)
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
    _init_db()
    with _baglan() as con:
        row = con.execute("SELECT * FROM gorevler WHERE id = ?", (gorev_id,)).fetchone()
        if row is None:
            return None
        yeni_baslik   = baslik    if baslik    is not None else row["baslik"]
        yeni_oncelik  = oncelik   if oncelik   is not None else row["oncelik"]
        yeni_tarih    = son_tarih if son_tarih is not None else row["son_tarih"]
        yeni_etiketler = ",".join(etiketler) if etiketler is not None else row["etiketler"]
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
