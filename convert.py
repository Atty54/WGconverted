import base64
import msgpack
import requests

SOURCE_URL = "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt"
OUTPUT_FILE = "my_wg_sub.txt"

def decode_husi(url):
    try:
        if '?' not in url: return None
        # Извлекаем Base64 часть
        b64_part = url.split('?')[1].strip()
        
        # Стандартная очистка Base64 для URL
        b64_part = b64_part.replace('-', '+').replace('_', '/')
        b64_part += '=' * (-len(b64_part) % 4)
        
        # Декодируем Base64 в байты
        binary_data = base64.b64decode(b64_part)
        
        # Десериализуем MessagePack (БЕЗ zlib)
        # raw=False позволяет сразу получить строки вместо байтовых объектов
        data = msgpack.unpackb(binary_data, raw=False)
        
        # Извлекаем параметры
        server = data.get('server')
        port = data.get('server_port')
        pk = data.get('private_key')
        pub = data.get('server_pub') or data.get('public_key')
        
        # Форматируем Reserved
        res_list = data.get('reserved', [0, 0, 0])
        res = "-".join(map(str, res_list))
        
        # Форматируем адреса
        addrs = ",".join(data.get('local_address', []))
        
        if server and pk:
            return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={addrs}&reserved={res}&mtu=1280#WARP_{server}"
            
    except Exception as e:
        # Если MsgPack без сжатия не прошел, пробуем один раз со сжатием (на всякий случай)
        try:
            import zlib
            decompressed = zlib.decompress(base64.b64decode(b64_part), -15)
            data = msgpack.unpackb(decompressed, raw=False)
            # ... (логика извлечения такая же)
            return f"wg://{data['server']}:{data['server_port']}?private_key={data['private_key']}&public_key={data.get('server_pub')}&local_address={','.join(data.get('local_address', []))}&reserved={'-'.join(map(str, data.get('reserved', [])))}&mtu=1280#WARP_ALT"
        except:
            print(f"Ошибка декодирования: {e}")
            return None

def main():
    print(f"Загрузка {SOURCE_URL}...")
    try:
        r = requests.get(SOURCE_URL)
        r.raise_for_status()
        
        results = []
        for line in r.text.splitlines():
            line = line.strip()
            if "://" in line:
                link = decode_husi(line)
                if link:
                    results.append(link)
        
        if results:
            with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
                f.write("\n".join(results))
            print(f"Успех! Сгенерировано {len(results)} ссылок.")
        else:
            print("Не удалось получить ссылки. Проверь логи.")
            
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()
