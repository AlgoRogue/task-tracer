import os
import pytest
from datetime import date, timedelta
from tasks import (
    gorev_ekle, gorev_tamamla, gorev_arsivle, gorev_aktife_al,
    gorev_sil,
    gorevleri_yukle, arsivi_yukle,
    bugunun_gorevleri, gecmis_gorevler, yaklasan_gorevler,
    DB
)


# Her testten önce veritabanını temizle
def setup_function():
    if os.path.exists(DB):
        os.remove(DB)


# --- gorev_ekle testleri ---

def test_gorev_ekle_basarili():
    gorev = gorev_ekle("Test görevi")
    assert gorev["baslik"] == "Test görevi"
    assert gorev["durum"] == "aktif"
    assert gorev["oncelik"] == "normal"


def test_gorev_ekle_oncelik_ile():
    gorev = gorev_ekle("Acil iş", oncelik="yuksek")
    assert gorev["oncelik"] == "yuksek"


def test_gorev_ekle_yanlis_oncelik():
    with pytest.raises(ValueError):
        gorev_ekle("Bir görev", oncelik="cok_acil")  # geçersiz öncelik


def test_gorev_ekle_id_artar():
    gorev1 = gorev_ekle("Birinci")
    gorev2 = gorev_ekle("İkinci")
    assert gorev1["id"] == 1
    assert gorev2["id"] == 2


# --- gorev_tamamla testleri ---

def test_gorev_tamamla_basarili():
    gorev = gorev_ekle("Tamamlanacak iş")
    sonuc = gorev_tamamla(gorev["id"])
    assert sonuc == True
    gorevler = gorevleri_yukle()
    assert gorevler[0]["durum"] == "tamamlandi"


def test_gorev_tamamla_olmayan_id():
    sonuc = gorev_tamamla(999)
    assert sonuc == False


# --- gorev_sil testleri ---

def test_gorev_arsivle_basarili():
    gorev = gorev_ekle("Arşivlenecek iş")
    sonuc = gorev_arsivle(gorev["id"])
    assert sonuc == True


def test_gorev_arsivle_olmayan_id():
    sonuc = gorev_arsivle(999)
    assert sonuc == False


# --- zaman damgası ve soft delete testleri ---

def test_yeni_gorev_durum_aktif():
    gorev = gorev_ekle("Yeni görev")
    assert gorev["durum"] == "aktif"

def test_yeni_gorev_olusturulma_dolu():
    gorev = gorev_ekle("Yeni görev")
    assert gorev["olusturulma"] is not None

def test_yeni_gorev_tamamlanma_null():
    gorev = gorev_ekle("Yeni görev")
    assert gorev["tamamlanma"] is None

def test_yeni_gorev_arsivlenme_null():
    gorev = gorev_ekle("Yeni görev")
    assert gorev["arsivlenme"] is None

def test_tamamlanan_gorev_durum_degisir():
    gorev = gorev_ekle("Tamamlanacak görev")
    gorev_tamamla(gorev["id"])
    aktif = gorevleri_yukle()
    assert aktif[0]["durum"] == "tamamlandi"

def test_tamamlanan_gorev_tarih_dolu():
    gorev = gorev_ekle("Tamamlanacak görev")
    gorev_tamamla(gorev["id"])
    aktif = gorevleri_yukle()
    assert aktif[0]["tamamlanma"] is not None

def test_tamamlanan_gorev_aktif_listede_kaliyor():
    gorev = gorev_ekle("Tamamlanacak görev")
    gorev_tamamla(gorev["id"])
    aktif = gorevleri_yukle()
    assert len(aktif) == 1

def test_arsivlenen_gorev_aktif_listeden_cikar():
    gorev = gorev_ekle("Arşivlenecek görev")
    gorev_arsivle(gorev["id"])
    aktif = gorevleri_yukle()
    assert len(aktif) == 0

