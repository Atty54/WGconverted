import base64
import zlib
import msgpack
import requests

SOURCE_URL = "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt"
OUTPUT_FILE = "my_wg_sub.txt"

def decode_reserved(res_data):
    """Превращает байты или base64-строку reserved в формат 'число-число-число'"""
    try:
        if isinstance(res_data, str):
            res_bytes = base64.b64decode(res_data)
        else:
            res_bytes = res_data
        return "-".join(map(str, list(res_bytes)))
    except:
        return "0-0-0"

def parse_singbox_binary(raw_bytes):
    try:
        # Декодируем MsgPack. 
        # Sing-box использует карты с числовыми ключами.
        data = msgpack.unpackb(raw_bytes, raw=False, strict_map_key=False)
        
        # Карта полей Sing-box (опытным путем из NekoBox):
        name = data.get(1, "WARP")
        server = data.get(2)
        port = data.get(3)
        local_addrs = data.get(4, [])
        pk = data.get(5)
        pub = data.get(6)
        mtu = data.get(7, 1280)
        reserved_raw = data.get(8, b"\x00\x00\x00")
        
        if not server or not pk:
            return None

        reserved = decode_reserved(reserved_raw)
        addr_str = ",".join(local_addrs) if isinstance(local_addrs, list) else str(local_addrs)
        
        # Собираем полную ссылку со ВСЕМИ параметрами
        link = (f"wg://{server}:{port}?private_key={pk}&public_key={pub}"
                f"&local_address={addr_str}&reserved={reserved}&mtu={mtu}#{name}")
        return link
    except Exception as e:
        return None

def main():
    print(f"Загрузка: {SOURCE_URL}")
    r = requests.get(SOURCE_URL)
    results = []
    
    for line in r.text.splitlines():
        line = line.strip()
        if '?' not in line: continue
        
        try:
            # Чистим Base64
            payload = line.split('?')[1].replace('-', '+').replace('_', '/')
            payload += "=" * (-len(payload) % 4)
            decoded = base64.b64decode(payload)
            
            # Разжимаем Zlib (сигнатура 78)
            if decoded[0] == 0x78:
                raw_data = zlib.decompress(decoded)
                res = parse_singbox_binary(raw_data)
                if res:
                    results.append(res)
        except:
            continue

    if results:
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            f.write("\n".join(results))
        print(f"ПОБЕДА! Собрано {len(results)} полных конфигов.")
        print(f"Пример первого: {results[0][:100]}...")
    else:
        print("Данные не удалось распарсить. Возможно, изменились ID полей.")

if __name__ == "__main__":
    main()
