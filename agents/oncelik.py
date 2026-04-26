from datetime import date
from agents.base import TemelAjan
import tasks

_ONCELIK_AGIRLIK = {"dusuk": 1, "normal": 2, "yuksek": 3}


def _deadline_carpani(gun_farki):
    if gun_farki is None:
        return 1.0
    if gun_farki < 0:
        return 10.0
    if gun_farki == 0:
        return 8.0
    if gun_farki == 1:
        return 6.0
    if gun_farki <= 3:
        return 4.0
    if gun_farki <= 7:
        return 2.0
    if gun_farki <= 14:
        return 1.5
    return 1.0


class OncelikAjan(TemelAjan):
    @property
    def ajan_adi(self):
        return "OncelikAjan"

    def calistir(self) -> dict:
        try:
            gorevler = tasks.gorevleri_yukle()
            aktifler = [g for g in gorevler if g["durum"] == "aktif"]
            bugun = date.today()
            skorlar = []
            for g in aktifler:
                agirlik = _ONCELIK_AGIRLIK.get(g["oncelik"], 2)
                if g["son_tarih"]:
                    gun_farki = (date.fromisoformat(g["son_tarih"]) - bugun).days
                else:
                    gun_farki = None
                skor = agirlik * _deadline_carpani(gun_farki)
                skorlar.append({**g, "aciliyet_skoru": round(skor, 2)})
            skorlar.sort(key=lambda x: x["aciliyet_skoru"], reverse=True)
            self.olay_kaydet("calistirma", f"{len(skorlar)} görev önceliklendirildi.")
            return {"ajan": self.ajan_adi, "oncelikli_gorevler": skorlar}
        except Exception as e:
            self.olay_kaydet("hata", str(e))
            return {"ajan": self.ajan_adi, "hata": str(e)}
