import re
from agents.base import TemelAjan
import tasks


class GirisAjan(TemelAjan):
    @property
    def ajan_adi(self):
        return "GirisAjan"

    def normalize(self, gorev: dict) -> dict:
        baslik = gorev.get("baslik") or ""
        baslik = baslik.strip()
        baslik = re.sub(r" +", " ", baslik)
        baslik = re.sub(r"[\x00-\x1f\x7f]", "", baslik)
        if baslik:
            baslik = baslik[0].upper() + baslik[1:]

        oncelik = (gorev.get("oncelik") or "normal").strip().lower()

        etiketler = gorev.get("etiketler")
        if etiketler:
            parcalar = [e.strip() for e in etiketler.split(",") if e.strip()]
            goruldu = set()
            temiz = []
            for e in parcalar:
                if e not in goruldu:
                    goruldu.add(e)
                    temiz.append(e)
            etiketler = ",".join(temiz) if temiz else None

        return {**gorev, "baslik": baslik, "oncelik": oncelik, "etiketler": etiketler}

    def calistir(self) -> dict:
        guncellenen = 0
        hatalar = []
        try:
            gorevler = tasks.gorevleri_yukle()
            for gorev in gorevler:
                norm = self.normalize(gorev)
                degisen = {}
                if norm["baslik"] != gorev["baslik"]:
                    degisen["baslik"] = norm["baslik"]
                if norm["oncelik"] != gorev["oncelik"]:
                    degisen["oncelik"] = norm["oncelik"]
                if norm["etiketler"] != gorev["etiketler"]:
                    degisen["etiketler"] = norm["etiketler"].split(",") if norm["etiketler"] else []
                if degisen:
                    tasks.gorev_duzenle(gorev["id"], **degisen)
                    guncellenen += 1
            self.olay_kaydet("calistirma", f"{guncellenen} görev normalize edildi.")
        except Exception as e:
            hatalar.append(str(e))
            self.olay_kaydet("hata", str(e))
        return {"ajan": self.ajan_adi, "guncellenen": guncellenen, "hatalar": hatalar}
