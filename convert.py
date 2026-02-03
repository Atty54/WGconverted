import base64
import zlib
import msgpack
import requests

SOURCE_URLS = [
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt",
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/nekobox-wg.txt"
]

def parse_link(payload):
    try:
        # 1. Base64
        payload = payload.replace('-', '+').replace('_', '/')
        payload += "=" * (-len(payload) % 4)
        decoded = base64.b64decode(payload)
        
        # 2. Zlib
        if len(decoded) > 0 and decoded[0] == 0x78:
            raw_data = zlib.decompress(decoded)
        else:
            raw_data = decoded

        # 3. MsgPack - пробуем raw=True, чтобы не падать на кодировках
        # Это вернет ключи и значения как bytes, которые мы потом декодируем
        data = msgpack.unpackb(raw_data, raw=True, strict_map_key=False)
        
        # Функция-помощник для безопасного извлечения данных из байтовых ключей
        def get_val(idx):
            # Проверяем и числовой ключ, и байтовый (так как raw=True)
            val = data.get(idx) or data.get(str(idx).encode())
            if isinstance(val, bytes):
                try: return val.decode('utf-8')
                except: return val
            return val

        # Извлекаем по ID (теперь ключи в словаре - это байты b'\x01', b'\x02' и т.д.)
        name = get_val(1) or "WARP"
        server = get_val(2)
        port = get_val(3)
        addrs = get_val(4) or []
        pk = get_val(5)
        pub = get_val(6)
        mtu = get_val(7) or 1280
        res_raw = get_val(8) or b"\x00\x00\x00"

        if server and pk:
            # Обработка адресов (они могут быть списком байтов)
            if isinstance(addrs, list):
                clean_addrs = [a.decode() if isinstance(a, bytes) else str(a) for a in addrs]
                addr_str = ",".join(clean_addrs)
            else:
                addr_str = addrs.decode() if isinstance(addrs, bytes) else str(addrs)

            # Reserved в формат 0-0-0
            res_bytes = res_raw if isinstance(res_raw, bytes) else base64.b64decode(res_raw)
            reserved = "-".join(map(str, list(res_bytes)))

            return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={addr_str}&reserved={reserved}&mtu={mtu}#{name}"
    except Exception as e:
        # Если это тест эталона, мы увидим ошибку в консоли
        return f"ERROR:{e}"
    return None

def main():
    # Твой пример
    example = "eNoNzjsOgjAAANCqcekp3E1KW6DWJk6Gxh9iED8r0IIkfuIvgBurd2E38TYewRPoO8FrAgDy7KLR8RrvUfZ9twB4kR5FhCGMqGFSSBlmwuphLAjBgieqL6yQ2yLEcSgSKxJca2YQymvmYbN7VqXkOvAVT48qjtJisb9f_E0ebWeF5jb3w3xuWoM6Omy9YVcSWTiu7Ksym9KRbZDl6vYY4cl9fbLJjuaLJC1Pgwq0AXDd86fx70IIx52lE3Tk2HcgfFbVD6BkOHk"
    test_res = parse_link(example)
    print(f"--- РЕЗУЛЬТАТ ТЕСТА: {test_res} ---")

    if "ERROR" in str(test_res):
        return # Останавливаемся, если даже эталон не прошел

    results = []
    for url in SOURCE_URLS:
        r = requests.get(url)
        for line in r.text.splitlines():
            if '?' in line:
                link = parse_link(line.split('?')[1])
                if link and "ERROR" not in link:
                    results.append(link)

    with open("my_wg_sub.txt", "w", encoding='utf-8') as f:
        f.write("\n".join(results))
    print(f"ФИНАЛ: Собрано {len(results)}")

if __name__ == "__main__":
    main()
