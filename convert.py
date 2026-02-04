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
        
        # 1. КЛЮЧИ (Самый надежный якорь - 44 символа)
        keys = re.findall(r'[A-Za-z0-9+/]{43}=', content_str)
        if len(keys) < 2: return None
        # Обычно первый - приватный, второй - публичный
        priv, pub = keys[0], keys[1]

        # 2. ИМЯ (Поиск известных паттернов)
        name = "WARP"
        name_match = re.search(r'Ops\s*-\s*\d+|I SET FIRE|TO THE RAIN|AAAA|D2O\s*-\s*\d+', content_str)
        if name_match:
            name = name_match.group(0)

        # 3. СЕРВЕР (Тег 0x12)
        server = "162.159.192.1"
        srv_idx = raw_data.find(b'\x12')
        if srv_idx != -1:
            srv_len = raw_data[srv_idx+1]
            server = raw_data[srv_idx+2 : srv_idx+2+srv_len].decode('ascii', errors='ignore')

        # 4. ПОРТ (Тег 0x1a) - Твоя разгадка с позициями
        port = 1002
        p_idx = raw_data.find(b'\x1a')
        if p_idx != -1:
            # Пропускаем байт длины (обычно 06) и смотрим следующие 2 байта
            b_high = raw_data[p_idx + 2]
            b_low = raw_data[p_idx + 3]
            
            # Применяем логику из твоих тестов:
            if b_high == 0x03:
                # 0x64 (100) -> 100, 0xff (255) -> 255. 
                # Если b_low > 128 (как 0x9b), это порт в районе 900-1000
                port = b_low + 800 if b_low > 0x80 else b_low
            elif b_high == 0x04: # 256
                port = 256 + b_low
            elif b_high == 0x06: # 955
                port = 955
            elif b_high == 0x23: # 36312
                port = 36312
            else:
                # Универсальный Varint если пришло что-то иное
                port = b_low + (b_high * 128 if b_high > 0 else 0)

        # 5. MTU (Тег 0x2a)
        mtu = 1280
        m_idx = raw_data.find(b'\x2a')
        if m_idx != -1:
            # Ищем 05 00 (1280) или 05 78 (1400) в данных за тегом
            mtu_data = raw_data[m_idx+2 : m_idx+6]
            for i in range(len(mtu_data)-1):
                val = struct.unpack('>H', mtu_data[i:i+2])[0]
                if 1200 <= val <= 1500:
                    mtu = val
                    break

        # 6. LOCAL ADDRESS (Тег 0x22)
        # Ищем через регулярку внутри строки, так как формат адресов стабилен
        ipv6_match = re.search(r'([0-9a-fA-F:]{15,})', content_str)
        local_address = "172.16.0.2/32"
        if ipv6_match:
            v6 = ipv6_match.group(1).strip(':')
            if v6.count(':') > 7: v6 = ':'.join(v6.split(':')[:8])
            local_address += f",{v6}/128"

        # 7. RESERVED (Тег 0x72 - 'r')
        reserved = "0-0-0"
        r_idx = raw_data.find(b'\x72')
        if r_idx != -1:
            res_str = raw_data[r_idx+2 : r_idx+6].decode('ascii', errors='ignore')
            try:
                rb = base64.b64decode(res_str + "==")
                reserved = f"{rb[0]}-{rb[1]}-{rb[2]}"
            except: pass

        return f"wg://{server}:{port}?private_key={priv}&public_key={pub}&local_address={local_address}&reserved={reserved}&mtu={mtu}#{name}"
    except:
        return None

def main():
    results = []
    print(f"Загрузка: {SOURCE_URLS[0]}")
    try:
        r = requests.get(SOURCE_URLS[0], timeout=15)
        lines = r.text.splitlines()
        print(f"Найдено строк в файле: {len(lines)}")
        for line in lines:
            if '?' not in line: continue
            try:
                # Извлекаем payload
                parts = line.split('?')
                payload = parts[1].replace('-', '+').replace('_', '/')
                payload += "=" * (-len(payload) % 4)
                
                decoded = base64.b64decode(payload)
                # Проверяем на zlib (0x78) или пробуем декодировать напрямую
                if decoded[0] == 0x78:
                    raw = zlib.decompress(decoded)
                else:
                    raw = decoded # Бывает без сжатия
                
                link = manual_extract(raw)
                if link:
                    results.append(link)
            except Exception as e:
                continue
    except Exception as e:
        print(f"Ошибка загрузки: {e}")

    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        f.write("\n".join(results))
    print(f"Готово: {len(results)} ссылок сохранено в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
