import base64
import zlib
import json
import requests

SOURCE_URL = "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt"
OUTPUT_FILE = "my_wg_sub.txt"

def decode_husi(url):
    try:
        if '?' not in url: return None
        # Вырезаем часть после знака вопроса
        data_part = url.split('?')[1].strip()
        
        # Используем urlsafe_b64decode с добавлением padding, как в твоем примере
        # Это корректно обработает и '-' и '_'
        missing_padding = len(data_part) % 4
        if missing_padding:
            data_part += '=' * (4 - missing_padding)
            
        raw_data = base64.urlsafe_b64decode(data_part)
        
        # Разжимаем стандартным zlib (как в твоем тесте)
        decompressed = zlib.decompress(raw_data)
        decoded_text = decompressed.decode("utf-8")
        
        # Парсим JSON
        data = json.loads(decoded_text)
        
        # Извлекаем данные (учитываем структуру Sing-box)
        server = data.get('server')
        port = data.get('server_port')
        pk = data.get('private_key')
        pub = data.get('server_pub') or data.get('public_key')
        
        # Reserved: из списка [105, 102, 188] в строку "105-102-188"
        res_list = data.get('reserved', [0, 0, 0])
        res = "-".join(map(str, res_list))
        
        # Адреса: объединяем в одну строку через запятую
        addr_list = data.get('local_address', [])
        addr = ",".join(addr_list)
        
        if server and pk:
            # Формируем итоговую ссылку
            return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={addr}&reserved={res}&mtu=1280#WARP_{server}"
            
    except Exception:
        return None
    return None

def main():
    print(f"Загрузка: {SOURCE_URL}")
    try:
        r = requests.get(SOURCE_URL)
        r.raise_for_status()
        
        results = []
        for line in r.text.splitlines():
            line = line.strip()
            # Обрабатываем обе подписки одним кодом
            if line.startswith(('husi://', 'exclave://')):
                res = decode_husi(line)
                if res:
                    results.append(res)
        
        if results:
            with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
                f.write("\n".join(results))
            print(f"Успех! Собрано {len(results)} ссылок.")
        else:
            print("Ошибка: не удалось декодировать ни одной ссылки. Проверь логи выше.")
            
    except Exception as e:
        print(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
