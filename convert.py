import base64
import zlib
import struct
import re
import requests

SOURCE_URLS = [
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/nekobox-wg.txt"
]
OUTPUT_FILE = "my_wg_sub.txt"

def manual_extract(raw_data):
    try:
        # 1. СЕРВЕР: Читаем до первого байта < 32
        server_bytes = []
        for b in raw_data[4:40]:
            if b < 32: break
            server_bytes.append(b)
        server_raw = bytes(server_bytes).decode('ascii', errors='ignore').strip()
        
        # Индекс конца домена
        end_server_idx = 4 + len(server_bytes)

        # Фикс домена .ir
        if server_raw.endswith(".ncl.i") or server_raw.endswith(".nscl.i"):
            server_raw += "r"

        # 2. ПОРТ: Little-Endian (<H)
        # Пропускаем 1 байт (разделитель) после домена
        port_offset = end_server_idx + 1
        port = struct.unpack('<H', raw_data[port_offset:port_offset+2])[0]
        
        # Если порт слишком мал (например, попали на разделитель), 
        # пробуем сдвинуться на 1 байт вперед
        if port < 100:
            port = struct.unpack('<H', raw_data[port_offset+1:port_offset+3])[0]

        # 3. КЛЮЧИ
        content = raw_data.decode('ascii', errors='ignore')
        keys = re.findall(r'[A-Za-z0-9+/]{43}=', content)
        if len(keys) < 2: return None
        pk, pub = keys[0], keys[1]

        # 4. ИМЕНА: Adele или OPS
        name = "WARP"
        if "I SET FIRE" in content: name = "I SET FIRE"
        elif "TO THE RAIN" in content: name = "TO THE RAIN"
        else:
            name_match = re.search(r'(OPS\s*-\s*\d+)', content)
            if name_match: name = name_match.group(1)
            else: name = re.sub(r'[^A-Z0-9\-\s]', '', content[-15:]).strip()
        
        # 5. IP АДРЕСА: Только чистые группы цифр (убираем спецсимволы в конце)
        ipv4_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', content)
        ipv6_match = re.search(r'([0-9a-fA-F:]+:[0-9a-fA-F:]+)', content)
        
        addrs = []
        if ipv4_match: addrs.append(f"{ipv4_match.group(1)}/32")
        if ipv6_match:
            v6 = ipv6_match.group(1).strip(':')
            if v6.count(':') >= 2: addrs.append(f"{v6}/128")
        local_address = ",".join(addrs)

        # 6. RESERVED и MTU (привязка к имени)
        name_idx = raw_data.find(name[:5].encode())
        if name_idx > 20:
            # Reserved: 3 байта перед именем (с учетом разделителя)
            res_bytes = raw_data[name_idx-4:name_idx-1]
            if 0 in list(res_bytes): res_bytes = raw_data[name_idx-5:name_idx-2]
            
            # MTU: пробуем найти 1280 (00 05) или 1420 (8C 05) в зоне перед Reserved
            mtu = 1280
            mtu_area = raw_data[name_idx-10:name_idx-3]
            for i in range(len(mtu_area)-1):
                m = struct.unpack('<H', mtu_area[i:i+2])[0]
                if 1200 <= m <= 1500:
                    mtu = m
                    break
        else:
            res_bytes = raw_data[171:174]
            mtu = 1280

        reserved = "-".join(map(str, list(res_bytes)))

        return f"wg://{server_raw}:{port}?private_key={pk}&public_key={pub}&local_address={local_address}&reserved={reserved}&mtu={mtu}#{name}"
    except:
        return None

def main():
    results = []
    for url in SOURCE_URLS:
        try:
            r = requests.get(url, timeout=15)
            for line in r.text.splitlines():
                if '?' not in line: continue
                try:
                    payload = line.split('?')[1].replace('-', '+').replace('_', '/')
                    payload += "=" * (-len(payload) % 4)
                    decoded = base64.b64decode(payload)
                    if decoded[0] == 0x78:
                        raw = zlib.decompress(decoded)
                        link = manual_extract(raw)
                        if link: results.append(link)
                except: continue
        except: continue

    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        f.write("\n".join(results))
    print(f"Done: {len(results)}")

if __name__ == "__main__":
    main()