def test_arsivlenen_gorev_arsivde_gorunur():
    gorev = gorev_ekle("Arşivlenecek görev")
    gorev_arsivle(gorev["id"])
    arsiv = arsivi_yukle()
    assert len(arsiv) == 1
    assert arsiv[0]["durum"] == "arsivlendi"

def test_arsivlenen_gorev_tarih_dolu():
    gorev = gorev_ekle("Arşivlenecek görev")
    gorev_arsivle(gorev["id"])
    arsiv = arsivi_yukle()
    assert arsiv[0]["arsivlenme"] is not None

def test_bos_veritabani_calisiyor():
    # Hiç görev yokken sistem çökmemeli
    assert gorevleri_yukle() == []
    assert arsivi_yukle() == []

# --- kenar durum testleri ---

def test_arsivleme_sonrasi_id_cakismaz():
    # 3 görev ekle, ortadakini arşivle, yeni ekle → ID çakışmamalı
    import sqlite3
    gorev_ekle("Birinci")
    gorev_ekle("Ikinci")
    gorev_ekle("Ucuncu")
    gorev_arsivle(2)
    yeni = gorev_ekle("Dorduncu")
    with sqlite3.connect(DB) as con:
        tum_idler = [r[0] for r in con.execute("SELECT id FROM gorevler").fetchall()]
    assert len(tum_idler) == len(set(tum_idler))


def test_bos_baslik_kabul_edilmez():
    with pytest.raises(ValueError):
        gorev_ekle("")


def test_cok_uzun_baslik_kabul_edilmez():
    with pytest.raises(ValueError):
        gorev_ekle("a" * 300)


# --- entegrasyon testleri ---

def test_ekle_tamamla_arsivle_akisi():
    # Kullanıcının en yaygın yolculuğu: ekle → tamamla → arşivle
    gorev = gorev_ekle("Markete git", "yuksek")
    gorev_tamamla(gorev["id"])
    gorev_arsivle(gorev["id"])

    assert gorevleri_yukle() == []          # aktif listede yok
    arsiv = arsivi_yukle()
    assert len(arsiv) == 1
    assert arsiv[0]["tamamlanma"] is not None   # tamamlandı
    assert arsiv[0]["arsivlenme"] is not None   # arşivlendi


def test_vazgecme_akisi():
    # Kullanıcı tamamlamadan vazgeçer: ekle → arşivle
    gorev = gorev_ekle("Spor yap")
    gorev_arsivle(gorev["id"])

    assert gorevleri_yukle() == []
    arsiv = arsivi_yukle()
    assert arsiv[0]["tamamlanma"] is None       # hiç tamamlanmadı
    assert arsiv[0]["arsivlenme"] is not None   # ama arşivlendi


def test_coklu_gorev_karismazlik():
    # Birden fazla görev varken işlemler birbirine karışmamalı
    g1 = gorev_ekle("Birinci")
    g2 = gorev_ekle("Ikinci")
    g3 = gorev_ekle("Ucuncu")

    gorev_tamamla(g1["id"])
    gorev_arsivle(g2["id"])

    aktif = gorevleri_yukle()
    arsiv = arsivi_yukle()

    assert len(aktif) == 2                          # g1(tamamlı) + g3(aktif)
    assert len(arsiv) == 1                          # sadece g2
    assert arsiv[0]["baslik"] == "Ikinci"


# --- görevi aktife al testleri ---

def test_tamamlanan_gorevi_aktife_al():
    gorev = gorev_ekle("Yoga yap")
    gorev_tamamla(gorev["id"])
    sonuc = gorev_aktife_al(gorev["id"])
    assert sonuc == True
    aktif = gorevleri_yukle()
    assert aktif[0]["durum"] == "aktif"
    assert aktif[0]["tamamlanma"] is None


def test_arsivlenen_gorevi_aktife_al():
    gorev = gorev_ekle("Kitap oku")
    gorev_arsivle(gorev["id"])
    sonuc = gorev_aktife_al(gorev["id"])
    assert sonuc == True
    aktif = gorevleri_yukle()
    assert aktif[0]["durum"] == "aktif"
    assert aktif[0]["arsivlenme"] is None


