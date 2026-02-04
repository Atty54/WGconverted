import base64
import zlib
import struct
import re
import requests

SOURCE_URLS = ["https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/nekobox-wg.txt"]
OUTPUT_FILE = "my_wg_sub.txt"

def manual_extract(raw_data):
    try:
        content_str = raw_data.decode('ascii', errors='ignore')
        
        # 1. КЛЮЧИ
        keys = re.findall(r'[A-Za-z0-9+/]{43}=', content_str)
        if len(keys) < 2: return None
        pk, pub = keys[0], keys[1]
        
        # 2. ИМЯ (Якорь)
        name = "WARP"
        patterns = [r'I SET FIRE', r'TO THE RAIN', r'(?:OPS|D2O)\s*-\s*\d+']
        for p in patterns:
            m = re.search(p, content_str)
            if m:
                name = m.group(0)
                break
        
        name_idx = raw_data.find(name.encode())

        # 3. СЕРВЕР И ПОРТ (Поиск по структуре)
        # Ищем домен в начале
        srv_b = []
        for b in raw_data[4:40]:
            if b < 32: break
            srv_b.append(b)
        server = bytes(srv_b).decode('ascii', errors='ignore')
        if ".nscl.i" in server: server = server.replace(".i", ".ir")

        # ПОРТ: Ищем 2 байта, которые в сумме дают что-то похожее на 1002, 903 и т.д.
        # В MsgPack порт обычно идет после маркера 0xCD
        port = 0
        port_area = raw_data[4 + len(srv_b) : 4 + len(srv_b) + 10]
        for i in range(len(port_area)-1):
            val = struct.unpack('>H', port_area[i:i+2])[0]
            if 400 < val < 60000: # Диапазон реальных портов
                port = val
                break

        # 4. RESERVED (Декодируем 4 символа перед именем как Base64)
        try:
            # Ищем 4 символа перед байтом длины имени (name_idx - 5 : name_idx - 1)
            res_string = raw_data[name_idx-5:name_idx-1].decode('ascii')
            # Декодируем Base64 в байты
            res_bytes = base64.b64decode(res_string + "==") # Добавляем padding на всякий случай
            reserved = f"{res_bytes[0]}-{res_bytes[1]}-{res_bytes[2]}"
        except:
            # Если не Base64, оставляем как было (запасной вариант)
            res_area = raw_data[name_idx-4:name_idx-1]
            reserved = "-".join(map(str, list(res_area)))

        # 5. IP АДРЕСА
        # Вытаскиваем IPv6 по паттерну, игнорируя прилипшие символы
        v6_match = re.search(r'([0-9a-fA-F:]{15,})', content_str)
        local_address = "172.16.0.2/32"
        if v6_match:
            v6 = v6_match.group(1).strip(':')
            # Важно: отсекаем порт, если он приклеился к IPv6
            if v6.count(':') > 7: 
                v6 = ':'.join(v6.split(':')[:8])
            local_address += f",{v6}/128"

        # 6. MTU
        # Обычно это 1300 (05 14 в Big-Endian или 14 05 в Little)
        mtu = 1280
        mtu_search = raw_data[name_idx-10:name_idx-4]
        for i in range(len(mtu_search)-1):
            m = struct.unpack('>H', mtu_search[i:i+2])[0]
            if 1280 <= m <= 1500:
                mtu = m
                break

        return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={local_address}&reserved={reserved}&mtu={mtu}#{name}"
    except:
        return None

def main():
    try:
        r = requests.get(SOURCE_URLS[0], timeout=15)
        results = []
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
        
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            f.write("\n".join(results))
    except:
        pass

if __name__ == "__main__":
    main()
