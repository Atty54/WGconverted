import base64
import zlib
import msgpack
import requests

SOURCE_URLS = [
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt",
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/nekobox-wg.txt"
]
OUTPUT_FILE = "my_wg_sub.txt"

def decode_reserved(res_data):
    try:
        if isinstance(res_data, (bytes, bytearray)):
            return "-".join(map(str, list(res_data)))
        elif isinstance(res_data, str):
            # Если это строка (Base64), декодируем её в байты
            res_bytes = base64.b64decode(res_data)
            return "-".join(map(str, list(res_bytes)))
        return "0-0-0"
    except:
        return "0-0-0"

def parse_link(payload):
    try:
        # 1. Base64 коррекция
        payload = payload.replace('-', '+').replace('_', '/')
        payload += "=" * (-len(payload) % 4)
        decoded = base64.b64decode(payload)
        
        # 2. Zlib декомпрессия (78 da)
        if decoded[0] == 0x78:
            raw_data = zlib.decompress(decoded)
        else:
            raw_data = decoded

        # 3. MsgPack парсинг
        # Используем raw=False чтобы ключи-числа не превратились в байты
        data = msgpack.unpackb(raw_data, raw=False, strict_map_key=False)
        
        # Обработка словаря (Map)
        if isinstance(data, dict):
            name = data.get(1, "WARP")
            server = data.get(2)
            port = data.get(3)
            local_addrs = data.get(4, [])
            pk = data.get(5)
            pub = data.get(6)
            mtu = data.get(7, 1280)
            res = data.get(8, b"\x00\x00\x00")
            
            if server and pk:
                addr_str = ",".join(local_addrs) if isinstance(local_addrs, list) else str(local_addrs)
                return (f"wg://{server}:{port}?private_key={pk}&public_key={pub}"
                        f"&local_address={addr_str}&reserved={decode_reserved(res)}&mtu={mtu}#{name}")
    except:
        return None
    return None

def test_your_example():
    print("\n--- [ИНСПЕКЦИЯ]: ЭТАЛОННЫЙ ПРИМЕР ---")
    example_b64 = "eNoNzjsOgjAAANCqcekp3E1KW6DWJk6Gxh9iED8r0IIkfuIvgBurd2E38TYewRPoO8FrAgDy7KLR8RrvUfZ9twB4kR5FhCGMqGFSSBlmwuphLAjBgieqL6yQ2yLEcSgSKxJca2YQymvmYbN7VqXkOvAVT48qjtJisb9f_E0ebWeF5jb3w3xuWoM6Omy9YVcSWTiu7Ksym9KRbZDl6vYY4cl9fbLJjuaLJC1Pgwq0AXDd86fx70IIx52lE3Tk2HcgfFbVD6BkOHk"
    res = parse_link(example_b64)
    if res:
        print(f"РЕЗУЛЬТАТ ЭТАЛОНА: {res[:80]}...")
    else:
        print("ОШИБКА: Эталон не распарсился!")

def main():
    test_your_example()
    
    results = []
    for url in SOURCE_URLS:
        print(f"\n--- [ИНСПЕКЦИЯ]: ЗАГРУЗКА {url} ---")
        try:
            r = requests.get(url, timeout=10)
            lines = r.text.strip().splitlines()
            
            # Выводим первые 3 строки для контроля
            for i, line in enumerate(lines[:3]):
                print(f"Строка {i}: {line[:60]}...")
            
            print(f"Всего строк в файле: {len(lines)}")
            
            for line in lines:
                if '?' not in line: continue
                payload = line.split('?')
