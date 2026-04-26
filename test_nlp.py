"""Phase 2a NLU bileşen testleri."""
import pytest
import json
from datetime import date, timedelta
import tasks
from nlp.kural_motoru import yorumla, _sonraki_gun, _tarih_cikart, _oncelik_cikart, _niyet_cikart
from nlp import desen_hafizasi as dh
from nlp.session_context import SessionContext
from nlp.baglam_cozucu import coz
from nlp.guven_kapisi import karar_ver, _did_you_mean
from agents.giris import GirisAjan

# Testlerde sabit referans tarihi kullan: Pazar, 2026-04-26
_REF = date(2026, 4, 26)  # Pazar — weekday() == 6


@pytest.fixture(autouse=True)
def test_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(tasks, "DB", db_path)
    tasks._init_db()
    yield db_path


# ---------------------------------------------------------------------------
# KuralMotoru — tarih çıkarma
# ---------------------------------------------------------------------------

class TestTarihCikart:
    def test_bugun(self):
        sonuc = _tarih_cikart("bugün toplantı", _REF)
        assert sonuc[0] == str(_REF)

    def test_yarin(self):
        sonuc = _tarih_cikart("yarın toplantı", _REF)
        assert sonuc[0] == str(_REF + timedelta(days=1))

    def test_obur_gun(self):
        sonuc = _tarih_cikart("öbür gün sunum", _REF)
        assert sonuc[0] == str(_REF + timedelta(days=2))

    def test_n_gun_sonra_sayi(self):
        sonuc = _tarih_cikart("3 gün sonra rapor", _REF)
        assert sonuc[0] == str(_REF + timedelta(days=3))

    def test_n_gun_sonra_kelime(self):
        sonuc = _tarih_cikart("iki gün sonra rapor", _REF)
        assert sonuc[0] == str(_REF + timedelta(days=2))

    def test_n_hafta_sonra(self):
        sonuc = _tarih_cikart("2 hafta sonra teslim", _REF)
        assert sonuc[0] == str(_REF + timedelta(weeks=2))

    def test_pazartesi(self):
        # REF = Pazar (6), Pazartesi = 0 → +1 gün
        sonuc = _tarih_cikart("pazartesi toplantı", _REF)
        assert sonuc[0] == str(_REF + timedelta(days=1))

    def test_cuma(self):
        # REF = Pazar (6), Cuma = 4 → (4-6)%7 = 5 gün
        sonuc = _tarih_cikart("cuma teslim", _REF)
        assert sonuc[0] == str(_REF + timedelta(days=5))

    def test_hafta_sonu(self):
        # REF = Pazar (6), Cumartesi = 5 → (5-6)%7 = 6 gün
        sonuc = _tarih_cikart("hafta sonu piknik", _REF)
        assert sonuc[0] == str(_REF + timedelta(days=6))

    def test_gelecek_hafta(self):
        # REF = Pazar (6), gelecek Pazartesi = 7-6 = 1 gün
        sonuc = _tarih_cikart("gelecek hafta sunum", _REF)
        assert sonuc[0] == str(_REF + timedelta(days=1))

    def test_iso_format(self):
        sonuc = _tarih_cikart("2027-01-15 teslim", _REF)
        assert sonuc[0] == "2027-01-15"

    def test_tarihsiz_none(self):
        assert _tarih_cikart("toplantı", _REF) is None


# ---------------------------------------------------------------------------
# KuralMotoru — öncelik çıkarma
# ---------------------------------------------------------------------------

class TestOncelikCikart:
    def test_acil(self):
        assert _oncelik_cikart("acil görev")[0] == "yuksek"

    def test_onemli(self):
        assert _oncelik_cikart("önemli toplantı")[0] == "yuksek"

    def test_yuksek_oncelikli(self):
        assert _oncelik_cikart("yüksek öncelikli rapor")[0] == "yuksek"

    def test_dusuk(self):
        assert _oncelik_cikart("düşük öncelikli görev")[0] == "dusuk"

    def test_firsatta(self):
        assert _oncelik_cikart("fırsatta yap")[0] == "dusuk"

    def test_normal_varsayilan(self):
        oncelik, eslesme = _oncelik_cikart("toplantı yap")
        assert oncelik == "normal"
        assert eslesme is None

    def test_normal_acik(self):
        assert _oncelik_cikart("normal görev")[0] == "normal"


# ---------------------------------------------------------------------------
# KuralMotoru — niyet çıkarma
# ---------------------------------------------------------------------------

