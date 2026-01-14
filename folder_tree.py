import os
import argparse

def klasor_agaci_yaz(
    dizin_yolu,
    dosya,
    girinti="",
    son_mu=True,
    seviye=0,
    max_seviye=None,
    gizli_dahil=False
):
    if max_seviye is not None and seviye > max_seviye:
        return

    isim = os.path.basename(dizin_yolu)
    ikon = "📁" if os.path.isdir(dizin_yolu) else "📄"

    if girinti == "":
        satir = f"{ikon} {dizin_yolu}"
    else:
        dal = "└── " if son_mu else "├── "
        satir = f"{girinti}{dal}{ikon} {isim}"

    dosya.write(satir + "\n")

    if not os.path.isdir(dizin_yolu):
        return

    try:
        ogeler = os.listdir(dizin_yolu)
    except PermissionError:
        dosya.write(girinti + "    ❌ Erişim reddedildi\n")
        return

    if not gizli_dahil:
        ogeler = [o for o in ogeler if not o.startswith(".")]

    # klasörler üstte, alfabetik sıralı
    ogeler.sort(key=lambda x: (not os.path.isdir(os.path.join(dizin_yolu, x)), x.lower()))

    for index, oge in enumerate(ogeler):
        oge_yolu = os.path.join(dizin_yolu, oge)
        son_oge_mi = index == len(ogeler) - 1
        yeni_girinti = girinti + ("    " if son_mu else "│   ")

        klasor_agaci_yaz(
            oge_yolu,
            dosya,
            yeni_girinti,
            son_oge_mi,
            seviye + 1,
            max_seviye,
            gizli_dahil
        )


# === CLI ===
parser = argparse.ArgumentParser(description="📂 Klasör ağacı oluşturucu")
parser.add_argument("path", help="Listelenecek klasör yolu")
parser.add_argument("-o", "--output", default="klasor_agaci.txt", help="Çıktı dosyası")
parser.add_argument("-d", "--depth", type=int, help="Maksimum derinlik")
parser.add_argument("--hidden", action="store_true", help="Gizli dosyaları dahil et")

args = parser.parse_args()

if not os.path.exists(args.path):
    print("❌ Yol bulunamadı")
    exit()

with open(args.output, "w", encoding="utf-8") as dosya:
    klasor_agaci_yaz(
        args.path,
        dosya,
        max_seviye=args.depth,
        gizli_dahil=args.hidden
    )

print(f"✅ Klasör ağacı oluşturuldu → {args.output}")
