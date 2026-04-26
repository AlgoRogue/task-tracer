import pytest
from datetime import date, timedelta
import tasks
from agents import run_all_agents, run_agent, _AJAN_KAYDEDICISI
from agents.giris import GirisAjan
from agents.skor import SkorAjan
from agents.hatirlatma import HatirlatmaAjan
from agents.takvim import TakvimAjan
from agents.oncelik import OncelikAjan, _deadline_carpani


@pytest.fixture(autouse=True)
def test_db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(tasks, "DB", db_path)
    tasks._init_db()
    yield db_path


# ---------------------------------------------------------------------------
# tasks.py — yeni helper fonksiyonlar
# ---------------------------------------------------------------------------

class TestBildirimler:
    def test_bildirim_ekle_ve_yukle(self):
        g = tasks.gorev_ekle("Test görevi")
        tasks.bildirim_ekle(g["id"], "bugun", "Bugün: Test görevi")
        bildirimler = tasks.bildirimleri_yukle()
        assert len(bildirimler) == 1
        assert bildirimler[0]["tur"] == "bugun"
        assert bildirimler[0]["goruldu_mu"] == 0

    def test_bildirim_var_mi_ayni_gun(self):
        g = tasks.gorev_ekle("Test görevi")
        assert not tasks._bildirim_var_mi(g["id"], "bugun")
        tasks.bildirim_ekle(g["id"], "bugun", "Bugün: Test görevi")
        assert tasks._bildirim_var_mi(g["id"], "bugun")

    def test_bildirim_var_mi_farkli_tur(self):
        g = tasks.gorev_ekle("Test görevi")
        tasks.bildirim_ekle(g["id"], "bugun", "Bugün")
        assert not tasks._bildirim_var_mi(g["id"], "yarin")

    def test_bildirimleri_yukle_tur_filtresi(self):
        g = tasks.gorev_ekle("Görev")
        tasks.bildirim_ekle(g["id"], "bugun", "Bugün")
        tasks.bildirim_ekle(g["id"], "gecmis", "Geçmiş")
        assert len(tasks.bildirimleri_yukle(tur="bugun")) == 1
        assert len(tasks.bildirimleri_yukle(tur="gecmis")) == 1
        assert len(tasks.bildirimleri_yukle()) == 2

    def test_bildirimi_goruldu_isaretle(self):
        g = tasks.gorev_ekle("Görev")
        bid = tasks.bildirim_ekle(g["id"], "bugun", "Mesaj")
        assert tasks.bildirimi_goruldu_isaretle(bid)
        goruldu = tasks.bildirimleri_yukle(goruldu_mu=1)
        assert len(goruldu) == 1

    def test_bildirimi_goruldu_isaretle_olmayan_id(self):
        assert not tasks.bildirimi_goruldu_isaretle(9999)


class TestSkorGecmisi:
    def test_gunluk_skor_kaydet_ve_getir(self):
        bugun = str(date.today())
        tasks.gunluk_skor_kaydet(bugun, 3, 5, 3, 0, 0.375, 1.0, 2)
        skor = tasks.gunluk_skor_getir(bugun)
        assert skor is not None
        assert skor["tamamlanan_sayi"] == 3
        assert skor["seri"] == 2

    def test_gunluk_skor_getir_bugun_varsayilan(self):
        bugun = str(date.today())
        tasks.gunluk_skor_kaydet(bugun, 1, 2, 1, 0, 0.33, 1.0, 0)
        assert tasks.gunluk_skor_getir() is not None

    def test_gunluk_skor_getir_olmayan_tarih(self):
        assert tasks.gunluk_skor_getir("2000-01-01") is None

    def test_skor_gecmisi_limit(self):
        for i in range(5):
            tarih = str(date.today() - timedelta(days=i))
            tasks.gunluk_skor_kaydet(tarih, i, 0, i, 0, 0.0, 0.0, 0)
        assert len(tasks.skor_gecmisini_getir(limit=3)) == 3
        assert len(tasks.skor_gecmisini_getir(limit=10)) == 5

    def test_gunluk_skor_kaydet_upsert(self):
        bugun = str(date.today())
        tasks.gunluk_skor_kaydet(bugun, 1, 0, 1, 0, 1.0, 1.0, 0)
        tasks.gunluk_skor_kaydet(bugun, 5, 0, 5, 0, 1.0, 1.0, 3)
        skor = tasks.gunluk_skor_getir(bugun)
        assert skor["tamamlanan_sayi"] == 5