class TestNiyetCikart:
    def test_tamamla(self):
        assert _niyet_cikart("tamamla")[0] == "gorev_tamamla"

    def test_bitti(self):
        assert _niyet_cikart("bitti")[0] == "gorev_tamamla"

    def test_arsivle(self):
        assert _niyet_cikart("arşivle")[0] == "gorev_arsivle"

    def test_listele(self):
        assert _niyet_cikart("listele")[0] == "gorev_listele"

    def test_goster(self):
        assert _niyet_cikart("göster")[0] == "gorev_listele"

    def test_ara(self):
        assert _niyet_cikart("ara")[0] == "gorev_ara"

    def test_ekle(self):
        assert _niyet_cikart("ekle")[0] == "gorev_ekle"

    def test_varsayilan_gorev_ekle(self):
        niyet, eslesme = _niyet_cikart("toplantı patronla")
        assert niyet == "gorev_ekle"
        assert eslesme is None


# ---------------------------------------------------------------------------
# KuralMotoru — yorumla() tam pipeline
# ---------------------------------------------------------------------------

class TestYorumla:
    def test_basit_gorev(self):
        y = yorumla("yarın toplantı acil", _bugun=_REF)
        assert y["niyet"] == "gorev_ekle"
        assert y["tarih"] == str(_REF + timedelta(days=1))
        assert y["oncelik"] == "yuksek"
        assert y["baslik"] == "toplantı"
        assert y["guven"] > 0.6

    def test_etiket_cikartilir(self):
        y = yorumla("yarın #iş toplantısı", _bugun=_REF)
        assert "iş" in y["etiketler"]

    def test_tamamla_komutu(self):
        y = yorumla("tamamla", _bugun=_REF)
        assert y["niyet"] == "gorev_tamamla"
        assert y["guven"] == 0.70

    def test_listele_yuksek_guven(self):
        y = yorumla("listele", _bugun=_REF)
        assert y["niyet"] == "gorev_listele"
        assert y["guven"] == 0.90

    def test_oncelik_varsayilan_normal(self):
        y = yorumla("bugün rapor yaz", _bugun=_REF)
        assert y["oncelik"] == "normal"

    def test_ham_girdi_korunur(self):
        girdi = "yarın toplantı"
        y = yorumla(girdi, _bugun=_REF)
        assert y["ham_girdi"] == girdi

    def test_bos_girdi(self):
        y = yorumla("", _bugun=_REF)
        assert y["niyet"] == "gorev_ekle"
        assert y["baslik"] is None

    def test_coklu_etiket(self):
        y = yorumla("#iş #önemli rapor yaz", _bugun=_REF)
        assert set(y["etiketler"]) == {"iş", "önemli"}

    def test_tarihsiz_gorev(self):
        y = yorumla("rapor yaz acil", _bugun=_REF)
        assert y["tarih"] is None
        assert y["oncelik"] == "yuksek"

    def test_guven_tam_bilgi(self):
        y = yorumla("yarın rapor ekle acil", _bugun=_REF)
        assert y["guven"] >= 0.80


# ---------------------------------------------------------------------------
# tasks.py — desen_hafizasi CRUD
# ---------------------------------------------------------------------------

class TestDesenHafizasiCrud:
    def test_desen_ekle_ve_listele(self):
        tasks.desen_ekle("yarın toplantı", {"niyet": "gorev_ekle"})
        desenleri = tasks.desen_listele()
        assert len(desenleri) == 1
        assert desenleri[0]["ham_girdi"] == "yarın toplantı"

    def test_desen_onayla_guven_artar(self):
        did = tasks.desen_ekle("test", {"niyet": "gorev_ekle"})
        tasks.desen_onayla(did)
        tasks.desen_onayla(did)
        d = tasks.desen_listele()[0]
        assert d["onay_sayisi"] == 2
        assert d["guven"] > 0.5

    def test_desen_reddet_guven_duşer(self):
        did = tasks.desen_ekle("test", {"niyet": "gorev_ekle"}, guven=0.8)
        tasks.desen_reddet(did)
        d = tasks.desen_listele()[0]
        assert d["red_sayisi"] == 1
        assert d["guven"] < 0.8

    def test_desen_onayla_olmayan_id(self):
        assert not tasks.desen_onayla(9999)

    def test_desen_reddet_olmayan_id(self):
        assert not tasks.desen_reddet(9999)


# ---------------------------------------------------------------------------
# DesenhafizasiModül — benzerlik ve birleştirme
# ---------------------------------------------------------------------------

