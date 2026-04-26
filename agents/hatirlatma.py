from agents.base import TemelAjan
import tasks

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    _RENK = True
except ImportError:
    _RENK = False

_PREFIX = {"gecmis": "[!]", "bugun": "[•]", "yarin": "[-]"}
_RENKLER = {"gecmis": "\033[31m", "bugun": "\033[33m", "yarin": "\033[36m"}
_RESET = "\033[0m"


class HatirlatmaAjan(TemelAjan):
    @property
    def ajan_adi(self):
        return "HatirlatmaAjan"

    def calistir(self) -> dict:
        from datetime import date, timedelta
        toplam = 0
        try:
            toplam += self._isle(tasks.gecmis_gorevler(), "gecmis")
            toplam += self._isle(tasks.bugunun_gorevleri(), "bugun")
            yarin = str(date.today() + timedelta(days=1))
            yarinki = [g for g in tasks.yaklasan_gorevler(gun=1) if g["son_tarih"] == yarin]
            toplam += self._isle(yarinki, "yarin")
            self.olay_kaydet("calistirma", f"{toplam} bildirim oluşturuldu.")
        except Exception as e:
            self.olay_kaydet("hata", str(e))
        return {"ajan": self.ajan_adi, "olusturulan_bildirim": toplam}

    def _isle(self, gorevler, tur):
        sayi = 0
        for gorev in gorevler:
            if tasks._bildirim_var_mi(gorev["id"], tur):
                continue
            mesaj = self._mesaj_olustur(gorev, tur)
            tasks.bildirim_ekle(gorev["id"], tur, mesaj)
            self._terminale_yaz(mesaj, tur)
            sayi += 1
        return sayi

    def _mesaj_olustur(self, gorev, tur):
        baslik = gorev["baslik"]
        if tur == "gecmis":
            return f"Gecikmiş: {baslik} (son tarih: {gorev['son_tarih']})"
        elif tur == "bugun":
            return f"Bugün: {baslik}"
        return f"Yarın bitiyor: {baslik}"

    def _terminale_yaz(self, mesaj, tur):
        prefix = _PREFIX.get(tur, "[?]")
        if _RENK:
            renk = _RENKLER.get(tur, "")
            print(f"{renk}{prefix} {mesaj}{_RESET}")
        else:
            print(f"{prefix} {mesaj}")
