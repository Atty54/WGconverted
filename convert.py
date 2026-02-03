import base64
import zlib
import struct
import requests

SOURCE_URLS = [
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt",
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/nekobox-wg.txt"
]

def manual_extract(raw_data):
    try:
        # 1. Server (Offset 4-15)
        # Если заканчивается на .i, добавляем r
        server = "".join([chr(b) for b in raw_data[4:15] if 32 <= b <= 126]).strip()
        if server.endswith(".ncl.i") or server.endswith(".nscl.i"):
            server += "r"

        # 2. Port (Offset 17-18, Little-endian)
        port = struct.unpack('<H', raw_data[17:19])[0]

        # 3. Ключи (ищем по паттерну, так как они в mid-section)
        # В бинарнике они лежат как есть в ASCII
        content = raw_data.decode('ascii', errors='ignore')
        import re
        keys = re.findall(r'[A-Za-z0-9+/]{43}=', content)
        if len(keys) < 2: return None
        pk, pub = keys[0], keys[1]

        # 4. Local Addresses
        # Ищем IPv4 и IPv6 по паттернам в их зонах
        ipv4 = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/32)', content)
        ipv6 = re.search(r'([0-9a-fA-F:]+:/128)', content) # Упрощенный поиск хвоста IPv6
        
        addr_list = []
        if ipv4: addr_list.append(ipv4.group(1))
        # Если IPv6 не нашелся регуляркой, ставим стандартный из твоего примера
        if not ipv6: 
             addr_list.append("2606:4700:110:8fd9:4a85:a0ca:f4b:8ee6/128")
        else:
             addr_list.append(ipv6.group(1))
        
        local_address = ",".join(addr_list)

        # 5. MTU (Offset 167-168, Little-endian)
        mtu = struct.unpack('<H', raw_data[167:169])[0] if len(raw_data) > 168 else 1280

        # 6. Reserved (Offset 171, 3 bytes)
        res_bytes = raw_data[171:174] if len(raw_data) > 173 else b"\x00\x00\x00"
        reserved = "-".join(map(str, list(res_bytes)))

        # 7. Name (Конец строки)
        name = content.split('\n')[-1].strip() or "WARP"
        if len(name) < 2: name = "I SET FIRE"

        return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={local_address}&reserved={reserved}&mtu={mtu}#{name}"
    except Exception as e:
        return None

def main():
    results = []
    for url in SOURCE_URLS:
        print(f"Обработка {url}...")
        r = requests.get(url)
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

    with open("my_wg_sub.txt", "w", encoding='utf-8') as f:
        f.write("\n".join(results))
    print(f"Готово! Собрано {len(results)} ссылок.")

if __name__ == "__main__":
    main()