def test_aktife_al_olmayan_id():
    sonuc = gorev_aktife_al(999)
    assert sonuc == False


def test_aktife_alinca_aktif_listede_gorunur():
    gorev = gorev_ekle("Koşu yap")
    gorev_arsivle(gorev["id"])
    assert len(gorevleri_yukle()) == 0
    gorev_aktife_al(gorev["id"])
    assert len(gorevleri_yukle()) == 1


# --- son_tarih ve zaman sorguları testleri ---

DUN   = str(date.today() - timedelta(days=1))
BUGUN = str(date.today())
YARIN = str(date.today() + timedelta(days=1))


def test_gorev_son_tarih_ile_eklenir():
    gorev = gorev_ekle("Yoga yap", son_tarih=YARIN)
    assert gorev["son_tarih"] == YARIN


def test_gorev_son_tarih_olmadan_null():
    gorev = gorev_ekle("Yoga yap")
    assert gorev["son_tarih"] is None


def test_bugunun_gorevleri():
    gorev_ekle("Bugünkü iş", son_tarih=BUGUN)
    gorev_ekle("Yarınki iş", son_tarih=YARIN)
    gorev_ekle("Dünkü iş",   son_tarih=DUN)
    assert len(bugunun_gorevleri()) == 1
    assert bugunun_gorevleri()[0]["baslik"] == "Bugünkü iş"


def test_gecmis_gorevler():
    gorev_ekle("Gecikmiş iş", son_tarih=DUN)
    gorev_ekle("Bugünkü iş",  son_tarih=BUGUN)
    assert len(gecmis_gorevler()) == 1
    assert gecmis_gorevler()[0]["baslik"] == "Gecikmiş iş"


def test_tamamlanan_gecmis_gorev_gelmez():
    gorev = gorev_ekle("Gecikmiş ama bitti", son_tarih=DUN)
    gorev_tamamla(gorev["id"])
    assert len(gecmis_gorevler()) == 0


def test_yaklasan_gorevler():
    gorev_ekle("Bugünkü",      son_tarih=BUGUN)
    gorev_ekle("3 gün sonra",  son_tarih=str(date.today() + timedelta(days=3)))
    gorev_ekle("10 gün sonra", son_tarih=str(date.today() + timedelta(days=10)))
    assert len(yaklasan_gorevler(gun=7)) == 2


# --- gorev_sil testleri ---

def test_arsivlenmis_gorev_silinebilir():
    gorev = gorev_ekle("Silinecek görev")
    gorev_arsivle(gorev["id"])
    sonuc = gorev_sil(gorev["id"])
    assert sonuc == True
    assert arsivi_yukle() == []


def test_aktif_gorev_silinemez():
    gorev = gorev_ekle("Aktif görev")
    with pytest.raises(ValueError):
        gorev_sil(gorev["id"])


def test_tamamlanan_gorev_silinemez():
    gorev = gorev_ekle("Tamamlanan görev")
    gorev_tamamla(gorev["id"])
    with pytest.raises(ValueError):
        gorev_sil(gorev["id"])


def test_olmayan_gorev_silinemez():
    sonuc = gorev_sil(999)
    assert sonuc == False


def test_silinen_gorev_listede_kalmaz():
    gorev = gorev_ekle("Silinecek")
    gorev_arsivle(gorev["id"])
    gorev_sil(gorev["id"])
    assert arsivi_yukle() == []
    assert gorevleri_yukle() == []


# --- kenar durum testleri ---

def test_db_olmadan_cokturmez(tmp_path, monkeypatch):
    # Veritabanı dosyası yoksa otomatik oluşturulmalı, çökmemeli
    import tasks
    monkeypatch.setattr(tasks, "DB", str(tmp_path / "test.db"))
    assert tasks.gorevleri_yukle() == []
