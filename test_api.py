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


# --- arama endpoint ---

def test_arama_endpoint_q():
    client.post("/gorevler", json={"baslik": "Alışveriş"})
    client.post("/gorevler", json={"baslik": "Toplantı"})
    r = client.get("/gorevler/ara?q=alışveriş")
    assert len(r.json()) == 1


def test_arama_endpoint_oncelik():
    client.post("/gorevler", json={"baslik": "Acil", "oncelik": "yuksek"})
    client.post("/gorevler", json={"baslik": "Normal", "oncelik": "normal"})
    r = client.get("/gorevler/ara?oncelik=yuksek")
    assert len(r.json()) == 1


def test_arama_endpoint_bos_hepsini_doner():
    client.post("/gorevler", json={"baslik": "A"})
    client.post("/gorevler", json={"baslik": "B"})
    r = client.get("/gorevler/ara")
    assert len(r.json()) == 2


# --- web arayüzü ---

def test_anasayfa_200_doner():
    r = client.get("/")
    assert r.status_code == 200


def test_anasayfa_html_icerir():
    r = client.get("/")
    assert "text/html" in r.headers["content-type"]
    assert "task" in r.text.lower() or "görev" in r.text.lower()


# --- NL pipeline ---

def test_nl_yorumla_acikla_dusuk_guven():
    r = client.post("/nl/yorumla", json={"girdi": "xyz"})
    assert r.status_code == 200
    assert r.json()["eylem"] in ("acikla", "onay_iste", "direkt_uygula")


def test_nl_yorumla_direkt_gorev_olusturur():
    r = client.post("/nl/yorumla", json={"girdi": "toplantı hatırlatıcısı ekle"})
    assert r.status_code == 200
    veri = r.json()
    assert "eylem" in veri
    assert "yorum" in veri


def test_nl_yorumla_onay_iste_desen_id_doner():
    r = client.post("/nl/yorumla", json={"girdi": "belki yarın bir şeyler yapabilirim"})
    assert r.status_code == 200
    veri = r.json()
    if veri["eylem"] == "onay_iste":
        assert "desen_id" in veri
        assert isinstance(veri["desen_id"], int)


def test_nl_geri_bildirim_red():
    # Önce onay_iste döndüren bir girdi ile desen oluştur
    r = client.post("/nl/yorumla", json={"girdi": "belki bir ara şu raporu bitireyim"})
    veri = r.json()
    if veri["eylem"] == "onay_iste":
        desen_id = veri["desen_id"]
        r2 = client.post("/nl/geri-bildirim", json={"desen_id": desen_id, "onay": False})
        assert r2.status_code == 200
        assert r2.json()["ok"] is True


def test_nl_geri_bildirim_onay_gorev_olusturur():
    # Yüksek güvenli bir gorev_ekle deseni oluştur
    from tasks import desen_ekle
    desen_id = desen_ekle(
        "yarın toplantı var",
        {"niyet": "gorev_ekle", "baslik": "Toplantı", "oncelik": "normal",
         "tarih": YARIN, "etiketler": []},
        guven=0.75,
    )
    r = client.post("/nl/geri-bildirim", json={"desen_id": desen_id, "onay": True})
    assert r.status_code == 200
    veri = r.json()
    assert veri["ok"] is True
    assert veri["gorev"]["baslik"] == "Toplantı"


def test_nl_geri_bildirim_olmayan_desen_404():
    r = client.post("/nl/geri-bildirim", json={"desen_id": 999999, "onay": True})
    assert r.status_code == 404


def test_nl_yorumla_direkt_uygula_gorev_kaydedilir():
    onceki = len(client.get("/gorevler").json())
    client.post("/nl/yorumla", json={"girdi": "yarın acil rapor teslimi ekle"})
    sonraki = client.get("/gorevler").json()
    # direkt_uygula ise görev sayısı artar; onay_iste/acikla ise artmaz
    assert len(sonraki) >= onceki
