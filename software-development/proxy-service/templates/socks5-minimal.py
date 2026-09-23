#!/usr/bin/env python3
"""Минимальный SOCKS5 прокси (no-auth) для быстрого теста.
   0 зависимостей, только stdlib.
   НЕ для продакшна — open proxy, нет лимитов, нет логов."""
import sys
import os
import socket
import select
import threading

PROXY_HOST = "0.0.0.0"
PROXY_PORT = 1080
MAX_WORKERS = 64


def handle_client(conn):
    remote = None
    try:
        # 1. Handshake
        ver, nmethods = conn.recv(2)
        if ver != 5:
            return
        conn.recv(nmethods)
        conn.sendall(bytes([5, 0]))  # no auth

        # 2. Request
        data = conn.recv(4)
        ver, cmd, rsv, atyp = data
        if ver != 5 or cmd != 1:  # только CONNECT
            conn.sendall(bytes([5, 7, 0, 1, 0, 0, 0, 0, 0, 0]))
            return

        if atyp == 1:       # IPv4
            addr = socket.inet_ntoa(conn.recv(4))
        elif atyp == 3:     # domain
            addr_len = conn.recv(1)[0]
            addr = conn.recv(addr_len).decode()
        elif atyp == 4:     # IPv6
            addr = socket.inet_ntop(socket.AF_INET6, conn.recv(16))
        else:
            return

        port = int.from_bytes(conn.recv(2), 'big')

        # 3. Connect to target
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.settimeout(10)
        remote.connect((addr, port))

        # 4. Reply success
        bind_addr = remote.getsockname()
        conn.sendall(bytes([5, 0, 0, 1]) +
                     socket.inet_aton(bind_addr[0]) +
                     bind_addr[1].to_bytes(2, 'big'))

        # 5. Relay (bidirectional)
        conn.setblocking(False)
        remote.setblocking(False)
        while True:
            r, _, _ = select.select([conn, remote], [], [])
            if conn in r:
                data = conn.recv(65536)
                if not data:
                    break
                remote.sendall(data)
            if remote in r:
                data = remote.recv(65536)
                if not data:
                    break
                conn.sendall(data)
    except Exception:
        pass
    finally:
        for s in (conn, remote):
            try:
                s.close()
            except Exception:
                pass


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((PROXY_HOST, PROXY_PORT))
    server.listen(MAX_WORKERS)
    print(f"SOCKS5 running on {PROXY_HOST}:{PROXY_PORT}", flush=True)

    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_client, args=(conn,), daemon=True)
        t.start()


if __name__ == "__main__":
    main()