class TestAjanOlaylari:
    def test_olay_kaydet_ve_getir(self):
        tasks.ajan_olayi_kaydet("TestAjan", "calistirma", "Çalıştı")
        olaylar = tasks.ajan_olaylarini_getir()
        assert len(olaylar) == 1
        assert olaylar[0]["ajan_adi"] == "TestAjan"

    def test_olay_ajan_filtresi(self):
        tasks.ajan_olayi_kaydet("AjanA", "bilgi", "A çalıştı")
        tasks.ajan_olayi_kaydet("AjanB", "bilgi", "B çalıştı")
        assert len(tasks.ajan_olaylarini_getir(ajan_adi="AjanA")) == 1
        assert len(tasks.ajan_olaylarini_getir(ajan_adi="AjanB")) == 1
        assert len(tasks.ajan_olaylarini_getir()) == 2

    def test_olay_limit(self):
        for i in range(10):
            tasks.ajan_olayi_kaydet("Ajan", "bilgi", f"Mesaj {i}")
        assert len(tasks.ajan_olaylarini_getir(limit=5)) == 5

    def test_olay_meta_json(self):
        tasks.ajan_olayi_kaydet("Ajan", "bilgi", "Meta test", meta={"key": "value"})
        olay = tasks.ajan_olaylarini_getir()[0]
        assert olay["meta"] == '{"key": "value"}'


# ---------------------------------------------------------------------------
# GirisAjan
# ---------------------------------------------------------------------------

class TestGirisAjanNormalize:
    def setup_method(self):
        self.ajan = GirisAjan()

    def test_baslik_strip(self):
        g = {"baslik": "  görev  ", "oncelik": "normal", "etiketler": None}
        assert self.ajan.normalize(g)["baslik"] == "Görev"

    def test_baslik_coklu_bosluk(self):
        g = {"baslik": "görev   adı", "oncelik": "normal", "etiketler": None}
        assert self.ajan.normalize(g)["baslik"] == "Görev adı"

    def test_baslik_ilk_harf_buyuk(self):
        g = {"baslik": "toplantı", "oncelik": "normal", "etiketler": None}
        assert self.ajan.normalize(g)["baslik"] == "Toplantı"

    def test_baslik_kontrol_karakteri(self):
        g = {"baslik": "görev\x00\x1ftest", "oncelik": "normal", "etiketler": None}
        assert self.ajan.normalize(g)["baslik"] == "Görevtest"

    def test_oncelik_kucuk_harf(self):
        g = {"baslik": "Görev", "oncelik": "YUKSEK", "etiketler": None}
        assert self.ajan.normalize(g)["oncelik"] == "yuksek"

    def test_etiket_deduplicate(self):
        g = {"baslik": "Görev", "oncelik": "normal", "etiketler": "iş,ev,iş"}
        assert self.ajan.normalize(g)["etiketler"] == "iş,ev"

    def test_etiket_bosluk_temizle(self):
        g = {"baslik": "Görev", "oncelik": "normal", "etiketler": " iş , ev "}
        assert self.ajan.normalize(g)["etiketler"] == "iş,ev"

    def test_etiket_none_kalir(self):
        g = {"baslik": "Görev", "oncelik": "normal", "etiketler": None}
        assert self.ajan.normalize(g)["etiketler"] is None

    def test_degismemis_gorev_aynen_kalir(self):
        g = {"baslik": "Görev", "oncelik": "normal", "etiketler": "iş"}
        norm = self.ajan.normalize(g)
        assert norm["baslik"] == "Görev"
        assert norm["oncelik"] == "normal"
        assert norm["etiketler"] == "iş"


class TestGirisAjanCalistir:
    def test_normalize_db_gunceller(self):
        tasks.gorev_ekle("  toplantı  ")
        sonuc = GirisAjan().calistir()
        assert sonuc["guncellenen"] == 1
        gorev = tasks.gorevleri_yukle()[0]
        assert gorev["baslik"] == "Toplantı"

    def test_normalize_degismemis_atlar(self):
        tasks.gorev_ekle("Toplantı")
        sonuc = GirisAjan().calistir()
        assert sonuc["guncellenen"] == 0

    def test_olay_kaydedilir(self):
        tasks.gorev_ekle("Test")
        GirisAjan().calistir()
        olaylar = tasks.ajan_olaylarini_getir(ajan_adi="GirisAjan")
        assert len(olaylar) == 1

    def test_bos_db_hatasiz(self):
        sonuc = GirisAjan().calistir()
        assert sonuc["guncellenen"] == 0
        assert sonuc["hatalar"] == []


# ---------------------------------------------------------------------------
# SkorAjan
# ---------------------------------------------------------------------------

