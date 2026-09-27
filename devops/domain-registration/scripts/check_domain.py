#!/usr/bin/env python3
"""Batch whois availability check: `check_domain.py 24qabul:uz 24zapis:com [.. .net .org]`.

.uz  -> whois.cctld.uz  (free: 'not found in database' / 'No match')
.com/.net/.org -> whois.verisign-grs.com (free: 'No match for')
Exit 0 always; per-line verdicts on stdout.
"""
import socket
import sys

SERVERS = {
    "uz": "whois.cctld.uz",
    "com": "whois.verisign-grs.com",
    "net": "whois.verisign-grs.com",
    "org": "whois.pir.org",
}


def whois(server: str, q: str) -> str:
    try:
        s = socket.create_connection((server, 43), timeout=8)
        s.sendall((q + "\r\n").encode())
        buf = b""
        while True:
            ch = s.recv(4096)
            if not ch:
                break
            buf += ch
        s.close()
        return buf.decode(errors="ignore")
    except Exception as e:  # noqa: BLE001
        return f"ERR {e}"


def check(name: str) -> str:
    parts = name.split(":")
    if len(parts) != 2 or parts[1] not in SERVERS:
        return f"{name:20} формат <имя>:<uz|com|net|org>"
    dom, tld = name + "." + parts[1], parts[1]
    r = whois(SERVERS[tld], dom)
    if r.startswith("ERR"):
        return f"{dom:20} whois недоступен: {r[:60]}"
    free = ("not found" in r.lower()) or ("no match" in r.lower())
    return f"{dom:20} {'СВОБОДЕН' if free else 'занят'}"


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    for a in args:
        print(check(a.strip().lower().removeprefix("www.")))


if __name__ == "__main__":
    main()
