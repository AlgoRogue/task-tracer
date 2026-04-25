import sqlite3
import os
from datetime import datetime

_KLASOR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(_KLASOR, "tasks.db")

GECERLI_ONCELIKLER = ["dusuk", "normal", "yuksek"]


def _simdi():
    return datetime.now().isoformat(timespec="seconds")


def _baglan():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row  # sütun adıyla erişim sağlar
    return con


def _init_db():
    with _baglan() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS gorevler (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                baslik    TEXT    NOT NULL,
                oncelik   TEXT    NOT NULL DEFAULT 'normal',
                durum     TEXT    NOT NULL DEFAULT 'aktif',
                olusturulma TEXT,
                tamamlanma  TEXT,
                arsivlenme  TEXT
            )
        """)


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


def gorev_ekle(baslik, oncelik="normal"):
    """Yeni görev ekle ve kaydet."""
    if not baslik or not baslik.strip():
        raise ValueError("Görev başlığı boş olamaz.")
    if len(baslik) > 200:
        raise ValueError("Görev başlığı 200 karakterden uzun olamaz.")
    if oncelik not in GECERLI_ONCELIKLER:
        raise ValueError(f"Geçersiz öncelik: '{oncelik}'. Seçenekler: {GECERLI_ONCELIKLER}")
    _init_db()
    with _baglan() as con:
        cur = con.execute(
            "INSERT INTO gorevler (baslik, oncelik, durum, olusturulma) VALUES (?, ?, 'aktif', ?)",
            (baslik, oncelik, _simdi())
        )
        gorev_id = cur.lastrowid
        row = con.execute("SELECT * FROM gorevler WHERE id = ?", (gorev_id,)).fetchone()
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
