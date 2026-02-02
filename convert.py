import base64
import zlib
import json
import requests
import msgpack

SOURCE_URL = "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt"
OUTPUT_FILE = "my_wg_sub.txt"

def universal_decode(payload):
    # 1. Готовим байты из Base64
    try:
        payload = payload.replace('-', '+').replace('_', '/')
        payload += "=" * (-len(payload) % 4)
        raw_bytes = base64.b64decode(payload)
    except:
        return None

    # 2. Пробуем разжать (Raw Deflate -15 — самый частый в Sing-box)
    decompressed = None
    try:
        decompressed = zlib.decompress(raw_bytes, -15)
    except:
        try:
            decompressed = zlib.decompress(raw_bytes) # Пробуем обычный Zlib
        except:
            decompressed = raw_bytes # Возможно, не сжато

    # 3. Пробуем парсить как JSON
    try:
        data = json.loads(decompressed.decode('utf-8'))
        return data
    except:
        # 4. Если не JSON, пробуем MessagePack (Husi часто юзает его)
        try:
            data = msgpack.unpackb(decompressed, raw=False)
            return data
        except:
            return None

def main():
    print(f"Загрузка: {SOURCE_URL}")
    r = requests.get(SOURCE_URL)
    results = []
    
    for line in r.text.splitlines():
        line = line.strip()
        if '?' not in line: continue
        
        # Вытаскиваем всё, что после '?' или после '=' (если там husi://wg?data=...)
        parts = line.split('?')
        payload = parts[1]
        if payload.startswith('data='):
            payload = payload[5:]
            
        data = universal_decode(payload)
        
        if data and isinstance(data, dict):
            # Извлекаем ключи (учитываем, что в MsgPack они могут чуть отличаться)
            server = data.get('server') or data.get('address')
            port = data.get('server_port') or data.get('port')
            pk = data.get('private_key')
            pub = data.get('server_pub') or data.get('public_key')
            
            if server and pk:
                res_list = data.get('reserved', [0, 0, 0])
                res = "-".join(map(str, res_list)) if isinstance(res_list, list) else str(res_list)
                
                addr_list = data.get('local_address', ["172.16.0.2/32"])
                addr = ",".join(addr_list) if isinstance(addr_list, list) else str(addr_list)
                
                link = f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={addr}&reserved={res}&mtu=1280#WARP_{server}"
                results.append(link)

    if results:
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            f.write("\n".join(results))
        print(f"ПОБЕДА! Собрано ссылок: {len(results)}")
    else:
        print("Стена всё ещё стоит. Проверь логи, если есть ошибки.")

if __name__ == "__main__":
    main()
