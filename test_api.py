import os
import pytest
from fastapi.testclient import TestClient
from api import app
from tasks import DB

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
