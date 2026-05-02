import argparse
import sys
import os
from pathlib import Path

# ANSI renk kodları (folder_tree.py ile uyumlu)
class Colors:
    DIR = '\033[94m'      # Mavi
    FILE = '\033[0m'      # Varsayılan
    SIZE = '\033[93m'     # Sarı
    RESET = '\033[0m'
    SUCCESS = '\033[92m'  # Yeşil
    ERROR = '\033[91m'    # Kırmızı

def format_size(size_in_bytes):
    """Bayt cinsinden boyutu okunabilir formata dönüştürür (KB, MB, GB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"

def get_dir_size(path):
    """Bir klasörün toplam boyutunu rekürsif olarak hesaplar."""
    total_size = 0
    try:
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # Kısayolları (symlink) atla
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
    except PermissionError:
        pass
    return total_size

class FolderAnalyzer:
    """Klasör boyutunu ve büyük dosyaları analiz eden ana sınıf."""
    
    def __init__(self, root_dir, top_n=5, use_color=True):
        self.root_dir = Path(root_dir)
        self.top_n = top_n
        self.use_color = use_color

    def _color(self, text, color_code):
        """Metne renk ekler."""
        if self.use_color:
            return f"{color_code}{text}{Colors.RESET}"
        return str(text)

    def analyze(self):
        if not self.root_dir.exists() or not self.root_dir.is_dir():
            print(self._color(f"❌ Hata: '{self.root_dir}' geçerli bir klasör değil.", Colors.ERROR))
            sys.exit(1)

        print(self._color(f"🔍 '{self.root_dir.resolve()}' dizini analiz ediliyor...\n", Colors.SUCCESS))

        dir_sizes = []
        all_files = []

        try:
            # Sadece kök dizindeki alt klasörleri listele
            for item in self.root_dir.iterdir():
                if item.is_dir():
                    size = get_dir_size(item)
                    dir_sizes.append((item, size))

            # Klasör içindeki TÜM dosyaları tarayarak en büyükleri bul
            for dirpath, _, filenames in os.walk(self.root_dir):
                for f in filenames:
                    fp = Path(dirpath) / f
                    if not fp.is_symlink() and fp.exists():
                        try:
                            all_files.append((fp, fp.stat().st_size))
                        except Exception:
                            pass

        except PermissionError:
            print(self._color("❌ Bazı dosyalara erişim izni reddedildi.", Colors.ERROR))

        # Genel Toplam Boyutu Hesapla
        total_size = get_dir_size(self.root_dir)

        # 1. Genel Bilgiler
        print(f"📊 {self._color('Toplam Boyut:', Colors.DIR)} {self._color(format_size(total_size), Colors.SIZE)}\n")

        # 2. Alt Klasör Boyutları
        print(f"📁 {self._color('Alt Klasör Boyutları:', Colors.DIR)}")
        dir_sizes.sort(key=lambda x: x[1], reverse=True)
        if not dir_sizes:
            print("   (Alt klasör bulunamadı)")
            
        for index, (d, size) in enumerate(dir_sizes):
            is_last = index == (len(dir_sizes) - 1)
            pointer = "└── " if is_last else "├── "
            print(f"   {pointer}{self._color(d.name, Colors.DIR)} - {self._color(format_size(size), Colors.SIZE)}")

        print("")

        # 3. En Büyük Dosyalar
        print(f"📄 {self._color(f'En Büyük {self.top_n} Dosya:', Colors.FILE)}")
        all_files.sort(key=lambda x: x[1], reverse=True)
        top_files = all_files[:self.top_n]
        
        if not top_files:
            print("   (Dosya bulunamadı)")
            
        for index, (f, size) in enumerate(top_files):
            is_last = index == (len(top_files) - 1)
            pointer = "└── " if is_last else "├── "
            try:
                # Dosya yolunu kök dizine göre göreceli (relative) göster
                rel_path = f.relative_to(self.root_dir)
            except ValueError:
                rel_path = f.name
                
            print(f"   {pointer}{self._color(rel_path, Colors.FILE)} - {self._color(format_size(size), Colors.SIZE)}")

def main():
    parser = argparse.ArgumentParser(
        description="Klasör Boyutu Analiz Aracı\n"
                    "Belirtilen klasörün toplam boyutunu, içindeki alt klasörlerin\n"
                    "boyutlarını ve en çok yer kaplayan dosyaları gösterir.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        "path", 
        nargs="?", 
        default=".", 
        help="Analiz edilecek klasör yolu (varsayılan: bulunulan dizin '.')"
    )
    parser.add_argument(
        "-n", "--top", 
        type=int, 
        default=5,
        help="Gösterilecek en büyük dosya sayısı (varsayılan: 5)"
    )
    parser.add_argument(
        "--no-color", 
        action="store_true", 
        help="Terminaldeki renkli çıktıyı devre dışı bırak"
    )

    args = parser.parse_args()
    use_color = not args.no_color

    analyzer = FolderAnalyzer(
        root_dir=args.path,
        top_n=args.top,
        use_color=use_color
    )
    
    analyzer.analyze()

if __name__ == "__main__":
    main()
