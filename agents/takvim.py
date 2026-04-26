from collections import defaultdict
from agents.base import TemelAjan
import tasks

_CATISMA_ESIGI = 2
_ONCELIK_AGIRLIK = {"dusuk": 1, "normal": 2, "yuksek": 3}


class TakvimAjan(TemelAjan):
    @property
    def ajan_adi(self):
        return "TakvimAjan"

    def calistir(self, gun=30) -> dict:
        try:
            gorevler = tasks.yaklasan_gorevler(gun=gun)
            catismalar = self._catismalari_bul(gorevler)
            gunluk_yuk = self._gunluk_yuk_hesapla(gorevler)
            self.olay_kaydet(
                "calistirma",
                f"{len(catismalar)} çakışma, {len(gunluk_yuk)} gün analiz edildi."
            )
            return {
                "ajan": self.ajan_adi,
                "catismalar": catismalar,
                "gunluk_yuk": gunluk_yuk,
            }
        except Exception as e:
            self.olay_kaydet("hata", str(e))
            return {"ajan": self.ajan_adi, "hata": str(e)}

    def _catismalari_bul(self, gorevler):
        tarih_sayac = defaultdict(list)
        for g in gorevler:
            if g["son_tarih"]:
                tarih_sayac[g["son_tarih"]].append(g["baslik"])
        return {
            t: basliklar
            for t, basliklar in tarih_sayac.items()
            if len(basliklar) >= _CATISMA_ESIGI
        }

    def _gunluk_yuk_hesapla(self, gorevler):
        yuk = defaultdict(int)
        for g in gorevler:
            if g["son_tarih"] and g["durum"] == "aktif":
                agirlik = _ONCELIK_AGIRLIK.get(g["oncelik"], 2)
                yuk[g["son_tarih"]] += agirlik
        return dict(sorted(yuk.items()))
