import requests
import json
import re
import sys

base = "http://192.168.68.1"
session = requests.Session()

print("[*] TP-Link Deco Bilgi Toplama Aracı")
print("="*60)

# 1. models.json - Cihaz bilgileri
print("\n[1] models.json analizi...")
try:
    r = session.get(f"{base}/models.json", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"[+] Başarılı! Yanıt boyutu: {len(r.text)} bytes")
        
        # Tüm anahtarları göster
        if isinstance(data, dict):
            print(f"[+] Anahtarlar: {list(data.keys())}")
            
            # Önemli alanları yazdır
            important_fields = ['model', 'device_model', 'hardware_version', 'firmware_version', 
                              'mac', 'mac_address', 'serial', 'serial_number', 'device_id', 
                              'default_password', 'owner_id']
            
            for field in important_fields:
                if field in data:
                    print(f"    {field}: {data[field]}")
                # Nested arama
                for key, value in data.items():
                    if isinstance(value, dict):
                        if field in value:
                            print(f"    {key}.{field}: {value[field]}")
            
            # JSON'un tamamını dosyaya kaydet
            with open('models_full.json', 'w') as f:
                json.dump(data, f, indent=2)
            print("[+] Tam JSON models_full.json dosyasına kaydedildi")
            
            # MAC adresi ara
            json_str = json.dumps(data).lower()
            if 'mac' in json_str:
                mac_matches = re.findall(r'["\']?([0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2})["\']?', json_str)
                if mac_matches:
                    print(f"[!] MAC adresi bulundu: {mac_matches[0]}")
        else:
            print(f"[!] Beklenmeyen format: {type(data)}")
    else:
        print(f"[-] HTTP {r.status_code}")
except Exception as e:
    print(f"[-] Hata: {e}")

# 2. modules.json - Yüklü modüller
print("\n[2] modules.json analizi...")
try:
    r = session.get(f"{base}/modules.json", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"[+] Başarılı! {len(data) if isinstance(data, list) else len(data.keys())} modül")
        
        # LUA modüllerini listele
        if isinstance(data, list):
            for module in data[:20]:  # İlk 20
                if isinstance(module, dict):
                    print(f"    - {module.get('name', module.get('module', str(module)[:50]))}")
        elif isinstance(data, dict):
            for key in list(data.keys())[:20]:
                print(f"    - {key}")
                
        # Diagnosis modülü var mı?
        json_str = json.dumps(data).lower()
        if 'diagnosis' in json_str or 'diag' in json_str:
            print("[!] Diagnosis modülü mevcut!")
except Exception as e:
    print(f"[-] Hata: {e}")

# 3. classes.json - LUA sınıfları
print("\n[3] classes.json analizi...")
try:
    r = session.get(f"{base}/classes.json", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"[+] Başarılı!")
        
        # Önemli sınıfları ara
        json_str = json.dumps(data).lower()
        interesting_classes = ['system', 'network', 'firewall', 'admin', 'auth', 'login', 'setup', 'wizard']
        
        for cls in interesting_classes:
            if cls in json_str:
                print(f"    [!] '{cls}' sınıfı mevcut")
except Exception as e:
    print(f"[-] Hata: {e}")

# 4. API endpoint'lerini keşfet
print("\n[4] API/LuCI endpoint keşfi...")
endpoints = [
    "/cgi-bin/luci/",
    "/cgi-bin/luci/api/",
    "/cgi-bin/luci/admin/",
    "/cgi-bin/luci/admin/system/",
    "/cgi-bin/luci/admin/network/",
    "/cgi-bin/luci/admin/status/",
    "/api/",
    "/api/v1/",
    "/api/system/",
    "/api/device/",
    "/api/network/",
]

for ep in endpoints:
    try:
        r = session.get(base + ep, timeout=2, allow_redirects=False)
        if r.status_code == 200:
            print(f"[+] {ep} - 200 OK")
            # İçeriğin başlangıcını göster
            content_preview = r.text[:100].replace('\n', ' ')
            if content_preview.strip():
                print(f"    Önizleme: {content_preview}...")
        elif r.status_code in [301, 302]:
            loc = r.headers.get('Location', '?')
            print(f"[*] {ep} - {r.status_code} -> {loc}")
    except Exception as e:
        pass

