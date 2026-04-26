import os
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from api import app
from tasks import DB, gorev_ekle, gorev_arsivle

BUGUN = str(date.today())
YARIN = str(date.today() + timedelta(days=1))
DUN   = str(date.today() - timedelta(days=1))

client = TestClient(app)


def setup_function():
    if os.path.exists(DB):
        os.remove(DB)


# --- GET /gorevler ---

def test_bos_liste():
    r = client.get("/gorevler")
    assert r.status_code == 200
    assert r.json() == []


def test_gorev_eklendikten_sonra_listede_gorunur():
    client.post("/gorevler", json={"baslik": "Test görevi"})
    r = client.get("/gorevler")
    assert len(r.json()) == 1
    assert r.json()[0]["baslik"] == "Test görevi"


# --- POST /gorevler ---

def test_gorev_ekleme_basarili():
    r = client.post("/gorevler", json={"baslik": "Yeni görev", "oncelik": "yuksek"})
    assert r.status_code == 201
    assert r.json()["baslik"] == "Yeni görev"
    assert r.json()["oncelik"] == "yuksek"
    assert r.json()["durum"] == "aktif"


def test_bos_baslik_422_doner():
    r = client.post("/gorevler", json={"baslik": ""})
    assert r.status_code == 422


def test_gecersiz_oncelik_422_doner():
    r = client.post("/gorevler", json={"baslik": "Görev", "oncelik": "cok_acil"})
    assert r.status_code == 422


# --- PUT /gorevler/{id}/tamamla ---

def test_gorevi_tamamla():
    gorev = client.post("/gorevler", json={"baslik": "Tamamlanacak"}).json()
    r = client.put(f"/gorevler/{gorev['id']}/tamamla")
    assert r.status_code == 200
    gorevler = client.get("/gorevler").json()
    assert gorevler[0]["durum"] == "tamamlandi"


def test_olmayan_gorevi_tamamla_404():
    r = client.put("/gorevler/999/tamamla")
    assert r.status_code == 404


# --- PUT /gorevler/{id}/arsivle ---

def test_gorevi_arsivle():
    gorev = client.post("/gorevler", json={"baslik": "Arşivlenecek"}).json()
    r = client.put(f"/gorevler/{gorev['id']}/arsivle")
    assert r.status_code == 200
    assert client.get("/gorevler").json() == []
    assert len(client.get("/arsiv").json()) == 1


def test_olmayan_gorevi_arsivle_404():
    r = client.put("/gorevler/999/arsivle")
    assert r.status_code == 404


# --- PUT /gorevler/{id}/aktife-al ---

def test_gorevi_aktife_al():
    gorev = client.post("/gorevler", json={"baslik": "Aktife alınacak"}).json()
    client.put(f"/gorevler/{gorev['id']}/arsivle")
    r = client.put(f"/gorevler/{gorev['id']}/aktife-al")
    assert r.status_code == 200
    assert len(client.get("/gorevler").json()) == 1


def test_olmayan_gorevi_aktife_al_404():
    r = client.put("/gorevler/999/aktife-al")
    assert r.status_code == 404


# --- GET /arsiv ---

def test_arsiv_bos():
    r = client.get("/arsiv")
    assert r.status_code == 200
    assert r.json() == []


def test_arsivlenen_gorev_arsivde_gorunur():
    gorev = client.post("/gorevler", json={"baslik": "Arşiv testi"}).json()
    client.put(f"/gorevler/{gorev['id']}/arsivle")
    r = client.get("/arsiv")
    assert len(r.json()) == 1
    assert r.json()[0]["durum"] == "arsivlendi"


def test_son_tarih_ile_gorev_olustur():
    r = client.post("/gorevler", json={"baslik": "Randevu", "son_tarih": YARIN})
    assert r.status_code == 201
    assert r.json()["son_tarih"] == YARIN


def test_bugun_endpoint():
    client.post("/gorevler", json={"baslik": "Bugünkü", "son_tarih": BUGUN})
    client.post("/gorevler", json={"baslik": "Yarınki", "son_tarih": YARIN})
    r = client.get("/gorevler/bugun")
    assert len(r.json()) == 1
    assert r.json()[0]["baslik"] == "Bugünkü"


def test_gecmis_endpoint():
    client.post("/gorevler", json={"baslik": "Gecikmiş", "son_tarih": DUN})
    r = client.get("/gorevler/gecmis")
    assert len(r.json()) == 1


def test_yaklasan_endpoint():
    client.post("/gorevler", json={"baslik": "Bu hafta", "son_tarih": YARIN})
    client.post("/gorevler", json={"baslik": "Uzak", "son_tarih": str(date.today() + timedelta(days=30))})
    r = client.get("/gorevler/yaklasan?gun=7")
    assert len(r.json()) == 1


# --- DELETE /gorevler/{id} ---

def test_delete_arsivlenmis_gorev_200():
    gorev = client.post("/gorevler", json={"baslik": "Silinecek"}).json()
    client.put(f"/gorevler/{gorev['id']}/arsivle")
    r = client.delete(f"/gorevler/{gorev['id']}")
    assert r.status_code == 200
    assert client.get("/arsiv").json() == []


def test_delete_aktif_gorev_400():
    gorev = client.post("/gorevler", json={"baslik": "Aktif görev"}).json()
    r = client.delete(f"/gorevler/{gorev['id']}")
    assert r.status_code == 400


def test_delete_olmayan_gorev_404():
    r = client.delete("/gorevler/999")
    assert r.status_code == 404


# --- PATCH /gorevler/{id} ---

def test_baslik_guncelle():
    gorev = client.post("/gorevler", json={"baslik": "Eski"}).json()
    r = client.patch(f"/gorevler/{gorev['id']}", json={"baslik": "Yeni"})
    assert r.status_code == 200
    assert r.json()["baslik"] == "Yeni"


def test_oncelik_guncelle():
    gorev = client.post("/gorevler", json={"baslik": "Görev", "oncelik": "normal"}).json()
    r = client.patch(f"/gorevler/{gorev['id']}", json={"oncelik": "yuksek"})
    assert r.status_code == 200
    assert r.json()["oncelik"] == "yuksek"


def test_guncelleme_diger_alanlar_korunur():
    gorev = client.post("/gorevler", json={"baslik": "Test", "oncelik": "dusuk"}).json()
    r = client.patch(f"/gorevler/{gorev['id']}", json={"baslik": "Yeni ad"})
    assert r.json()["oncelik"] == "dusuk"


def test_guncelle_gecersiz_oncelik_422():
    gorev = client.post("/gorevler", json={"baslik": "Görev"}).json()
    r = client.patch(f"/gorevler/{gorev['id']}", json={"oncelik": "uydurma"})
    assert r.status_code == 422


def test_guncelle_olmayan_gorev_404():
    r = client.patch("/gorevler/999", json={"baslik": "Bir şey"})
    assert r.status_code == 404


# --- etiket endpoint ---

def test_gorev_etiketle_olustur():
    r = client.post("/gorevler", json={"baslik": "Etiketli", "etiketler": ["iş", "acil"]})
    assert r.status_code == 201
    assert "iş" in r.json()["etiketler"]


def test_etiket_filtre_endpoint():
    client.post("/gorevler", json={"baslik": "İş görevi", "etiketler": ["iş"]})
    client.post("/gorevler", json={"baslik": "Kişisel", "etiketler": ["kişisel"]})
    r = client.get("/gorevler?etiket=iş")
    assert len(r.json()) == 1
    assert r.json()[0]["baslik"] == "İş görevi"
