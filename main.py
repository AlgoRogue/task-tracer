from tasks import gorev_ekle, gorev_tamamla, gorev_arsivle, gorev_aktife_al, gorevleri_yukle, arsivi_yukle


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
        durum = "✓" if g.get("durum") == "tamamlandi" else "○"
        oncelik = g.get("oncelik", "normal")
        print(f"  [{durum}] {sira}.  {g['baslik']}  [{oncelik}]")
    print()


def arsivi_goster():
    arsiv = arsivi_yukle()
    if not arsiv:
        print("Arşiv boş.")
        return
    print("\n--- ARŞİV ---")
    for g in arsiv:
        durum = "✓" if g.get("tamamlanma") else "○"
        tarih = g.get("arsivlenme", "-")
        print(f"  [{durum}] {g['baslik']}  [{g.get('oncelik','normal')}]  {tarih}")
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
        print(f"  {sira}. {g['baslik']}  [{etiket}]")
    print()
    return liste


def menu():
    print("\n=== GÖREV YÖNETİCİSİ ===")
    print("1. Görev ekle")
    print("2. Görevi tamamla")
    print("3. Görevi arşivle")
    print("4. Görevleri listele")
    print("5. Arşivi görüntüle")
    print("6. Görevi aktife al")
    print("0. Çıkış")
    return input("Seçim: ").strip()


def main():
    print("Hoş geldin!")
    while True:
        secim = menu()

        if secim == "1":
            baslik = input("Görev adı: ").strip()
            oncelik = input("Öncelik (dusuk / normal / yuksek) [varsayılan: normal]: ").strip() or "normal"
            try:
                gorev = gorev_ekle(baslik, oncelik)
                print(f"Eklendi: {gorev['baslik']} | Öncelik: {gorev['oncelik']}")
            except ValueError as e:
                print(f"Hata: {e}")

        elif secim == "2":
            gorevleri_goster()
            try:
                sira = int(input("Tamamlanacak görev sıra no: "))
                gorev_id = sira_no_to_id(sira)
                if not gorev_id:
                    print("Geçersiz sıra numarası.")
                else:
                    gorev = gorevleri_yukle()[sira - 1]
                    if gorev.get("durum") == "tamamlandi":
                        print("Bu görev zaten tamamlanmış.")
                    elif gorev_tamamla(gorev_id):
                        print("Görev tamamlandı!")
            except ValueError:
                print("Geçersiz giriş.")

        elif secim == "3":
            gorevleri_goster()
            try:
                sira = int(input("Arşivlenecek görev sıra no: "))
                gorev_id = sira_no_to_id(sira)
                if gorev_id and gorev_arsivle(gorev_id):
                    print("Görev arşivlendi.")
                else:
                    print("Geçersiz sıra numarası.")
            except ValueError:
                print("Geçersiz giriş.")

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
                            print("Görev aktife alındı.")
                    else:
                        print("Geçersiz sıra numarası.")
                except ValueError:
                    print("Geçersiz giriş.")

        elif secim == "0":
            print("Görüşürüz!")
            break

        else:
            print("Geçersiz seçim.")


if __name__ == "__main__":
    main()
