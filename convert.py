import base64
import zlib
import json
import requests

SOURCE_URL = "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt"
OUTPUT_FILE = "my_wg_sub.txt"

def decode_husi(husi_url):
    try:
        if '?' not in husi_url: return None
        data_part = husi_url.split('?')[1].strip()
        
        # 1. Исправляем URL-safe Base64
        # Заменяем - на + и _ на /
        data_part = data_part.replace('-', '+').replace('_', '/')
        
        # 2. Добавляем недостающий padding (равно в конце)
        missing_padding = len(data_part) % 4
        if missing_padding:
            data_part += '=' * (4 - missing_padding)
        
        # 3. Декодируем в байты
        compressed = base64.b64decode(data_part)
        
        # 4. Пробуем декомпрессию (Raw Deflate -15 самый вероятный)
        decompressed = None
        for wbits in [-15, 15, 31]:
            try:
                decompressed = zlib.decompress(compressed, wbits)
                if decompressed: break
            except:
                continue
        
        if not decompressed: return None
            
        # 5. Декодируем в строку и парсим JSON
        decoded_text = decompressed.decode('utf-8', errors='ignore')
        # Отладочный принт (увидишь в логах гитхаба)
        print(f"DEBUG: Начало данных: {decoded_text[:50]}")
        
        data = json.loads(decoded_text)
        
        # Поля Sing-box
        server = data.get('server')
        port = data.get('server_port')
        pk = data.get('private_key')
        pub = data.get('server_pub') or data.get('public_key')
        
        res_list = data.get('reserved', [0, 0, 0])
        res = "-".join(map(str, res_list)) if isinstance(res_list, list) else str(res_list)
        
        addr_list = data.get('local_address', ["172.16.0.2/32"])
        addr = ",".join(addr_list) if isinstance(addr_list, list) else str(addr_list)
        
        if server and pk:
            return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={addr}&reserved={res}&mtu=1280#WARP_{server}"
            
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        return None
    return None

def main():
    print(f"Загрузка: {SOURCE_URL}")
    r = requests.get(SOURCE_URL)
    lines = r.text.splitlines()
    
    results = []
    for line in lines:
        if line.strip().startswith('husi://'):
            res = decode_husi(line.strip())
            if res: results.append(res)
    
    if results:
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            f.write("\n".join(results))
        print(f"Успех! Собрано {len(results)} ссылок.")
    else:
        print("FAIL: Ссылки не найдены или не декодированы.")

if __name__ == "__main__":
    main()
