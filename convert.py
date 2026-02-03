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
        # 1. Server (Берем с запасом до 32 байт и режем по нулевому байту)
        server_chunk = raw_data[4:32].split(b'\x00')[0]
        server_raw = server_chunk.decode('ascii', errors='ignore').strip()
        
        # Фикс для доменов .ir (если вдруг обрезалось или считалось неверно)
        if server_raw.endswith(".ncl.i"): server_raw += "r"
        if server_raw.endswith(".nscl.i"): server_raw += "r"
        
        # 2. Port (Остается на 17-18, но проверим, не сдвинулся ли он)
        # Если порт подозрительно маленький (0, 1, 3), пробуем взять его чуть дальше
        port = struct.unpack('<H', raw_data[17:19])[0]
        if port < 10 and len(raw_data) > 25:
             # В некоторых версиях порт идет сразу за длинным именем сервера
             potential_port = struct.unpack('<H', raw_data[19:21])[0]
             if potential_port > 10: port = potential_port

        # 3. Подготовка контента для регулярки
        content = raw_data.decode('ascii', errors='ignore')
        
        # 4. Ключи
        keys = re.findall(r'[A-Za-z0-9+/]{42,43}=', content)
        if len(keys) < 2: return None
        pk, pub = keys[0], keys[1]

        # 5. IPv4 и IPv6 (Улучшенные регулярки)
        # Ищем 4 группы цифр. Если маски /32 нет в дампе, добавляем её.
        ipv4_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', content)
        ipv6_match = re.search(r'([0-9a-fA-F:]+:[0-9a-fA-F:]+(?:/[0-9]+)?)', content)
        
        addrs = []
        if ipv4_match:
            ip = ipv4_match.group(1)
            addrs.append(f"{ip}/32")
        if ipv6_match:
            ip = ipv6_match.group(1)
            if '/' not in ip: ip += "/128"
            addrs.append(ip)
            
        local_address = ",".join(addrs) if addrs else "172.16.0.2/32,2606:4700:110:8fd9:4a85:a0ca:f4b:8ee6/128"

        # 6. MTU (Offset 167-168)
        mtu = 1280
        if len(raw_data) > 168:
            potential_mtu = struct.unpack('<H', raw_data[167:169])[0]
            # Валидация: MTU должен быть в разумных пределах
            if 1000 < potential_mtu < 1600:
                mtu = potential_mtu

        # 7. Reserved (Offset 171-173) + Фикс нулей
        res_bytes = raw_data[171:174]
        if list(res_bytes) == [0, 0, 0] or res_bytes[0] == 0:
            # Если по офсету нули, ищем первый блок из 3-х ненулевых байт в зоне 160-185
            search_zone = raw_data[160:190]
            for i in range(len(search_zone)-3):
                chunk = search_zone[i:i+3]
                if 0 not in list(chunk) and all(32 <= b <= 126 for b in chunk):
                    res_bytes = chunk
                    break
        
        reserved = "-".join(map(str, list(res_bytes)))

        # 8. Имя профиля
        name_match = re.findall(r'[A-Z\s]{3,}', content)
        name = name_match[-1].strip() if name_match else "WARP"

        return f"wg://{server_raw}:{port}?private_key={pk}&public_key={pub}&local_address={local_address}&reserved={reserved}&mtu={mtu}#{name}"
    except Exception:
        return None

# Функция main() остается без изменений как в твоем рабочем варианте
