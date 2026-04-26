from colorama import init, Fore, Style
from tasks import (
    gorev_ekle, gorev_tamamla, gorev_arsivle,
    gorev_aktife_al, gorev_sil,
    gorevleri_yukle, arsivi_yukle,
)

init(autoreset=True)

_ONCELIK_RENK = {
    "yuksek": Fore.RED,
    "normal": Fore.YELLOW,
    "dusuk":  Fore.GREEN,
}


def _oncelik_str(oncelik):
    renk = _ONCELIK_RENK.get(oncelik, "")
    return f"{renk}[{oncelik}]{Style.RESET_ALL}"


def sira_no_to_id(sira_no):
    """Kullanıcının gördüğü sıra numarasını iç ID'ye çevirir. Geçersizse None döner."""
    gorevler = gorevleri_yukle()
    if 1 <= sira_no <= len(gorevler):
        return gorevler[sira_no - 1]["id"]
    return None


def gorevleri_goster():
    gorevler = gorevleri_yukle()
    if not gorevler:
        print("Henüz görev yok.")
        return
    print("\n--- GÖREVLER ---")
    for sira, g in enumerate(gorevler, start=1):
        tamamlandi = g.get("durum") == "tamamlandi"
        durum_simge = f"{Fore.GREEN}✓{Style.RESET_ALL}" if tamamlandi else f"{Fore.CYAN}○{Style.RESET_ALL}"
        baslik = f"{Style.DIM}{g['baslik']}{Style.RESET_ALL}" if tamamlandi else g["baslik"]
        oncelik = _oncelik_str(g.get("oncelik", "normal"))
        son_tarih = f"  {Fore.MAGENTA}→ {g['son_tarih']}{Style.RESET_ALL}" if g.get("son_tarih") else ""
        print(f"  [{durum_simge}] {sira}.  {baslik}  {oncelik}{son_tarih}")
    print()


def arsivi_goster():
    arsiv = arsivi_yukle()
    if not arsiv:
        print("Arşiv boş.")
        return
    print("\n--- ARŞİV ---")
    for sira, g in enumerate(arsiv, start=1):
        durum = f"{Fore.GREEN}✓{Style.RESET_ALL}" if g.get("tamamlanma") else f"{Fore.CYAN}○{Style.RESET_ALL}"
        tarih = g.get("arsivlenme", "-")
        oncelik = _oncelik_str(g.get("oncelik", "normal"))
        print(f"  [{durum}] {sira}. {Style.DIM}{g['baslik']}{Style.RESET_ALL}  {oncelik}  {tarih}")
    print()


def aktif_olmayan_gorevleri_goster():
    """Tamamlanmış ve arşivlenmiş görevleri numaralı listeler."""
    tamamlananlar = [g for g in gorevleri_yukle() if g.get("durum") == "tamamlandi"]
    arsivlenenler = arsivi_yukle()
    liste = tamamlananlar + arsivlenenler
    if not liste:
        print("Aktife alınabilecek görev yok.")
        return []
    print("\n--- AKTİFE ALINABİLECEK GÖREVLER ---")
    for sira, g in enumerate(liste, start=1):
        etiket = "tamamlandı" if g.get("durum") == "tamamlandi" else "arşivlendi"
        renk = Fore.GREEN if etiket == "tamamlandı" else Fore.BLUE
        print(f"  {sira}. {g['baslik']}  {renk}[{etiket}]{Style.RESET_ALL}")
    print()
    return liste


def menu():
    print(f"\n{Fore.CYAN}=== GÖREV YÖNETİCİSİ ==={Style.RESET_ALL}")
    print("1. Görev ekle")
    print("2. Görevi tamamla")
    print("3. Görevi arşivle")
    print("4. Görevleri listele")
    print("5. Arşivi görüntüle")
    print("6. Görevi aktife al")
    print("7. Arşivden kalıcı sil")
    print("0. Çıkış")
    return input("Seçim: ").strip()


def main():
    print(f"{Fore.CYAN}Hoş geldin!{Style.RESET_ALL}")
    while True:
        secim = menu()

        if secim == "1":
            baslik = input("Görev adı: ").strip()
            oncelik = input("Öncelik (dusuk / normal / yuksek) [varsayılan: normal]: ").strip() or "normal"
            try:
                gorev = gorev_ekle(baslik, oncelik)
                print(f"{Fore.GREEN}Eklendi:{Style.RESET_ALL} {gorev['baslik']} | Öncelik: {_oncelik_str(gorev['oncelik'])}")
            except ValueError as e:
                print(f"{Fore.RED}Hata:{Style.RESET_ALL} {e}")

        elif secim == "2":
            gorevleri_goster()
            try:
                sira = int(input("Tamamlanacak görev sıra no: "))
                gorev_id = sira_no_to_id(sira)
                if not gorev_id:
                    print(f"{Fore.RED}Geçersiz sıra numarası.{Style.RESET_ALL}")
                else:
                    gorev = gorevleri_yukle()[sira - 1]
                    if gorev.get("durum") == "tamamlandi":
                        print("Bu görev zaten tamamlanmış.")
                    elif gorev_tamamla(gorev_id):
                        print(f"{Fore.GREEN}Görev tamamlandı!{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Geçersiz giriş.{Style.RESET_ALL}")

        elif secim == "3":
            gorevleri_goster()
            try:
                sira = int(input("Arşivlenecek görev sıra no: "))
                gorev_id = sira_no_to_id(sira)
                if gorev_id and gorev_arsivle(gorev_id):
                    print(f"{Fore.BLUE}Görev arşivlendi.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Geçersiz sıra numarası.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Geçersiz giriş.{Style.RESET_ALL}")

        elif secim == "4":
            gorevleri_goster()

        elif secim == "5":
            arsivi_goster()

        elif secim == "6":
            liste = aktif_olmayan_gorevleri_goster()
            if liste:
                try:
                    sira = int(input("Aktife alınacak görev sıra no: "))
                    if 1 <= sira <= len(liste):
                        gorev_id = liste[sira - 1]["id"]
                        if gorev_aktife_al(gorev_id):
                            print(f"{Fore.GREEN}Görev aktife alındı.{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}Geçersiz sıra numarası.{Style.RESET_ALL}")
                except ValueError:
                    print(f"{Fore.RED}Geçersiz giriş.{Style.RESET_ALL}")

        elif secim == "7":
            arsivi_goster()
            arsiv = arsivi_yukle()
            if arsiv:
                try:
                    sira = int(input("Kalıcı silinecek görev sıra no: "))
                    if 1 <= sira <= len(arsiv):
                        gorev_id = arsiv[sira - 1]["id"]
                        onay = input(f"{Fore.RED}'{arsiv[sira-1]['baslik']}' kalıcı silinsin mi? (e/h):{Style.RESET_ALL} ").strip().lower()
                        if onay == "e":
                            gorev_sil(gorev_id)
                            print(f"{Fore.RED}Görev kalıcı olarak silindi.{Style.RESET_ALL}")
                        else:
                            print("İptal edildi.")
                    else:
                        print(f"{Fore.RED}Geçersiz sıra numarası.{Style.RESET_ALL}")
                except ValueError:
                    print(f"{Fore.RED}Geçersiz giriş.{Style.RESET_ALL}")

        elif secim == "0":
            print(f"{Fore.CYAN}Görüşürüz!{Style.RESET_ALL}")
            break

        else:
            print(f"{Fore.RED}Geçersiz seçim.{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