class TestDesenHafizasiModul:
    def test_bos_hafiza_none_doner(self):
        assert dh.en_iyi_eslesmesi_bul("yarın toplantı") is None

    def test_tam_eslesme(self):
        tasks.desen_ekle("yarın toplantı", {"niyet": "gorev_ekle", "baslik": "toplantı"}, guven=0.9)
        eslesme = dh.en_iyi_eslesmesi_bul("yarın toplantı")
        assert eslesme is not None
        assert eslesme["benzerlik"] >= 0.99

    def test_benzer_eslesme(self):
        tasks.desen_ekle("yarın toplantı var", {"niyet": "gorev_ekle"}, guven=0.8)
        eslesme = dh.en_iyi_eslesmesi_bul("yarın toplantı")
        assert eslesme is not None

    def test_cok_farkli_none_doner(self):
        tasks.desen_ekle("yarın toplantı", {"niyet": "gorev_ekle"})
        eslesme = dh.en_iyi_eslesmesi_bul("xyz123")
        assert eslesme is None

    def test_yuksek_benzerlik_desen_kazanir(self):
        niyet = {"niyet": "gorev_ekle", "baslik": "toplantı", "tarih": "2026-04-27"}
        tasks.desen_ekle("yarın toplantı", niyet, guven=0.95)
        kural = yorumla("yarın toplantı", _bugun=_REF)
        zengin = dh.kural_ile_birlestir("yarın toplantı", kural)
        assert zengin.get("_desen_id") is not None

    def test_dusuk_benzerlik_kural_kazanir(self):
        tasks.desen_ekle("hafta sonu piknik", {"niyet": "gorev_ekle"}, guven=0.9)
        kural = yorumla("yarın toplantı", _bugun=_REF)
        orijinal_guven = kural["guven"]
        zengin = dh.kural_ile_birlestir("yarın toplantı", kural)
        # Benzerlik düşük olduğundan _desen_id olmamalı
        assert zengin.get("_desen_id") is None


# ---------------------------------------------------------------------------
# SessionContext
# ---------------------------------------------------------------------------

class TestSessionContext:
    def test_son_gorev_id_kaydet_al(self):
        ctx = SessionContext()
        ctx.son_gorev_id_kaydet(42)
        assert ctx.son_gorev_id_al() == 42

    def test_son_gorev_id_yoksa_none(self):
        ctx = SessionContext()
        assert ctx.son_gorev_id_al() is None

    def test_secili_gorev_bellek_ici(self):
        ctx = SessionContext()
        ctx.secili_gorev_id_kaydet(7)
        assert ctx.secili_gorev_id_al() == 7

    def test_aktif_filtre(self):
        ctx = SessionContext()
        ctx.aktif_filtre_kaydet({"oncelik": "yuksek"})
        assert ctx.aktif_filtre_al() == {"oncelik": "yuksek"}

    def test_son_eylem(self):
        ctx = SessionContext()
        ctx.son_eylem_kaydet("gorev_ekle")
        assert ctx.son_eylem_al() == "gorev_ekle"

    def test_oturumu_kapat_bellek_temizler(self):
        ctx = SessionContext()
        ctx.secili_gorev_id_kaydet(5)
        ctx.son_eylem_kaydet("test")
        ctx.oturumu_kapat()
        assert ctx.secili_gorev_id_al() is None
        assert ctx.son_eylem_al() is None

    def test_son_gorev_kalici_kapat_sonrasi(self):
        ctx = SessionContext()
        ctx.son_gorev_id_kaydet(99)
        ctx.oturumu_kapat()
        # Kalıcı alan kapanmadan sonra da erişilebilir
        ctx2 = SessionContext()
        assert ctx2.son_gorev_id_al() == 99


# ---------------------------------------------------------------------------
# BaglamCozucu
# ---------------------------------------------------------------------------

