import base64
import zlib
import json
import requests
import re

SOURCE_URL = "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt"
OUTPUT_FILE = "my_wg_sub.txt"

def decode_husi(url):
    try:
        if '?' not in url: return None
        data_part = url.split('?')[1].strip()
        
        # 1. Твой метод декодирования
        data_part += "=" * (-len(data_part) % 4)
        raw = base64.b64decode(data_part)
        # Стандартный decompress (как в твоем примере)
        decoded_text = zlib.decompress(raw).decode("utf-8")
        
        # 2. Парсим JSON
        data = json.loads(decoded_text)
        
        # 3. Извлекаем данные
        server = data.get('server')
        port = data.get('server_port')
        pk = data.get('private_key')
        pub = data.get('server_pub') or data.get('public_key')
        
        # Reserved: из [1, 2, 3] в "1-2-3"
        res_list = data.get('reserved', [0, 0, 0])
        res = "-".join(map(str, res_list))
        
        # Адреса
        addrs = ",".join(data.get('local_address', []))
        
        if server and pk:
            return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={addrs}&reserved={res}&mtu=1280#WARP_{server}"
            
    except Exception as e:
        return None
    return None

def main():
    print(f"Загрузка {SOURCE_URL}...")
    try:
        r = requests.get(SOURCE_URL)
        r.raise_for_status()
        
        results = []
        for line in r.text.splitlines():
            line = line.strip()
            # Обрабатываем и husi, и exclave одним махом
            if "://" in line:
                link = decode_husi(line)
                if link:
                    results.append(link)
        
        if results:
            with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
                f.write("\n".join(results))
            print(f"Успех! Сгенерировано {len(results)} ссылок.")
        else:
            print("Не удалось декодировать ссылки.")
            
    except Exception as e:
        print(f"Ошибка загрузки: {e}")

if __name__ == "__main__":
    main()
