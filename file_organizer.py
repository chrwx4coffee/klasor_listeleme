import argparse
import sys
import shutil
from pathlib import Path

# ANSI renk kodları
class Colors:
    DIR = '\033[94m'      # Mavi
    FILE = '\033[0m'      # Varsayılan
    INFO = '\033[36m'     # Camgöbeği (Cyan)
    RESET = '\033[0m'
    SUCCESS = '\033[92m'  # Yeşil
    WARNING = '\033[93m'  # Sarı
    ERROR = '\033[91m'    # Kırmızı

# Kategori ve uzantı eşleştirmeleri
CATEGORIES = {
    "Resimler": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff", ".ico"],
    "Belgeler": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf", ".csv", ".md"],
    "Videolar": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".ts"],
    "Ses_Dosyalari": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".wma", ".m4a"],
    "Arsivler": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
    "Yazilim_ve_Kod": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".h", ".json", ".xml", ".sh", ".bat", ".yaml", ".yml", ".sql"],
    "Diger": [] # Eşleşmeyen uzantılar için varsayılan kategori
}

# Güvenlik amacıyla bu script dosyalarının kendilerini taşımasını engelliyoruz
IGNORE_FILES = {"folder_tree.py", "folder_size.py", "file_organizer.py"}

def get_category(extension):
    """Verilen uzantıya göre uygun kategoriyi döndürür."""
    ext_lower = extension.lower()
    for category, extensions in CATEGORIES.items():
        if ext_lower in extensions:
            return category
    return "Diger"

class FileOrganizer:
    """Dosyaları uzantılarına göre sınıflandıran ve klasörleyen ana sınıf."""
    
    def __init__(self, root_dir, dry_run=False, use_color=True):
        self.root_dir = Path(root_dir)
        self.dry_run = dry_run
        self.use_color = use_color
        self.moved_files = 0

    def _color(self, text, color_code):
        """Metne renk ekler."""
        if self.use_color:
            return f"{color_code}{text}{Colors.RESET}"
        return str(text)

    def organize(self):
        if not self.root_dir.exists() or not self.root_dir.is_dir():
            print(self._color(f"❌ Hata: '{self.root_dir}' geçerli bir klasör değil.", Colors.ERROR))
            sys.exit(1)

        mode_text = " (SİMÜLASYON MODU - Dosyalar gerçekte taşınmayacak)" if self.dry_run else ""
        print(self._color(f"🧹 '{self.root_dir.resolve()}' dizini düzenleniyor...{mode_text}\n", Colors.INFO))

        # Taşınacak işlemleri kategorilere göre grupla: { "Kategori": [(eski_yol, yeni_yol), ...] }
        operations = {cat: [] for cat in CATEGORIES.keys()}
        operations["Diger"] = []

        try:
            # Sadece kök dizindeki dosyaları tarar (alt klasörlere girmez)
            for item in self.root_dir.iterdir():
                if item.is_file() and item.name not in IGNORE_FILES:
                    # Gizli dosyaları atla (örneğin .gitignore, .DS_Store)
                    if item.name.startswith('.'):
                        continue
                        
                    category = get_category(item.suffix)
                    dest_dir = self.root_dir / category
                    dest_path = dest_dir / item.name
                    
                    operations[category].append((item, dest_path))

        except PermissionError:
            print(self._color("❌ Bazı dosyalara erişim izni reddedildi.", Colors.ERROR))
            sys.exit(1)

        # İşlemleri uygula ve terminale raporla
        for category, file_ops in operations.items():
            if not file_ops:
                continue

            print(f"📁 {self._color(category, Colors.DIR)}")
            
            dest_dir = self.root_dir / category
            
            # Simülasyon değilse ve klasör yoksa oluştur
            if not self.dry_run and not dest_dir.exists():
                dest_dir.mkdir(parents=True, exist_ok=True)

            for index, (src, dest) in enumerate(file_ops):
                is_last = index == (len(file_ops) - 1)
                pointer = "└── " if is_last else "├── "
                
                # Hedefte aynı isimli dosya varsa isim çakışmasını çöz (sayı ekle)
                actual_dest = dest
                if not self.dry_run and dest.exists():
                    base = dest.stem
                    ext = dest.suffix
                    counter = 1
                    while actual_dest.exists():
                        actual_dest = dest.with_name(f"{base}_{counter}{ext}")
                        counter += 1

                try:
                    if not self.dry_run:
                        shutil.move(str(src), str(actual_dest))
                    
                    self.moved_files += 1
                    status = self._color("Taşınacak" if self.dry_run else "Taşındı", Colors.SUCCESS)
                    print(f"   {pointer}{self._color(src.name, Colors.FILE)} -> {status}")
                except Exception as e:
                    status = self._color(f"Hata: {e}", Colors.ERROR)
                    print(f"   {pointer}{self._color(src.name, Colors.FILE)} -> {status}")
            
            print("")

        # Sonuç Özeti
        if self.moved_files == 0:
            print(self._color("ℹ️ Düzenlenecek dosya bulunamadı.", Colors.WARNING))
        else:
            action_word = "taşınması simüle edildi" if self.dry_run else "başarıyla sınıflandırıldı"
            print(self._color(f"✅ Toplam {self.moved_files} dosya {action_word}.", Colors.SUCCESS))

def main():
    parser = argparse.ArgumentParser(
        description="Dosya Sınıflandırma ve Düzenleme Aracı\n"
                    "Belirtilen klasördeki karmaşık dosyaları uzantılarına göre otomatik olarak\n"
                    "ilgili alt klasörlere (Resimler, Belgeler, Videolar vb.) taşır ve ayırır.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        "path", 
        nargs="?", 
        default=".", 
        help="Düzenlenecek klasör yolu (varsayılan: bulunulan dizin '.')"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Güvenli mod: Sadece simülasyon yapar, dosyaları gerçekte taşımaz"
    )
    parser.add_argument(
        "--no-color", 
        action="store_true", 
        help="Terminaldeki renkli çıktıyı devre dışı bırak"
    )

    args = parser.parse_args()
    use_color = not args.no_color

    organizer = FileOrganizer(
        root_dir=args.path,
        dry_run=args.dry_run,
        use_color=use_color
    )
    
    organizer.organize()

if __name__ == "__main__":
    main()
