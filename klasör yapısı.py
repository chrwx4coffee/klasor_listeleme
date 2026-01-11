import os

def klasor_agaci_yaz(dizin_yolu, dosya, girinti="", son_mu=True):
    if girinti == "":
        satir = dizin_yolu
    else:
        dal = "└── " if son_mu else "├── "
        satir = girinti + dal + os.path.basename(dizin_yolu)

    dosya.write(satir + "\n")

    if not os.path.isdir(dizin_yolu):
        return

    oge_listesi = os.listdir(dizin_yolu)
    oge_sayisi = len(oge_listesi)

    for index, oge in enumerate(oge_listesi):
        oge_yolu = os.path.join(dizin_yolu, oge)
        son_oge_mi = (index == oge_sayisi - 1)

        yeni_girinti = girinti + ("    " if son_mu else "│   ")
        klasor_agaci_yaz(oge_yolu, dosya, yeni_girinti, son_oge_mi)


# === ANA PROGRAM ===
girilen_yol = input("📂 Listelemek istediğiniz klasör yolunu girin: ").strip()

if not os.path.exists(girilen_yol):
    print("❌ Hata: Girilen yol bulunamadı.")
    exit()

if not os.path.isdir(girilen_yol):
    print("❌ Hata: Girilen yol bir klasör değil.")
    exit()

cikti_dosya_adi = "klasor_agaci.txt"

with open(cikti_dosya_adi, "w", encoding="utf-8") as dosya:
    klasor_agaci_yaz(girilen_yol, dosya)

print(f"✅ '{girilen_yol}' klasörü listelendi ve '{cikti_dosya_adi}' dosyasına kaydedildi.")