class TestSkorAjan:
    def test_skor_kayit_bos_db(self):
        sonuc = SkorAjan().calistir()
        assert sonuc["tamamlanan_sayi"] == 0
        skor = tasks.gunluk_skor_getir()
        assert skor is not None
        assert skor["tamamlanan_sayi"] == 0

    def test_tamamlanan_sayi_dogru(self):
        g1 = tasks.gorev_ekle("Görev 1")
        g2 = tasks.gorev_ekle("Görev 2")
        tasks.gorev_tamamla(g1["id"])
        tasks.gorev_tamamla(g2["id"])
        sonuc = SkorAjan().calistir()
        assert sonuc["tamamlanan_sayi"] == 2

    def test_aktif_gorevler_dahil_degil(self):
        tasks.gorev_ekle("Aktif görev")
        g = tasks.gorev_ekle("Tamamlanan")
        tasks.gorev_tamamla(g["id"])
        SkorAjan().calistir()
        skor = tasks.gunluk_skor_getir()
        assert skor["tamamlanan_sayi"] == 1
        assert skor["toplam_aktif_sayi"] == 1

    def test_zamaninda_sayi_son_tarihsiz(self):
        g = tasks.gorev_ekle("Görev", son_tarih=None)
        tasks.gorev_tamamla(g["id"])
        SkorAjan().calistir()
        skor = tasks.gunluk_skor_getir()
        assert skor["zamaninda_sayi"] == 1

    def test_seri_baslangic_sifir(self):
        sonuc = SkorAjan().calistir()
        assert sonuc["seri"] == 0

    def test_seri_ardisik_gun(self):
        dun = str(date.today() - timedelta(days=1))
        tasks.gunluk_skor_kaydet(dun, 1, 0, 1, 0, 1.0, 1.0, 0)
        sonuc = SkorAjan().calistir()
        assert sonuc["seri"] == 1


# ---------------------------------------------------------------------------
# HatirlatmaAjan
# ---------------------------------------------------------------------------

class TestHatirlatmaAjan:
    def test_gecmis_gorev_bildirimi(self):
        dun = str(date.today() - timedelta(days=1))
        tasks.gorev_ekle("Gecikmiş görev", son_tarih=dun)
        sonuc = HatirlatmaAjan().calistir()
        assert sonuc["olusturulan_bildirim"] == 1
        bildirimler = tasks.bildirimleri_yukle(tur="gecmis")
        assert len(bildirimler) == 1

    def test_bugun_gorevi_bildirimi(self):
        bugun = str(date.today())
        tasks.gorev_ekle("Bugünkü görev", son_tarih=bugun)
        sonuc = HatirlatmaAjan().calistir()
        assert sonuc["olusturulan_bildirim"] == 1

    def test_yarin_gorevi_bildirimi(self):
        yarin = str(date.today() + timedelta(days=1))
        tasks.gorev_ekle("Yarınki görev", son_tarih=yarin)
        sonuc = HatirlatmaAjan().calistir()
        assert sonuc["olusturulan_bildirim"] == 1

    def test_dedup_ayni_gun(self):
        dun = str(date.today() - timedelta(days=1))
        tasks.gorev_ekle("Gecikmiş görev", son_tarih=dun)
        HatirlatmaAjan().calistir()
        sonuc = HatirlatmaAjan().calistir()
        assert sonuc["olusturulan_bildirim"] == 0
        assert len(tasks.bildirimleri_yukle()) == 1

    def test_bos_db_hatasiz(self):
        sonuc = HatirlatmaAjan().calistir()
        assert sonuc["olusturulan_bildirim"] == 0


# ---------------------------------------------------------------------------
# TakvimAjan
# ---------------------------------------------------------------------------

class TestTakvimAjan:
    def test_catisma_iki_gorev_ayni_tarih(self):
        yarin = str(date.today() + timedelta(days=1))
        tasks.gorev_ekle("Görev 1", son_tarih=yarin)
        tasks.gorev_ekle("Görev 2", son_tarih=yarin)
        sonuc = TakvimAjan().calistir()
        assert yarin in sonuc["catismalar"]
        assert len(sonuc["catismalar"][yarin]) == 2

    def test_catisma_tek_gorev_yok(self):
        yarin = str(date.today() + timedelta(days=1))
        tasks.gorev_ekle("Tek görev", son_tarih=yarin)
        sonuc = TakvimAjan().calistir()
        assert len(sonuc["catismalar"]) == 0

    def test_gunluk_yuk_hesapla(self):
        yarin = str(date.today() + timedelta(days=1))
        tasks.gorev_ekle("Yüksek", oncelik="yuksek", son_tarih=yarin)
        tasks.gorev_ekle("Normal", oncelik="normal", son_tarih=yarin)
        sonuc = TakvimAjan().calistir()
        assert sonuc["gunluk_yuk"][yarin] == 5  # 3 + 2

    def test_gunluk_yuk_dusuk_oncelik(self):
        yarin = str(date.today() + timedelta(days=1))
        tasks.gorev_ekle("Düşük", oncelik="dusuk", son_tarih=yarin)
        sonuc = TakvimAjan().calistir()
        assert sonuc["gunluk_yuk"][yarin] == 1

    def test_bos_db_hatasiz(self):
        sonuc = TakvimAjan().calistir()
        assert sonuc["catismalar"] == {}
        assert sonuc["gunluk_yuk"] == {}


