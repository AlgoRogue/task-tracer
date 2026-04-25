from tasks import gorev_ekle, gorev_tamamla, gorev_sil, gorevleri_yukle


def gorevleri_goster():
    gorevler = gorevleri_yukle()
    if not gorevler:
        print("Henüz görev yok.")
        return
    print("\n--- GÖREVLER ---")
    for g in gorevler:
        durum = "✓" if g["tamamlandi"] else "○"
        print(f"  [{durum}] {g['id']}. {g['baslik']}")
    print()


def menu():
    print("\n=== GÖREV YÖNETİCİSİ ===")
    print("1. Görev ekle")
    print("2. Görevi tamamla")
    print("3. Görevi sil")
    print("4. Görevleri listele")
    print("0. Çıkış")
    return input("Seçim: ").strip()


def main():
    print("Hoş geldin!")
    while True:
        secim = menu()

        if secim == "1":
            baslik = input("Görev adı: ").strip()
            if baslik:
                gorev = gorev_ekle(baslik)
                print(f"Eklendi: {gorev['baslik']} (ID: {gorev['id']})")

        elif secim == "2":
            gorevleri_goster()
            try:
                gorev_id = int(input("Tamamlanacak görev ID: "))
                if gorev_tamamla(gorev_id):
                    print("Görev tamamlandı!")
                else:
                    print("Görev bulunamadı.")
            except ValueError:
                print("Geçersiz ID.")

        elif secim == "3":
            gorevleri_goster()
            try:
                gorev_id = int(input("Silinecek görev ID: "))
                if gorev_sil(gorev_id):
                    print("Görev silindi.")
                else:
                    print("Görev bulunamadı.")
            except ValueError:
                print("Geçersiz ID.")

        elif secim == "4":
            gorevleri_goster()

        elif secim == "0":
            print("Görüşürüz!")
            break

        else:
            print("Geçersiz seçim.")


if __name__ == "__main__":
    main()
