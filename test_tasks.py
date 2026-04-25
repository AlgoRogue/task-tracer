import os
import json
import pytest
from tasks import gorev_ekle, gorev_tamamla, gorev_arsivle, gorevleri_yukle, arsivi_yukle, DOSYA


# Her testten önce tasks.json'u temizle
# Böylece testler birbirini etkilemez
def setup_function():
    if os.path.exists(DOSYA):
        os.remove(DOSYA)


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
    assert gorevler[0]["tamamlandi"] == True


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

def test_eski_format_bozulmuyor():
    # durum alanı olmayan eski görevler sistemi çökertmemeli
    eski_gorev = {"id": 1, "baslik": "Eski görev", "tamamlandi": False, "oncelik": "normal"}
    with open(DOSYA, "w", encoding="utf-8") as f:
        json.dump([eski_gorev], f)
    gorevler = gorevleri_yukle()
    assert len(gorevler) == 1

# --- kenar durum testleri ---

def test_arsivleme_sonrasi_id_cakismaz():
    # 3 görev ekle, ortadakini arşivle, yeni ekle → ID çakışmamalı
    gorev_ekle("Birinci")
    gorev_ekle("Ikinci")
    gorev_ekle("Ucuncu")
    gorev_arsivle(2)
    gorev_ekle("Dorduncu")
    from tasks import _tum_gorevleri_yukle
    tum_idler = [g["id"] for g in _tum_gorevleri_yukle()]
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


# --- kenar durum testleri ---

def test_bozuk_json_cokturmez(tmp_path, monkeypatch):
    # tasks.json bozuk içerik içeriyorsa program çökmemeli
    import tasks
    bozuk_dosya = tmp_path / "tasks.json"
    bozuk_dosya.write_text("bu gecerli json degil {{{")
    monkeypatch.setattr(tasks, "DOSYA", str(bozuk_dosya))
    gorevler = tasks.gorevleri_yukle()
    assert gorevler == []  # çökmek yerine boş liste döndürmeli
