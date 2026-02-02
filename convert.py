import base64
import zlib
import json
import msgpack
import requests

SOURCE_URL = "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt"
OUTPUT_FILE = "my_wg_sub.txt"

def sing_box_parse(url):
    try:
        # Извлекаем payload
        payload = url.split('?')[1].strip()
        if payload.startswith('data='): payload = payload[5:]
        
        # 1. Декодируем Base64
        payload = payload.replace('-', '+').replace('_', '/')
        payload += "=" * (-len(payload) % 4)
        data = base64.b64decode(payload)
        
        # 2. Проверка на Zlib (Sing-box/Husi способ)
        # Если первые байты 0x78 0x9c или 0x78 0x01 — это Zlib
        if len(data) > 2 and data[0] == 0x78:
            try:
                data = zlib.decompress(data)
            except:
                pass # Если не вышло, пробуем сырым

        # 3. Определение формата: MsgPack или JSON
        decoded_obj = None
        first_byte = data[0]

        # Маркеры MessagePack для Map (0x80-0x8f, 0xde, 0xdf)
        if (0x80 <= first_byte <= 0x8f) or first_byte == 0xde or first_byte == 0xdf:
            decoded_obj = msgpack.unpackb(data, raw=False)
        # Маркер JSON
        elif first_byte == 0x7b: # Символ '{'
            decoded_obj = json.loads(data.decode('utf-8', errors='ignore'))
        
        if not decoded_obj: return None

        # 4. Сборка ссылки по стандартам WireGuard
        server = decoded_obj.get('server')
        port = decoded_obj.get('server_port')
        pk = decoded_obj.get('private_key')
        pub = decoded_obj.get('server_pub') or decoded_obj.get('public_key', '')
        
        # Обработка Reserved (в бинарном виде это массив байт)
        res_raw = decoded_obj.get('reserved', [0, 0, 0])
        res = "-".join(map(str, res_raw)) if isinstance(res_raw, list) else str(res_raw)
        
        # Локальные адреса
        addr_raw = decoded_obj.get('local_address', ["172.16.0.2/32"])
        addr = ",".join(addr_raw) if isinstance(addr_raw, list) else str(addr_raw)
        
        if server and pk:
            return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={addr}&reserved={res}&mtu=1280#WARP_{server}"

    except Exception as e:
        return None

def main():
    print(f"Загрузка: {SOURCE_URL}")
    r = requests.get(SOURCE_URL)
    results = []
    for line in r.text.splitlines():
        if "://" in line:
            link = sing_box_parse(line.strip())
            if link: results.append(link)
    
    if results:
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            f.write("\n".join(results))
        print(f"Успех! Сгенерировано {len(results)} ссылок.")
    else:
        print("Ошибка: Парсер Sing-box не нашел валидных данных.")

if __name__ == "__main__":
    main()
