from tasks import gorev_ekle, gorev_tamamla, gorev_sil, gorevleri_yukle


def gorevleri_goster():
    gorevler = gorevleri_yukle()
    if not gorevler:
        print("Henüz görev yok.")
        return
    print("\n--- GÖREVLER ---")
    for g in gorevler:
        durum = "✓" if g["tamamlandi"] else "○"
        oncelik = g.get("oncelik", "normal")
        print(f"  [{durum}] {g['id']}. {g['baslik']}  [{oncelik}]")
    print()


def yardim_goster():
    print("""
=== YARDIM ===

  1. Görev ekle
     → Yeni bir görev oluşturur.
     → Öncelik sorulur: dusuk / normal / yuksek
     → Her görev otomatik bir ID alır.

  2. Görevi tamamla
     → Mevcut görevler listelenir.
     → ID girerek görevi tamamlandı olarak işaretlersin.
     → Tamamlanan görev [✓] ile görünür.

  3. Görevi sil
     → Mevcut görevler listelenir.
     → ID girerek görevi kalıcı olarak silersin.

  4. Görevleri listele
     → Tüm görevleri gösterir.
     → [○] = tamamlanmadı, [✓] = tamamlandı

  0. Çıkış
     → Programı kapatır. Görevler kaydedilmiş olur.

  5. Yardım
     → Bu ekranı gösterir.
""")


def menu():
    print("\n=== GÖREV YÖNETİCİSİ ===")
    print("1. Görev ekle")
    print("2. Görevi tamamla")
    print("3. Görevi sil")
    print("4. Görevleri listele")
    print("5. Yardım")
    print("0. Çıkış")
    return input("Seçim: ").strip()


def main():
    print("Hoş geldin!")
    while True:
        secim = menu()

        if secim == "1":
            baslik = input("Görev adı: ").strip()
            if baslik:
                oncelik = input("Öncelik (dusuk / normal / yuksek) [varsayılan: normal]: ").strip() or "normal"
                try:
                    gorev = gorev_ekle(baslik, oncelik)
                    print(f"Eklendi: {gorev['baslik']} | Öncelik: {gorev['oncelik']} (ID: {gorev['id']})")
                except ValueError as e:
                    print(f"Hata: {e}")

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

        elif secim == "5":
            yardim_goster()

        elif secim == "0":
            print("Görüşürüz!")
            break

        else:
            print("Geçersiz seçim.")


if __name__ == "__main__":
    main()
