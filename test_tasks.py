import os
import json
import pytest
from tasks import gorev_ekle, gorev_tamamla, gorev_sil, gorevleri_yukle, DOSYA


# Her testten önce tasks.json'u temizle
# Böylece testler birbirini etkilemez
def setup_function():
    if os.path.exists(DOSYA):
        os.remove(DOSYA)


# --- gorev_ekle testleri ---

def test_gorev_ekle_basarili():
    gorev = gorev_ekle("Test görevi")
    assert gorev["baslik"] == "Test görevi"
    assert gorev["tamamlandi"] == False
    assert gorev["oncelik"] == "normal"  # varsayılan öncelik


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

def test_gorev_sil_basarili():
    gorev = gorev_ekle("Silinecek iş")
    sonuc = gorev_sil(gorev["id"])
    assert sonuc == True
    assert gorevleri_yukle() == []


def test_gorev_sil_olmayan_id():
    sonuc = gorev_sil(999)
    assert sonuc == False
