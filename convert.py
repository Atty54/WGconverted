import base64
import zlib
import json
import requests

SOURCE_URL = "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt"
OUTPUT_FILE = "my_wg_sub.txt"

def decode_singbox_link(url):
    try:
        if '?' not in url: return None
        # Отрезаем префикс (husi://wg? или exclave://wg?)
        b64_part = url.split('?')[1].strip()
        
        # 1. Корректный Base64 URL-Safe
        b64_part = b64_part.replace('-', '+').replace('_', '/')
        b64_part += "=" * (-len(b64_part) % 4)
        raw_data = base64.b64decode(b64_part)
        
        # 2. Распаковка GZIP (Флаг 16 + MAX_WBITS говорит zlib работать с Gzip)
        # Именно так Sing-box пакует свои бинарные конфиги
        decompressed = zlib.decompress(raw_data, zlib.MAX_WBITS | 16)
        
        # 3. Читаем JSON
        config = json.loads(decompressed.decode('utf-8'))
        
        # Вытаскиваем данные из структуры Sing-box
        # В этих конфигах часто 'server' и 'server_port' лежат в корне
        server = config.get('server')
        port = config.get('server_port')
        pk = config.get('private_key')
        pub = config.get('server_pub') or config.get('public_key')
        
        # Обработка Reserved (в Sing-box это массив [105, 102, 188])
        res_list = config.get('reserved', [0, 0, 0])
        res = "-".join(map(str, res_list)) if isinstance(res_list, list) else str(res_list)
        
        # Адреса
        addrs = ",".join(config.get('local_address', ["172.16.0.2/32"]))
        
        if server and pk:
            return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={addrs}&reserved={res}&mtu=1280#WARP_{server}"
            
    except Exception as e:
        # Если это не Gzip, пробуем как обычный Zlib (стандарт v2ray)
        try:
            raw_data = base64.b64decode(b64_part)
            decompressed = zlib.decompress(raw_data)
            config = json.loads(decompressed.decode('utf-8'))
            return f"wg://{config['server']}:{config['server_port']}?private_key={config['private_key']}&public_key={config.get('server_pub')}&local_address={','.join(config.get('local_address', []))}&reserved={'-'.join(map(str, config.get('reserved', [])))}&mtu=1280#WARP_ALT"
        except:
            return None

def main():
    print(f"Загрузка: {SOURCE_URL}")
    r = requests.get(SOURCE_URL)
    results = []
    for line in r.text.splitlines():
        if "://" in line:
            res = decode_singbox_link(line.strip())
            if res: results.append(res)
    
    if results:
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            f.write("\n".join(results))
        print(f"Победа! Собрано ссылок: {len(results)}")
    else:
        print("Китайская стена не пробита. Ссылки не декодировались.")

if __name__ == "__main__":
    main()
