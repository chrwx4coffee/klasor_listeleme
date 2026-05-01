import argparse
import sys
from pathlib import Path

# ANSI renk kodları
class Colors:
    DIR = '\033[94m'      # Mavi
    FILE = '\033[0m'      # Varsayılan
    SYMLINK = '\033[36m'  # Camgöbeği (Cyan)
    RESET = '\033[0m'
    SUCCESS = '\033[92m'  # Yeşil
    ERROR = '\033[91m'    # Kırmızı

class TreeGenerator:
    """Klasör ağacını oluşturan ve yöneten ana sınıf."""
    
    def __init__(self, root_dir, output_file=None, max_depth=None, include_hidden=False, exclude=None, use_color=True):
        self.root_dir = Path(root_dir)
        self.output_file = output_file
        self.max_depth = max_depth
        self.include_hidden = include_hidden
        self.exclude = set(exclude) if exclude else set()
        self.use_color = use_color
        self.file_count = 0
        self.dir_count = 0

    def _get_color(self, path):
        """Dosya veya klasör tipine göre uygun rengi döndürür."""
        if not self.use_color:
            return ""
        if path.is_symlink():
            return Colors.SYMLINK
        if path.is_dir():
            return Colors.DIR
        return Colors.FILE

    def _reset_color(self):
        """Kullanılıyorsa renk sıfırlama kodunu döndürür."""
        return Colors.RESET if self.use_color else ""

    def generate(self):
        """Klasör ağacını oluşturur ve belirtilen hedefe (terminal/dosya) yazar."""
        if not self.root_dir.exists():
            print(f"{Colors.ERROR}❌ Hata: '{self.root_dir}' yolu bulunamadı.{Colors.RESET}")
            sys.exit(1)

        # Eğer çıktı dosyası belirtilmişse dosyaya yaz, aksi takdirde terminale bas
        output_stream = open(self.output_file, 'w', encoding='utf-8') if self.output_file else sys.stdout

        try:
            # Kök dizini yazdır
            icon = "📁" if self.root_dir.is_dir() else "📄"
            root_name = self.root_dir.resolve().name or str(self.root_dir)
            colored_root = f"{self._get_color(self.root_dir)}{root_name}{self._reset_color()}"
            output_stream.write(f"{icon} {colored_root}\n")
            
            # Klasör içindekileri dolaş
            if self.root_dir.is_dir():
                self._walk(self.root_dir, "", 0, output_stream)
                
            # Özeti yazdır
            summary = f"\n{self.dir_count} dizin, {self.file_count} dosya\n"
            output_stream.write(summary)
            
        except Exception as e:
            print(f"{Colors.ERROR}❌ Beklenmeyen bir hata oluştu: {e}{Colors.RESET}", file=sys.stderr)
        finally:
            if self.output_file:
                output_stream.close()
                print(f"{Colors.SUCCESS}✅ Klasör ağacı başarıyla '{self.output_file}' dosyasına kaydedildi.{Colors.RESET}")

    def _walk(self, current_dir, prefix, depth, output_stream):
        """Dizinleri rekürsif olarak dolaşır."""
        if self.max_depth is not None and depth >= self.max_depth:
            return

        try:
            # Klasörler üstte olacak şekilde alfabetik sırala
            paths = sorted(current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            output_stream.write(f"{prefix}    ❌ Erişim reddedildi\n")
            return

        # Gizli ve hariç tutulan dosyaları filtrele
        if not self.include_hidden:
            paths = [p for p in paths if not p.name.startswith('.')]
        
        if self.exclude:
            paths = [p for p in paths if p.name not in self.exclude]

        for index, path in enumerate(paths):
            is_last = index == (len(paths) - 1)
            pointer = "└── " if is_last else "├── "
            
            icon = "📁" if path.is_dir() else "📄"
            colored_name = f"{self._get_color(path)}{path.name}{self._reset_color()}"
            
            output_stream.write(f"{prefix}{pointer}{icon} {colored_name}\n")

            if path.is_dir():
                self.dir_count += 1
                extension = "    " if is_last else "│   "
                self._walk(path, prefix + extension, depth + 1, output_stream)
            else:
                self.file_count += 1

def main():
    parser = argparse.ArgumentParser(
        description="Gelişmiş Klasör Ağacı Oluşturucu (Terminal ve Dosya Çıktısı Destekli)\n"
                    "Bu araç, belirtilen dizinin veya bulunulan dizinin hiyerarşik\n"
                    "ağaç yapısını terminale yazdırır veya bir dosyaya kaydeder.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        "path", 
        nargs="?", 
        default=".", 
        help="Listelenecek klasör yolu (varsayılan: bulunulan dizin '.')"
    )
    parser.add_argument(
        "-o", "--output", 
        help="Çıktıyı terminal yerine bir dosyaya kaydet (örn: agac.txt)"
    )
    parser.add_argument(
        "-d", "--depth", 
        type=int, 
        help="Ağacın ineceği maksimum klasör derinliği"
    )
    parser.add_argument(
        "-a", "--all", 
        action="store_true", 
        dest="hidden",
        help="Gizli dosyaları ve klasörleri de dahil et (.git vb.)"
    )
    parser.add_argument(
        "-e", "--exclude", 
        nargs="+", 
        help="Hariç tutulacak dosya veya klasör isimleri (örn: node_modules __pycache__)"
    )
    parser.add_argument(
        "--no-color", 
        action="store_true", 
        help="Terminaldeki renkli çıktıyı devre dışı bırak"
    )

    args = parser.parse_args()

    # Dosyaya yazdırılıyorsa veya no-color seçilmişse renkleri kapat
    use_color = not args.no_color and not args.output

    tree = TreeGenerator(
        root_dir=args.path,
        output_file=args.output,
        max_depth=args.depth,
        include_hidden=args.hidden,
        exclude=args.exclude,
        use_color=use_color
    )
    
    tree.generate()

if __name__ == "__main__":
    main()