# 5. Login mekanizmasını analiz et
print("\n[5] Login mekanizması analizi...")
login_urls = [
    "/login",
    "/cgi-bin/luci/login",
    "/cgi-bin/luci/admin/login",
    "/webpages/login.html",
    "/api/login",
]

for url in login_urls:
    try:
        r = session.get(base + url, timeout=2)
        if r.status_code == 200:
            print(f"[+] Login sayfası: {url}")
            # Form parametrelerini ara
            if 'password' in r.text.lower():
                print("    Password alanı mevcut")
            if 'owner' in r.text.lower():
                print("    Owner ID alanı mevcut")
            if 'challenge' in r.text.lower() or 'rsa' in r.text.lower():
                print("    Challenge-response mekanizması")
            
            # RSA keys endpoint'ini bul
            if 'keys' in r.text or 'modulus' in r.text:
                keys_match = re.search(r'["\']([^"\']*keys[^"\']*)["\']', r.text)
                if keys_match:
                    print(f"    Keys endpoint: {keys_match.group(1)}")
    except:
        pass

# 6. Farklı RSA keys endpoint'lerini dene
print("\n[6] RSA keys endpoint'i aranıyor...")
keys_endpoints = [
    "/login?form=keys",
    "/cgi-bin/luci/login?form=keys",
    "/cgi-bin/luci/;stok=/login?form=keys",
    "/api/auth/keys",
    "/api/login/keys",
]

for ep in keys_endpoints:
    try:
        r = session.get(base + ep, timeout=2)
        if r.status_code == 200:
            print(f"[+] Bulundu: {ep}")
            try:
                data = r.json()
                print(f"    Yanıt: {json.dumps(data)[:200]}")
                if 'seq' in data:
                    print(f"    [!] seq: {data['seq']}")
                if 'modulus' in data:
                    print(f"    [!] modulus mevcut")
                break
            except:
                print(f"    Yanıt (text): {r.text[:100]}")
    except:
        pass

# 7. Setup wizard sayfalarını bul
print("\n[7] Setup wizard sayfaları aranıyor...")
wizard_paths = [
    "/webpages/setup.html",
    "/webpages/wizard.html",
    "/webpages/welcome.html",
    "/webpages/owner.html",
    "/setup",
    "/wizard",
    "/cgi-bin/luci/admin/setup",
]

for path in wizard_paths:
    try:
        r = session.get(base + path, timeout=2, allow_redirects=False)
        if r.status_code == 200:
            print(f"[+] Wizard sayfası: {path}")
            if 'owner' in r.text.lower():
                print("    Owner ID sayfası")
            if 'welcome' in r.text.lower():
                print("    Welcome sayfası")
    except:
        pass

# 8. Cihazın web sunucusu bilgileri
print("\n[8] Web sunucu bilgileri...")
try:
    r = session.get(base + "/", timeout=2)
    server = r.headers.get('Server', 'Bilinmiyor')
    print(f"[+] Server: {server}")
    
    # Set-Cookie analizi
    cookies = r.headers.get('Set-Cookie', '')
    if cookies:
        print(f"[+] Cookie: {cookies[:100]}")
        
    # Yönlendirme var mı?
    if r.status_code in [301, 302]:
        print(f"[*] Yönlendirme: {r.headers.get('Location')}")
except:
    pass

print("\n" + "="*60)
print("[*] Bilgi toplama tamamlandı!")

# SSH için yeni şifre listesi oluştur
print("\n[9] SSH için potansiyel şifreler...")
# models.json'dan alınan bilgileri kullan
# Bu kısmı manuel olarak models_full.json'dan bakıp ekleyelim
print("[*] models_full.json dosyasını kontrol edin ve şu alanları arayın:")
print("    - MAC adresi")
print("    - Seri numarası")
print("    - Varsayılan şifre")
print("    - Device ID")