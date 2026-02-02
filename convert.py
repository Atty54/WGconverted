import base64
import zlib
import json
import requests
import sys


SOURCE_URL = "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/husi-wg.txt"
OUTPUT_FILE = "my_wg_sub.txt"


# ---------------------------
# Utils
# ---------------------------

def fix_padding(s: str) -> str:
    return s + "=" * (-len(s) % 4)


def b64decode_auto(data: str) -> bytes:
    data = fix_padding(data)

    try:
        return base64.urlsafe_b64decode(data)
    except:
        return base64.b64decode(data)


def zlib_decompress_auto(data: bytes) -> bytes:

    # gzip/zlib
    try:
        return zlib.decompress(data, zlib.MAX_WBITS | 32)
    except:
        pass

    # raw deflate
    try:
        return zlib.decompress(data, -zlib.MAX_WBITS)
    except:
        pass

    raise ValueError("zlib decompress failed")


# ---------------------------
# WG (Husi / Exclave)
# ---------------------------

def parse_wg(url: str):

    if not url.startswith(("husi://wg?", "exclave://wg?")):
        return None

    payload = url.split("?", 1)[1]

    raw = b64decode_auto(payload)
    decoded = zlib_decompress_auto(raw)

    text = decoded.decode("utf-8", errors="ignore").strip()

    # JSON
    if text.startswith("{"):

        data = json.loads(text)

        server = data.get("server")
        port = data.get("server_port", 51820)

        pk = data.get("private_key")
        pub = data.get("server_pub") or data.get("public_key")

        addrs = ",".join(data.get("local_address", []))

        res_list = data.get("reserved", [0, 0, 0])
        res = "-".join(map(str, res_list))

        if not (server and pk):
            raise ValueError("WG JSON missing fields")

        return (
            f"wg://{server}:{port}"
            f"?private_key={pk}"
            f"&public_key={pub}"
            f"&local_address={addrs}"
            f"&reserved={res}"
            f"&mtu=1280"
            f"#WARP_{server}"
        )

    # WG-Quick (ini)
    if "[Interface]" in text:

        pk = None
        addr = ""

        for line in text.splitlines():

            if line.startswith("PrivateKey"):
                pk = line.split("=", 1)[1].strip()

            if line.startswith("Address"):
                addr = line.split("=", 1)[1].strip()

        if not pk:
            raise ValueError("WG ini without private key")

        return f"wg://local?private_key={pk}&local_address={addr}#WG_LOCAL"

    raise ValueError("Unknown WG format")


# ---------------------------
# VLESS
# ---------------------------

def parse_vless(url: str):

    if not url.startswith("vless://"):
        return None

    return url


# ---------------------------
# VMESS
# ---------------------------

def parse_vmess(url: str):

    if not url.startswith("vmess://"):
        return None

    data = url[8:]

    raw = b64decode_auto(data)

    text = raw.decode("utf-8", errors="ignore")

    if not text.startswith("{"):
        raise ValueError("Bad vmess json")

    obj = json.loads(text)

    return url


# ---------------------------
# Shadowsocks
# ---------------------------

def parse_ss(url: str):

    if not url.startswith("ss://"):
        return None

    return url


# ---------------------------
# Dispatcher
# ---------------------------

def parse_line(line: str):

    parsers = [
        parse_wg,
        parse_vless,
        parse_vmess,
        parse_ss,
    ]

    for parser in parsers:
        try:
            result = parser(line)

            if result:
                return result

        except Exception as e:
            print(f"[WARN] {parser.__name__}: {e}", file=sys.stderr)

    return None


# ---------------------------
# Main
# ---------------------------

def main():

    print(f"[INFO] Downloading: {SOURCE_URL}")

    r = requests.get(SOURCE_URL, timeout=30)
    r.raise_for_status()

    ok = 0
    bad = 0

    results = []

    for i, line in enumerate(r.text.splitlines(), 1):

        line = line.strip()

        if not line or line.startswith("#"):
            continue

        res = parse_line(line)

        if res:
            results.append(res)
            ok += 1
        else:
            bad += 1
            print(f"[SKIP] line {i}: {line[:80]}", file=sys.stderr)

    print(f"[INFO] OK={ok} BAD={bad}")

    if not results:
        raise RuntimeError("No links parsed")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(results))

    print(f"[INFO] Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