class TestBaglamCozucu:
    def test_hedef_id_bos_bağlamdan_doldurulur(self):
        ctx = SessionContext()
        ctx.son_gorev_id_kaydet(10)
        yorum = {"niyet": "gorev_tamamla", "hedef_id": None, "guven": 0.70}
        cozulmus = coz(yorum, ctx)
        assert cozulmus["hedef_id"] == 10
        assert cozulmus["guven"] > 0.70

    def test_hedef_id_dolu_degismez(self):
        ctx = SessionContext()
        ctx.son_gorev_id_kaydet(10)
        yorum = {"niyet": "gorev_tamamla", "hedef_id": 5, "guven": 0.80}
        cozulmus = coz(yorum, ctx)
        assert cozulmus["hedef_id"] == 5

    def test_gorev_ekle_hedef_gerekmez(self):
        ctx = SessionContext()
        yorum = {"niyet": "gorev_ekle", "hedef_id": None, "guven": 0.75}
        cozulmus = coz(yorum, ctx)
        assert cozulmus["hedef_id"] is None

    def test_bağlam_yok_hedef_yok(self):
        ctx = SessionContext()
        yorum = {"niyet": "gorev_tamamla", "hedef_id": None, "guven": 0.70}
        cozulmus = coz(yorum, ctx)
        assert cozulmus["hedef_id"] is None

    def test_secili_gorev_oncelikli(self):
        ctx = SessionContext()
        ctx.son_gorev_id_kaydet(1)
        ctx.secili_gorev_id_kaydet(2)
        yorum = {"niyet": "gorev_tamamla", "hedef_id": None, "guven": 0.70}
        cozulmus = coz(yorum, ctx)
        assert cozulmus["hedef_id"] == 2  # seçili olanı tercih eder

    def test_guven_maks_090(self):
        ctx = SessionContext()
        ctx.son_gorev_id_kaydet(1)
        yorum = {"niyet": "gorev_tamamla", "hedef_id": None, "guven": 0.85}
        cozulmus = coz(yorum, ctx)
        assert cozulmus["guven"] <= 0.90


# ---------------------------------------------------------------------------
# GuvenKapisi
# ---------------------------------------------------------------------------

class TestGuvenKapisi:
    def test_yuksek_guven_direkt(self):
        yorum = {"niyet": "gorev_ekle", "guven": 0.92, "baslik": "toplantı",
                 "tarih": None, "oncelik": "normal", "etiketler": []}
        karar = karar_ver(yorum)
        assert karar["eylem"] == "direkt_uygula"

    def test_orta_guven_onay_iste(self):
        yorum = {"niyet": "gorev_ekle", "guven": 0.75, "baslik": "toplantı",
                 "tarih": None, "oncelik": "normal", "etiketler": []}
        karar = karar_ver(yorum)
        assert karar["eylem"] == "onay_iste"
        assert "?" in karar["mesaj"] or "mi" in karar["mesaj"]

    def test_dusuk_guven_acikla(self):
        yorum = {"niyet": "gorev_ekle", "guven": 0.40, "baslik": None,
                 "tarih": None, "oncelik": "normal", "etiketler": []}
        karar = karar_ver(yorum)
        assert karar["eylem"] == "acikla"

    def test_esik_siniri_09_direkt(self):
        yorum = {"niyet": "gorev_ekle", "guven": 0.9, "baslik": "test",
                 "tarih": None, "oncelik": "normal", "etiketler": []}
        assert karar_ver(yorum)["eylem"] == "direkt_uygula"

    def test_esik_siniri_06_onay(self):
        yorum = {"niyet": "gorev_ekle", "guven": 0.6, "baslik": "test",
                 "tarih": None, "oncelik": "normal", "etiketler": []}
        assert karar_ver(yorum)["eylem"] == "onay_iste"

    def test_did_you_mean_baslik_icerir(self):
        yorum = {"niyet": "gorev_ekle", "guven": 0.7, "baslik": "toplantı",
                 "tarih": "2026-04-27", "oncelik": "yuksek", "etiketler": ["iş"]}
        mesaj = _did_you_mean(yorum)
        assert "toplantı" in mesaj
        assert "2026-04-27" in mesaj
        assert "yuksek" in mesaj

    def test_yorum_her_zaman_dahil(self):
        yorum = {"niyet": "gorev_ekle", "guven": 0.3, "baslik": None,
                 "tarih": None, "oncelik": "normal", "etiketler": []}
        karar = karar_ver(yorum)
        assert "yorum" in karar


# ---------------------------------------------------------------------------
# GirisAjan — yorumla_nl entegrasyonu
# ---------------------------------------------------------------------------

class TestGirisAjanNL:
    def test_yorumla_nl_temel(self):
        ajan = GirisAjan()
        karar = ajan.yorumla_nl("listele")
        assert karar["eylem"] in ("direkt_uygula", "onay_iste", "acikla")
        assert "yorum" in karar

    def test_yorumla_nl_yuksek_guven(self):
        ajan = GirisAjan()
        # "listele" → guven=0.90, direkt_uygula
        karar = ajan.yorumla_nl("listele")
        assert karar["eylem"] == "direkt_uygula"

    def test_yorumla_nl_context_gecilir(self):
        ctx = SessionContext()
        ctx.son_gorev_id_kaydet(5)
        ajan = GirisAjan()
        karar = ajan.yorumla_nl("tamamla", context=ctx)
        assert karar["yorum"]["niyet"] == "gorev_tamamla"
        assert karar["yorum"].get("hedef_id") == 5