# ---------------------------------------------------------------------------
# OncelikAjan
# ---------------------------------------------------------------------------

class TestDeadlineCarpani:
    def test_gecikmiş(self):
        assert _deadline_carpani(-1) == 10.0
        assert _deadline_carpani(-5) == 10.0

    def test_bugun(self):
        assert _deadline_carpani(0) == 8.0

    def test_yarin(self):
        assert _deadline_carpani(1) == 6.0

    def test_iki_uc_gun(self):
        assert _deadline_carpani(2) == 4.0
        assert _deadline_carpani(3) == 4.0

    def test_dort_yedi_gun(self):
        assert _deadline_carpani(4) == 2.0
        assert _deadline_carpani(7) == 2.0

    def test_sekiz_ondort_gun(self):
        assert _deadline_carpani(8) == 1.5
        assert _deadline_carpani(14) == 1.5

    def test_uzak_tarih(self):
        assert _deadline_carpani(15) == 1.0
        assert _deadline_carpani(100) == 1.0

    def test_tarihsiz(self):
        assert _deadline_carpani(None) == 1.0


class TestOncelikAjan:
    def test_sirali_cikti(self):
        dun = str(date.today() - timedelta(days=1))
        ay_sonra = str(date.today() + timedelta(days=30))
        tasks.gorev_ekle("Uzak görev", oncelik="normal", son_tarih=ay_sonra)
        tasks.gorev_ekle("Gecikmiş yüksek", oncelik="yuksek", son_tarih=dun)
        sonuc = OncelikAjan().calistir()
        gorevler = sonuc["oncelikli_gorevler"]
        assert gorevler[0]["baslik"] == "Gecikmiş yüksek"
        assert gorevler[0]["aciliyet_skoru"] == 30.0  # 3 * 10

    def test_tamamlananlar_dahil_degil(self):
        g = tasks.gorev_ekle("Tamamlanan")
        tasks.gorev_tamamla(g["id"])
        sonuc = OncelikAjan().calistir()
        assert len(sonuc["oncelikli_gorevler"]) == 0

    def test_son_tarihi_olmayan(self):
        tasks.gorev_ekle("Tarihsiz görev", oncelik="yuksek")
        sonuc = OncelikAjan().calistir()
        gorev = sonuc["oncelikli_gorevler"][0]
        assert gorev["aciliyet_skoru"] == 3.0  # 3 * 1.0

    def test_bos_db_hatasiz(self):
        sonuc = OncelikAjan().calistir()
        assert sonuc["oncelikli_gorevler"] == []


# ---------------------------------------------------------------------------
# Orkestratör
# ---------------------------------------------------------------------------

class TestOrchestrator:
    def test_run_all_agents_hatasiz(self):
        sonuclar = run_all_agents()
        assert set(sonuclar.keys()) == set(_AJAN_KAYDEDICISI.keys())

    def test_run_agent_giris(self):
        sonuc = run_agent("GirisAjan")
        assert sonuc["ajan"] == "GirisAjan"

    def test_run_agent_skor(self):
        sonuc = run_agent("SkorAjan")
        assert "tamamlanan_sayi" in sonuc or "hata" in sonuc

    def test_run_agent_hatirlatma(self):
        sonuc = run_agent("HatirlatmaAjan")
        assert "olusturulan_bildirim" in sonuc

    def test_run_agent_takvim(self):
        sonuc = run_agent("TakvimAjan")
        assert "catismalar" in sonuc

    def test_run_agent_oncelik(self):
        sonuc = run_agent("OncelikAjan")
        assert "oncelikli_gorevler" in sonuc

    def test_run_agent_bilinmeyen_hata(self):
        with pytest.raises(ValueError, match="Bilinmeyen ajan"):
            run_agent("YokAjan")

    def test_run_all_olay_kaydeder(self):
        run_all_agents()
        olaylar = tasks.ajan_olaylarini_getir()
        ajan_adlari = {o["ajan_adi"] for o in olaylar}
        assert "GirisAjan" in ajan_adlari
        assert "SkorAjan" in ajan_adlari
