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
        # 1. Сервер: от 4-го байта до первого нуля
        server_end = raw_data.find(b'\x00', 4)
        if server_end == -1: return None
        server = raw_data[4:server_end].decode('ascii', errors='ignore').strip()
        if server.endswith(".i"): server += "r"
        
        # 2. Порт: строго за сервером (через 1 байт типа поля)
        # В этой структуре Sing-box: [ID][LEN][DATA], порт обычно через 1-2 байта после домена
        port_idx = server_end + 2 
        if port_idx + 2 > len(raw_data): return None
        port = struct.unpack('<H', raw_data[port_idx:port_idx+2])[0]

        # 3. Ключи: ищем по маске Base64
        content_str = raw_data.decode('ascii', errors='ignore')
        keys = re.findall(r'[A-Za-z0-9+/]{42,43}=', content_str)
        if len(keys) < 2: return None
        pk, pub = keys[0], keys[1]

        # 4. IP-адреса: жадный поиск
        # Ищем группы цифр, разделенные точками, и не даем им обрываться на точке
        ipv4_candidates = re.findall(r'(\d{1,3}(?:\.\d{1,3}){3})', content_str)
        ipv6_candidates = re.findall(r'([0-9a-fA-F:]+:[0-9a-fA-F:]+(?:/[0-9]+)?)', content_str)
        
        addrs = []
        if ipv4_candidates:
            # Берем первый найденный IPv4 и убеждаемся, что он полный
            ip = ipv4_candidates[0]
            addrs.append(f"{ip}/32")
        if ipv6_candidates:
            ip = ipv6_candidates[0]
            if '/' not in ip: ip += "/128"
            addrs.append(ip)
        
        local_address = ",".join(addrs) if addrs else "172.16.0.2/32"

        # 5. MTU: ищем число в районе офсета 167
        mtu = 1280
        try:
            val = struct.unpack('<H', raw_data[167:169])[0]
            if 500 < val < 9000: # Просто проверка на адекватность
                mtu = val
        except: pass

        # 6. Reserved: 3 байта (обычно перед именем в конце)
        # Твой Reserved: 'MMqb' (48 203 166). Ищем 3 байта перед концом.
        res_bytes = raw_data[171:174]
        # Если там нули, берем байты 171-173 принудительно, какими бы они ни были
        reserved = "-".join(map(str, list(res_bytes)))

        # 7. Имя профиля: всё, что после последнего '='
        parts = content_str.split('=')
        name = parts[-1].strip() if len(parts) > 2 else "WARP"
        # Убираем непечатные символы из имени
        name = "".join(filter(lambda x: x.isupper() or x.isspace(), name)).strip()

        return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={local_address}&reserved={reserved}&mtu={mtu}#{name}"
    except Exception as e:
        return None

def main():
    results = []
    for url in SOURCE_URLS:
        print(f"Парсинг {url}")
        try:
            r = requests.get(url, timeout=10)
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

    if results:
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            f.write("\n".join(results))
        print(f"Готово! Сгенерировано: {len(results)}")
    else:
        # Если ссылок 0, создадим пустой файл, чтобы Git увидел изменения (если файла не было)
        open(OUTPUT_FILE, 'a').close()
        print("ВНИМАНИЕ: Ссылок не найдено.")

if __name__ == "__main__":
    main()
