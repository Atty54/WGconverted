import base64
import zlib
import json
import requests
import urllib.parse

SOURCE_URL = "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt"
OUTPUT_FILE = "my_wg_sub.txt"

def decode_husi(husi_url):
    try:
        # Извлекаем часть после '?'
        if '?' not in husi_url: return None
        b64_part = husi_url.split('?')[1].strip()
        
        # Декодируем Base64 и разжимаем Zlib
        compressed = base64.urlsafe_b64decode(b64_part + '==')
        # Для husi/sing-box обычно используется стандартный zlib или raw inflate
        try:
            decompressed = zlib.decompress(compressed)
        except:
            decompressed = zlib.decompress(compressed, -15)
            
        data = json.loads(decompressed)
        
        # Извлекаем параметры для твоего формата wg://
        server = data.get('server')
        port = data.get('server_port')
        pk = data.get('private_key')
        pub = data.get('server_pub')
        
        # Reserved: из массива [105, 102, 188] в строку 105-102-188
        res_list = data.get('reserved', [])
        res = "-".join(map(str, res_list)) if res_list else "0-0-0"
        
        # Адреса
        addr_list = data.get('local_address', [])
        addr = ",".join(addr_list)
        
        # Собираем итоговую ссылку
        name = f"WARP_{server}"
        final_url = f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={addr}&reserved={res}&mtu=1280#{name}"
        return final_url
    except Exception as e:
        print(f"Ошибка при разборе ссылки: {e}")
        return None

def main():
    print(f"Читаю файл {SOURCE_URL}...")
    response = requests.get(SOURCE_URL)
    lines = response.text.splitlines()
    
    results = []
    for line in lines:
        if line.startswith('husi://'):
            link = decode_husi(line)
            if link:
                results.append(link)
    
    if results:
        with open(OUTPUT_FILE, "w") as f:
            f.write("\n".join(results))
        print(f"Готово! Сконвертировано ссылок: {len(results)}")
    else:
        print("Не найдено ссылок для конвертации.")

if __name__ == "__main__":
    main()
