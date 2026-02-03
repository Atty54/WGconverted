import base64
import zlib
import struct
import re
import requests

SOURCE_URLS = [
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt",
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/nekobox-wg.txt"
]
OUTPUT_FILE = "my_wg_sub.txt"

def manual_extract(raw_data):
    try:
        # 1. Server (Offset 4-15)
        # Декодируем кусок и чистим от непечатных символов
        server_raw = "".join([chr(b) if 32 <= b <= 126 else "" for b in raw_data[4:16]]).strip()
        # Фикс для доменов .ir
        if ".ncl.i" in server_raw and not server_raw.endswith("r"):
            server_raw = server_raw.replace(".ncl.i", ".ncl.ir").replace(".nscl.i", ".nscl.ir")
        
        # 2. Port (Offset 17-18, Little-endian uint16)
        port = struct.unpack('<H', raw_data[17:19])[0]

        # 3. Ключи и адреса через RegEx по всему массиву (самый надежный способ)
        content = raw_data.decode('ascii', errors='ignore')
        
        # Ищем ключи (Base64, 43-44 символа)
        keys = re.findall(r'[A-Za-z0-9+/]{43}=', content)
        if len(keys) < 2: return None
        pk, pub = keys[0], keys[1]

        # Ищем IPv4 и IPv6
        ipv4 = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/32)', content)
        ipv6 = re.search(r'([0-9a-fA-F:]+:[0-9a-fA-F:]+/[0-9]+)', content)
        
        addrs = []
        if ipv4: addrs.append(ipv4.group(1))
        if ipv6: addrs.append(ipv6.group(1))
        # Если пусто — ставим дефолт из твоего разбора
        local_address = ",".join(addrs) if addrs else "172.16.0.2/32,2606:4700:110:8fd9:4a85:a0ca:f4b:8ee6/128"

        # 4. MTU (Offset 167-168)
        mtu = 1280
        if len(raw_data) > 168:
            mtu = struct.unpack('<H', raw_data[167:169])[0]

        # 5. Reserved (Offset 171-173, 3 bytes)
        reserved = "0-0-0"
        if len(raw_data) > 173:
            res_bytes = raw_data[171:174]
            reserved = "-".join(map(str, list(res_bytes)))

        # 6. Имя профиля (обычно в самом конце)
        name_match = re.findall(r'[A-Z\s]{3,}', content)
        name = name_match[-1].strip() if name_match else "WARP"

        return f"wg://{server_raw}:{port}?private_key={pk}&public_key={pub}&local_address={local_address}&reserved={reserved}&mtu={mtu}#{name}"
    except Exception:
        return None

def main():
    results = []
    for url in SOURCE_URLS:
        print(f"Парсинг {url}...")
        try:
            r = requests.get(url, timeout=10)
            for line in r.text.splitlines():
                if '?' not in line: continue
                
                # Base64 -> Zlib -> Extract
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

    if results:
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            f.write("\n".join(results))
        print(f"Успех! Сгенерировано ссылок: {len(results)}")
    else:
        print("Ссылок не найдено. Проверь структуру входных данных.")

if __name__ == "__main__":
    main()
