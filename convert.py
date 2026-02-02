import base64
import zlib
import json
import requests

# Пробуем v2rayng-wg, так как он самый полный
SOURCE_URL = "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/v2rayng-wg.txt"
OUTPUT_FILE = "my_wg_sub.txt"

def process():
    try:
        print(f"Загрузка данных из {SOURCE_URL}...")
        resp = requests.get(SOURCE_URL).text.strip()
        
        # Декодируем Base64
        compressed = base64.b64decode(resp)
        
        # Разжимаем (пробуем Raw Deflate, если нет - обычный Zlib)
        try:
            decompressed = zlib.decompress(compressed, -15)
        except:
            decompressed = zlib.decompress(compressed)
            
        data = json.loads(decompressed)
        print(f"Найдено объектов в JSON: {len(data)}")
        
        output_links = []
        for i, item in enumerate(data):
            # Извлекаем данные с учетом разных возможных имен ключей
            server = item.get('server') or item.get('address')
            port = item.get('server_port') or item.get('port')
            
            # Приватный ключ
            pk = item.get('private_key')
            
            # Публичный ключ (бывает public_key или server_pub)
            pub = item.get('server_pub') or item.get('public_key')
            
            # Reserved (может быть массивом [1,2,3] или строкой)
            reserved_raw = item.get('reserved', [0, 0, 0])
            if isinstance(reserved_raw, list):
                res = "-".join(map(str, reserved_raw))
            else:
                res = str(reserved_raw)
                
            # Local Address
            addr_list = item.get('local_address') or ["172.16.0.2/32"]
            addr = ",".join(addr_list) if isinstance(addr_list, list) else addr_list
            
            if server and pk and pub:
                link = f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={addr}&reserved={res}&mtu=1280#WARP_{i}"
                output_links.append(link)
        
        if not output_links:
            print("ВНИМАНИЕ: Ссылки не сформированы. Проверь структуру JSON.")
        else:
            with open(OUTPUT_FILE, "w") as f:
                f.write("\n".join(output_links))
            print(f"Успешно сохранено ссылок: {len(output_links)}")

    except Exception as e:
        print(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    process()
