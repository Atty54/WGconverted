import base64
import zlib
import msgpack # Бинарный десериализатор
import requests

SOURCE_URL = "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt"
OUTPUT_FILE = "my_wg_sub.txt"

def decode_husi(url):
    try:
        # 1. Извлекаем и чистим Base64
        b64_part = url.split('?')[1].strip()
        b64_part = b64_part.replace('-', '+').replace('_', '/')
        # Добавляем padding
        b64_part += '=' * (-len(b64_part) % 4)
        
        # 2. Декодируем и разжимаем (Sing-box использует Raw Deflate)
        compressed = base64.b64decode(b64_part)
        decompressed = zlib.decompress(compressed, -15)
        
        # 3. Распаковываем MessagePack
        # raw=False преобразует байты строк в обычные строки Python
        data = msgpack.unpackb(decompressed, raw=False)
        
        # Теперь data — это обычный словарь (dict)
        server = data.get('server')
        port = data.get('server_port')
        pk = data.get('private_key')
        pub = data.get('server_pub')
        
        # Reserved в MsgPack обычно сохраняется как список
        res_list = data.get('reserved', [0, 0, 0])
        res = "-".join(map(str, res_list))
        
        # Адреса
        addrs = ",".join(data.get('local_address', []))
        
        if server and pk:
            return f"wg://{server}:{port}?private_key={pk}&public_key={pub}&local_address={addrs}&reserved={res}&mtu=1280#WARP_{server}"
            
    except Exception as e:
        print(f"Ошибка декодирования MsgPack: {e}")
        return None

def main():
    print(f"Загрузка {SOURCE_URL}...")
    r = requests.get(SOURCE_URL)
    results = []
    for line in r.text.splitlines():
        if "://" in line:
            link = decode_husi(line.strip())
            if link: results.append(link)
    
    if results:
        with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
            f.write("\n".join(results))
        print(f"Успех! Сгенерировано {len(results)} ссылок.")

if __name__ == "__main__":
    main()
