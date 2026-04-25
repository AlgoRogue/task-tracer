from tasks import gorev_ekle, gorev_tamamla, gorev_arsivle, gorevleri_yukle, arsivi_yukle


def gorevleri_goster():
    gorevler = gorevleri_yukle()
    if not gorevler:
        print("Henüz görev yok.")
        return
    print("\n--- GÖREVLER ---")
    for g in gorevler:
        durum = "✓" if g.get("durum") == "tamamlandi" else "○"
        oncelik = g.get("oncelik", "normal")
        print(f"  [{durum}] ID:{g['id']}  {g['baslik']}  [{oncelik}]")
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
        print(f"  [{durum}] ID:{g['id']}  {g['baslik']}  [{g.get('oncelik','normal')}]  {tarih}")
    print()


def menu():
    print("\n=== GÖREV YÖNETİCİSİ ===")
    print("1. Görev ekle")
    print("2. Görevi tamamla")
    print("3. Görevi arşivle")
    print("4. Görevleri listele")
    print("5. Arşivi görüntüle")
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
                gorev_id = int(input("Arşivlenecek görev ID: "))
                if gorev_arsivle(gorev_id):
                    print("Görev arşivlendi.")
                else:
                    print("Görev bulunamadı.")
            except ValueError:
                print("Geçersiz ID.")

        elif secim == "4":
            gorevleri_goster()

        elif secim == "5":
            arsivi_goster()

        elif secim == "0":
            print("Görüşürüz!")
            break

        else:
            print("Geçersiz seçim.")


if __name__ == "__main__":
    main()
