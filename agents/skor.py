from datetime import date, timedelta
from agents.base import TemelAjan
import tasks


class SkorAjan(TemelAjan):
    @property
    def ajan_adi(self):
        return "SkorAjan"

    def calistir(self) -> dict:
        bugun = str(date.today())
        try:
            tasks._init_db()
            with tasks._baglan() as con:
                tamamlananlar = con.execute(
                    "SELECT * FROM gorevler WHERE durum = 'tamamlandi' AND tamamlanma LIKE ?",
                    (f"{bugun}%",)
                ).fetchall()
                toplam_aktif_sayi = con.execute(
                    "SELECT COUNT(*) FROM gorevler WHERE durum = 'aktif'"
                ).fetchone()[0]

            tamamlanan_sayi = len(tamamlananlar)
            zamaninda_sayi = sum(
                1 for r in tamamlananlar
                if r["son_tarih"] is None or r["tamamlanma"][:10] <= r["son_tarih"]
            )
            gec_tamamlanan = tamamlanan_sayi - zamaninda_sayi

            toplam = tamamlanan_sayi + toplam_aktif_sayi
            tamamlanma_orani = tamamlanan_sayi / toplam if toplam > 0 else 0.0
            zamaninda_orani = zamaninda_sayi / tamamlanan_sayi if tamamlanan_sayi > 0 else 0.0

            seri = self._seri_hesapla(bugun)

            tasks.gunluk_skor_kaydet(
                bugun, tamamlanan_sayi, toplam_aktif_sayi,
                zamaninda_sayi, gec_tamamlanan,
                round(tamamlanma_orani, 4), round(zamaninda_orani, 4), seri
            )
            self.olay_kaydet("calistirma", f"Günlük skor kaydedildi: {tamamlanan_sayi} tamamlanan.")
            return {
                "ajan": self.ajan_adi,
                "tarih": bugun,
                "tamamlanan_sayi": tamamlanan_sayi,
                "seri": seri,
            }
        except Exception as e:
            self.olay_kaydet("hata", str(e))
            return {"ajan": self.ajan_adi, "hata": str(e)}

    def _seri_hesapla(self, bugun: str) -> int:
        gecmis = tasks.skor_gecmisini_getir(limit=365)
        aktif_gunler = {r["tarih"] for r in gecmis if r["tamamlanan_sayi"] > 0}
        seri = 0
        kontrol = date.fromisoformat(bugun) - timedelta(days=1)
        while str(kontrol) in aktif_gunler:
            seri += 1
            kontrol -= timedelta(days=1)
        return seri
