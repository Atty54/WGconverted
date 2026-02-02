import base64
import zlib
import json
import requests

SOURCE_URL = "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt"
OUTPUT_FILE = "my_wg_sub.txt"

def decode_husi(husi_url):
    try:
        if '?' not in husi_url: return None
        # Берем всё, что после знака вопроса
        b64_part = husi_url.split('?')[1].strip()
        
        # Декодируем base64 (используем urlsafe для надежности)
        compressed = base64.urlsafe_b64decode(b64_part + '==')
        
        # Разжимаем (пробуем raw inflate -15, так как это стандарт sing-box)
        try:
            decompressed = zlib.decompress(compressed, -15)
        except zlib.error:
            decompressed = zlib.decompress(compressed)
            
        # ПРИНУДИТЕЛЬНО декодируем в utf-8, игнорируя ошибки кодировки
        json_str = decompressed.decode('utf-8', errors='ignore')
        data = json.loads(json_str)
        
        # Извлекаем данные
        server = data.get('server')
        port = data.get('server_port')
        pk = data.get('private_key')
        pub = data.get('server_pub') or data.get('public_key')
        
        res_list = data.get('reserved', [])
        res = "-".join(map(str, res_list)) if isinstance(res_list, list) else str(res_list)
        
        addr_list = data.get('local_address', [])
        addr = ",".join(addr_list) if isinstance(addr_list, list) else str(addr_list)
        
        if server and pk:
            return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={addr}&reserved={res}&mtu=1280#WARP_{server}"
        
        return None
    except Exception as e:
        # Теперь мы увидим реальную ошибку, если она останется
        print(f"Ошибка парсинга: {e}")
        return None

def main():
    print(f"Загрузка: {SOURCE_URL}")
    try:
        response = requests.get(SOURCE_URL)
        response.encoding = 'utf-8'
        lines = response.text.splitlines()
        
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
            print(f"Успех! Сгенерировано ссылок: {len(results)}")
        else:
            print("Список пуст. Проверь логи ошибок выше.")
            
    except Exception as e:
        print(f"Ошибка загрузки файла: {e}")

if __name__ == "__main__":
    main()
