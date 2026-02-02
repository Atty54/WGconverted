import base64
import zlib
import json
import requests

SOURCE_URL = "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/v2rayng-wg.txt"
OUTPUT_FILE = "my_wg_sub.txt"

def process():
    try:
        resp = requests.get(SOURCE_URL).text.strip()
        # Декодируем и разжимаем Raw Deflate
        compressed = base64.b64decode(resp)
        decompressed = zlib.decompress(compressed, -15)
        data = json.loads(decompressed)
        
        output_links = []
        for item in data:
            # Извлекаем параметры
            ep = f"{item.get('server')}:{item.get('server_port')}"
            pk = item.get('private_key')
            pub = item.get('server_pub')
            # Превращаем [105, 102, 188] в 105-102-188
            res = "-".join(map(str, item.get('reserved', [])))
            # Собираем адреса
            addr = ",".join(item.get('local_address', []))
            
            link = f"wg://{ep}?private_key={pk}&public_key={pub}&local_address={addr}&reserved={res}&mtu=1280#WARP_{ep}"
            output_links.append(link)
        
        with open(OUTPUT_FILE, "w") as f:
            f.write("\n".join(output_links))
            
        print(f"Успешно сконвертировано {len(output_links)} ссылок.")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    process()
