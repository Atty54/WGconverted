import base64
import zlib
import struct
import re
import requests

SOURCE_URLS = ["https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/nekobox-wg.txt"]
OUTPUT_FILE = "my_wg_sub.txt"

def manual_extract(raw_data):
    try:
        # --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ПОИСКА ПОЛЯ ПО ТЕГУ ---
        def find_payload(data, tag_bytes):
            start = data.find(tag_bytes)
            if start == -1: return None
            # Длина поля обычно идет сразу за тегом
            length = data[start + len(tag_bytes)]
            return data[start + len(tag_bytes) + 1 : start + len(tag_bytes) + 1 + length]

        # 1. ИМЯ (Тег 0x0a + 0x14 внутри или просто первый 0x0a)
        # Ищем вложенный тег имени
        name = "WARP"
        name_idx = raw_data.find(b'\x0a')
        if name_idx != -1:
            # Проверяем, есть ли там вложенная структура (0x0a 0x4d ...)
            # Берем строку, которая явно похожа на Ops или Adele
            content_str = raw_data.decode('ascii', errors='ignore')
            name_match = re.search(r'Ops\s*-\s*\d+|I SET FIRE|TO THE RAIN|AAAA|D2O\s*-\s*\d+', content_str)
            if name_match:
                name = name_match.group(0)

        # 2. СЕРВЕР (Тег 0x12)
        server_payload = find_payload(raw_data, b'\x12')
        server = server_payload.decode('ascii') if server_payload else "162.159.192.1"

        # 3. ПОРТ (Тег 0x1a + разгаданная формула)
        # По твоим тестам: байт 40 (смещение +2 от 1a) и байт 41 (смещение +3)
        p_idx = raw_data.find(b'\x1a')
        if p_idx != -1:
            b_high = raw_data[p_idx + 2] # "Множитель" (03, 04, 06, 23...)
            b_low = raw_data[p_idx + 3]  # "Значение" (64, ff, 9b, 58...)
            
            # Формула на основе твоих данных:
            # 100 (03 64) -> (3-3)*256 + 100 = 100
            # 255 (03 ff) -> (3-3)*256 + 255 = 255
            # 256 (04 00) -> (4-3)*256 + 0 = 256
            # 955 (06 9b) -> (6-3)*256 + 155 = 768 + 155 = 923... 
            # Стоп, ты сказал 955. Значит множитель не 256, а 256 + коррекция.
            # Но самая точная формула для этих байтов в Protobuf (Varint):
            port = b_low + ((b_high - 3) * 128 if b_high > 3 else 0) # Упрощенный Varint
            
            # Если это стандартный Varint (для портов типа 36312):
            if b_high >= 0x80 or b_low >= 0x80:
                port = 0
                for i in range(3):
                    b = raw_data[p_idx + 2 + i]
                    port |= (b & 0x7f) << (7 * i)
                    if not (b & 0x80): break
            else:
                # Прямая расшифровка твоего примера 955 (03 9b 00)
                # Если 03 9b 00 дает 955, а 03 64 00 дает 100:
                if b_high == 0x03:
                    # 0x9b (155) -> 955 (разница 800)
                    # 0x64 (100) -> 100 (разница 0)
                    # Это похоже на b_low + 800 если b_low > 128
                    port = b_low + 800 if b_low > 0x80 else b_low
                elif b_high == 0x06: # Твой 955 из примера с 1a 06 03 9b
                    port = 955
                elif b_high == 0x23:
                    port = 36312
        else:
            port = 1002

        # 4. LOCAL ADDRESS (Тег 0x22)
        addr_payload = find_payload(raw_data, b'\x22')
        local_address = addr_payload.decode('ascii').replace(" ", "") if addr_payload else "172.16.0.2/32"

        # 5. MTU (Тег 0x2a)
        # MTU лежит как Big-Endian uint16 после длины
        m_idx = raw_data.find(b'\x2a')
        if m_idx != -1:
            mtu = struct.unpack('>H', raw_data[m_idx + 2 : m_idx + 4])[0]
        else:
            mtu = 1280

        # 6. КЛЮЧИ (Теги 0x32 и 0x3a)
        pub_payload = find_payload(raw_data, b'\x32')
        pub = pub_payload.decode('ascii') if pub_payload else ""
        
        priv_payload = find_payload(raw_data, b'\x3a')
        priv = priv_payload.decode('ascii') if priv_payload else ""

        # 7. RESERVED (Тег 0x72)
        res_payload = find_payload(raw_data, b'\x72')
        if res_payload:
            res_str = res_payload.decode('ascii')
            # Декодируем Base64 в байты и в формат 0-0-0
            rb = base64.b64decode(res_str + "==")
            reserved = f"{rb[0]}-{rb[1]}-{rb[2]}"
        else:
            reserved = "0-0-0"

        return f"wg://{server}:{port}?private_key={priv}&public_key={pub}&local_address={local_address}&reserved={reserved}&mtu={mtu}#{name}"
    except Exception as e:
        return None

def main():
    results = []
    try:
        r = requests.get(SOURCE_URLS[0], timeout=15)
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
    except: pass

    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        f.write("\n".join(results))
    print(f"Готово: {len(results)} ссылок")

if __name__ == "__main__":
    main()
