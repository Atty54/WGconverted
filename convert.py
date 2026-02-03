import base64
import zlib
import struct
import re
import requests

SOURCE_URLS = [
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt",
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/nekobox-wg.txt"
]

def manual_extract(raw_data):
    try:
        content_str = raw_data.decode('ascii', errors='ignore')
        
        # 1. SERVER (читаем с 4-го байта до нулевого терминатора)
        end_idx = raw_data.find(b'\x00', 4)
        server = raw_data[4:end_idx].decode('ascii', errors='ignore') if end_idx != -1 else ""
        if not server: return None

        # 2. PORT
        # В этом формате порт обычно идет через 1-2 байта после сервера
        # Мы ищем его как Little-endian uint16 сразу за нулевым байтом сервера
        port_offset = end_idx + 1
        # Пропускаем возможные типы полей (1 байт), если там не данные порта
        if raw_data[port_offset] < 20: port_offset += 1 
        port = struct.unpack('<H', raw_data[port_offset:port_offset+2])[0]

        # 3. KEYS
        keys = re.findall(r'[A-Za-z0-9+/]{43}=', content_str)
        if len(keys) < 2: return None
        pk, pub = keys[0], keys[1]

        # 4. LOCAL ADDRESSES
        ips = re.findall(r'(\d{1,3}(?:\.\d{1,3}){3}(?:/\d+)*|[0-9a-fA-F:]+:[0-9a-fA-F:]+(?:/\d+)*)', content_str)
        addrs = []
        for ip in ips:
            if '.' in ip and '/' not in ip: ip += "/32"
            if ':' in ip and '/' not in ip: ip += "/128"
            if ip not in addrs: addrs.append(ip)
        local_address = ",".join(addrs)

        # 5. ИСТИННЫЙ MTU (Поиск по паттерну)
        # MTU обычно находится ПЕРЕД Reserved или ПОСЛЕ ключей.
        # Мы ищем байт 0x05 (т.к. 1280-1500 это 0x05XX в Big-endian или XX05 в Little)
        mtu = 1280 # дефолт, если не найдем
        # Ищем 0x05 в зоне после ключей (где-то во второй половине конфига)
        mtu_search_zone = raw_data[120:180]
        idx_05 = mtu_search_zone.find(b'\x05')
        if idx_05 != -1:
            # Проверяем два варианта: 05 XX или XX 05
            val1 = struct.unpack('<H', mtu_search_zone[idx_05-1:idx_05+1])[0] # XX 05
            val2 = struct.unpack('>H', mtu_search_zone[idx_05:idx_05+2])[0]  # 05 XX
            
            if 1200 <= val1 <= 1500: mtu = val1
            elif 1200 <= val2 <= 1500: mtu = val2

        # 6. RESERVED (3 байта)
        # Ищем блок из 3-х ненулевых байт в самом конце, перед именем
        reserved = "0-0-0"
        potential_res = re.findall(b'[^\x00]{3}', raw_data[150:])
        if potential_res:
            # Берем тот блок, который не является частью ключа или MTU
            for block in reversed(potential_res):
                if len(block) == 3 and not any(b > 126 for b in block):
                    reserved = "-".join(map(str, list(block)))
                    break

        # 7. NAME
        names = re.findall(r'[A-Z\s]{3,}', content_str)
        name = names[-1].strip() if names else "WARP"

        return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={local_address}&reserved={reserved}&mtu={mtu}#{name}"
    except:
        return None
