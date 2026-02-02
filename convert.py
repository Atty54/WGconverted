import base64
import zlib
import json
import requests

SOURCE_URL = "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt"
OUTPUT_FILE = "my_wg_sub.txt"

def decode_husi(husi_url):
    try:
        if '?' not in husi_url: return None
        b64_part = husi_url.split('?')[1].strip()
        
        # Исправляем padding Base64 и меняем символы на стандартные
        b64_part = b64_part.replace('-', '+').replace('_', '/')
        compressed = base64.b64decode(b64_part + '==')
        
        # Метод перебора для Zlib (Deflate / Raw / Standard)
        decompressed = None
        for wbits in [-zlib.MAX_WBITS, zlib.MAX_WBITS, zlib.MAX_WBITS | 16]:
            try:
                decompressed = zlib.decompress(compressed, wbits)
                if decompressed: break
            except:
                continue
        
        if not decompressed:
            return None
            
        json_str = decompressed.decode('utf-8', errors='ignore')
        data = json.loads(json_str)
        
        # Мапинг полей Sing-box -> WG URI
        server = data.get('server')
        port = data.get('server_port')
        pk = data.get('private_key')
        pub = data.get('server_pub') or data.get('public_key')
        
        # Обработка Reserved
        res_val = data.get('reserved', [0,0,0])
        res = "-".join(map(str, res_val)) if isinstance(res_val, list) else str(res_val)
        
        # Обработка адресов
        addr_val = data.get('local_address', ["172.16.0.2/32"])
        addr = ",".join(addr_val) if isinstance(addr_val, list) else str(addr_val)
        
        if server and pk:
            # Формируем искомую ссылку
            return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={addr}&reserved={res}&mtu=1280#WARP_{server}"
            
    except Exception:
        return None
    return None

def main():
    print(f"Загрузка из {SOURCE_URL}...")
    try:
        r = requests.get(SOURCE_URL)
        r.raise_for_status()
        lines = r.text.splitlines()
        
        results = []
        for line in lines:
            line = line.strip()
            if line.startswith('husi://'):
                link = decode_husi(line)
                if link:
                    results.append(link)
        
        if results:
            with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
                f.write("\n".join(results))
            print(f"Успех! Сгенерировано {len(results)} ссылок.")
        else:
            print("Не удалось декодировать ни одной ссылки. Проверь формат источника.")
            
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()
