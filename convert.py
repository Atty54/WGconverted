import base64
import zlib
import struct
import re
import requests

SOURCE_URLS = [
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt",
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/nekobox-wg.txt"
]

def get_string(data, start_offset):
    """Читает строку из байтов до первого нулевого байта."""
    end = data.find(b'\x00', start_offset)
    if end == -1:
        return data[start_offset:].decode('ascii', errors='ignore').strip()
    return data[start_offset:end].decode('ascii', errors='ignore').strip()

def manual_extract(raw_data):
    try:
        # 1. Server (начинается с 4-го байта, длина произвольная до \x00)
        server = get_string(raw_data, 4)
        
        # 2. Port (Offset 17-18, Little-endian)
        port = struct.unpack('<H', raw_data[17:19])[0]

        # 3. Ключи (Base64) - ищем паттерном по всему бинарнику
        content_str = raw_data.decode('ascii', errors='ignore')
        keys = re.findall(r'[A-Za-z0-9+/]{43}=', content_str)
        if len(keys) < 2: return None
        pk, pub = keys[0], keys[1]

        # 4. Local Addresses (ищем паттернами IPv4/32 и IPv6/128)
        # Это надежнее, чем офсеты, так как адреса могут меняться местами
        ipv4 = re.search(r'(\d{1,3}(?:\.\d{1,3}){3}/32)', content_str)
        ipv6 = re.search(r'([0-9a-fA-F:]+:[0-9a-fA-F:]+/[0-9]+)', content_str)
        
        addrs = []
        if ipv4: addrs.append(ipv4.group(1))
        if ipv6: addrs.append(ipv6.group(1))
        local_address = ",".join(addrs)

        # 5. Reserved (3 байта) 
        # Если по офсету 171 нули, ищем первый блок из 3-х ненулевых байт в зоне reserved
        res_chunk = raw_data[171:174]
        if list(res_chunk) == [0, 0, 0]:
            # Зона reserved обычно находится между ключами и именем
            potential = re.search(b'[^\x00]{3}', raw_data[160:190])
            if potential:
                res_chunk = potential.group()
        
        reserved = "-".join(map(str, list(res_chunk)))

        # 6. MTU (Offset 167-168)
        mtu = struct.unpack('<H', raw_data[167:169])[0]

        # 7. Name (находится в самом конце, после всех ключей)
        # Ищем последнюю строку из печатных символов длиной > 2
        names = re.findall(r'[A-Z\s]{3,}', content_str)
        name = names[-1].strip() if names else "WARP"

        return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={local_address}&reserved={reserved}&mtu={mtu}#{name}"
    except:
        return None

# Функция main остается прежней
