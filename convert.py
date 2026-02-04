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
        # 1. СЕРВЕР: Читаем до первого нулевого байта или спецсимвола < 32
        server_bytes = []
        for b in raw_data[4:]:
            if b < 32: break
            server_bytes.append(b)
        server = bytes(server_bytes).decode('ascii', errors='ignore').strip()
        
        # Индекс, на котором закончился сервер
        end_server_idx = 4 + len(server_bytes)
        
        # Фикс домена .ir
        if server.endswith(".ncl.i") or server.endswith(".nscl.i"):
            server += "r"

        # 2. ПОРТ: Он идет сразу после байта-разделителя за сервером
        # В этом формате это обычно Big-Endian uint16
        port_offset = end_server_idx + 1
        port = struct.unpack('>H', raw_data[port_offset:port_offset+2])[0]
        
        # Если порт получился странный ( < 100), пробуем сместиться на 1 байт
        if port < 80:
            port = struct.unpack('>H', raw_data[port_offset+1:port_offset+3])[0]

        # 3. КЛЮЧИ
        content_str = raw_data.decode('ascii', errors='ignore')
        keys = re.findall(r'[A-Za-z0-9+/]{42,43}=', content_str)
        if len(keys) < 2: return None
        pk, pub = keys[0], keys[1]

        # 4. ИМЯ (в самом конце)
        # Ищем паттерн OPS - XXX
        name_match = re.search(r'OPS\s*-\s*\d+', content_str)
        name = name_match.group(0) if name_match else "WARP"

        # 5. RESERVED (3 байта ПЕРЕД именем)
        # Ищем индекс начала имени в байтах
        name_bytes = name.encode()
        name_idx = raw_data.find(name_bytes)
        # Reserved обычно за 4-5 байт до имени
        res_chunk = raw_data[name_idx-4:name_idx-1]
        if 0 in list(res_chunk): # Если опять нули, берем чуть левее
            res_chunk = raw_data[name_idx-5:name_idx-2]
        
        reserved = "-".join(map(str, list(res_chunk)))

        # 6. IP АДРЕСА
        # Ищем чистые IP без мусора в конце
        ipv4 = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', content_str)
        ipv6 = re.search(r'([0-9a-fA-F:]+:[0-9a-fA-F:]+)', content_str)
        
        addrs = []
        if ipv4: addrs.append(f"{ipv4.group(1)}/32")
        if ipv6:
            v6 = ipv6.group(1)
            if v6.endswith(':'): v6 = v6[:-1]
            addrs.append(f"{v6}/128")
        
        local_address = ",".join(addrs)

        # 7. MTU
        # В дампе мы видели 1280 и 5249 (что явно ошибка). 
        # MTU в этих конфигах обычно перед Reserved.
        mtu = 1280
        mtu_raw = struct.unpack('>H', raw_data[name_idx-7:name_idx-5])[0]
        if 1200 <= mtu_raw <= 1500:
            mtu = mtu_raw

        return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={local_address}&reserved={reserved}&mtu={mtu}#{name}"
    except:
        return None
