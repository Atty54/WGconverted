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
            res_bytes = base64.b64decode(res_data)
            return "-".join(map(str, list(res_bytes)))
        return "0-0-0"
    except:
        return "0-0-0"

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

        # 3. MsgPack
        data = msgpack.unpackb(raw_data, raw=False, strict_map_key=False)
        
        if isinstance(data, dict):
            name = data.get(1, "WARP")
            server = data.get(2)
            port = data.get(3)
            addrs = data.get(4, [])
            pk = data.get(5)
            pub = data.get(6)
            mtu = data.get(7, 1280)
            res = data.get(8, b"\x00\x00\x00")
            
            if server and pk:
                addr_str = ",".join(addrs) if isinstance(addrs, list) else str(addrs)
                return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={addr_str}&reserved={decode_reserved(res)}&mtu={mtu}#{name}"
    except:
        pass
    return None

def main():
    # Тест эталона
    example_b64 = "eNoNzjsOgjAAANCqcekp3E1KW6DWJk6Gxh9iED8r0IIkfuIvgBurd2E38TYewRPoO8FrAgDy7KLR8RrvUfZ9twB4kR5FhCGMqGFSSBlmwuphLAjBgieqL6yQ2yLEcSgSKxJca2YQymvmYbN7VqXkOvAVT48qjtJisb9f_E0ebWeF5jb3w3xuWoM6Omy9YVcSWTiu7Ksym9KRbZDl6vYY4cl9fbLJjuaLJC1Pgwq0AXDd86fx70IIx52lE3Tk2HcgfFbVD6BkOHk"
    test_res = parse_link(example_b64)
    print(f"--- [ТЕСТ ЭТАЛОНА]: {'УСПЕХ' if test_res else 'ПРОВАЛ'} ---")

    results = []
    for url in SOURCE_URLS:
        print(f"\n--- [ИНСПЕКЦИЯ]: {url} ---")
        try:
            r = requests.get(url, timeout=10)
            lines = r.text.strip().splitlines()
            
            # Логируем первые 2 строки для проверки
            for i, l in enumerate(lines[:2]):
                print(f"RAW {i}: {l[:60]}...")

            for line in lines:
                if '?' in line:
                    res = parse_link(line.split('?')[1])
                    if res:
                        results.append(res)
        except Exception as e:
            print(f"Ошибка при работе с URL: {e}")

    if results:
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            f.write("\n".join(results))
        print(f"\nФИНАЛ: Собрано {len(results)} ссылок.")
    else:
        print("\nФИНАЛ: Ссылок не найдено.")

if __name__ == "__main__":
    main()
