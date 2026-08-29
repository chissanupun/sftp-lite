"""SFTP-Lite server: TCP file-transfer service + UDP discovery beacon."""

import argparse
import os
import socket
import threading

from protocol import (
    ConnBuffer,
    DEFAULT_BROADCAST_ADDR,
    DEFAULT_DISCOVERY_PORT,
    DEFAULT_TCP_PORT,
    BEACON_INTERVAL_SEC,
    DISCOVERY_MAGIC,
    log,
)


def safe_filename(name):
    """Path traversal guard: reject anything with '/' or '..'."""
    if not name or "/" in name or "\\" in name or ".." in name or "\x00" in name:
        return None
    return name


def handle_store(conn, storage_dir, filename, size):
    # Validate the header BEFORE telling the client to send payload bytes.
    # If we reject here, the client must not have sent any file bytes yet —
    # otherwise those bytes sit in the stream and get misread as the next
    # command (session desync). Hence the 100 Continue handshake below.
    safe = safe_filename(filename)
    if safe is None:
        conn.send_line("400 Bad Request")
        log(">>", "400 Bad Request")
        return
    try:
        size = int(size)
    except ValueError:
        conn.send_line("400 Bad Request")
        log(">>", "400 Bad Request")
        return
    if size < 0:
        conn.send_line("400 Bad Request")
        log(">>", "400 Bad Request")
        return

    conn.send_line("100 Continue")
    log(">>", "100 Continue")

    path = os.path.join(storage_dir, safe)
    # Per-connection unique — two clients STOREing the same filename at once
    # must not share one temp file (same fd offset, interleaved writes).
    tmp_path = f"{path}.{threading.get_ident()}.{os.getpid()}.partial"
    received = 0
    last_pct = -1
    try:
        with open(tmp_path, "wb") as f:
            remaining = size
            while remaining > 0:
                chunk = conn.read_exact(min(4096, remaining))
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)
                remaining -= len(chunk)
                pct = int(received / size * 100) if size else 100
                if pct != last_pct:
                    print(f"    ...store {pct}% ({received}/{size} bytes)")
                    last_pct = pct
    except OSError:
        conn.send_line("500 Server Error")
        log(">>", "500 Server Error")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return

    if received != size:
        # Partial transfer — connection dropped mid-STORE. Discard, don't
        # leave a corrupt file behind.
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return  # connection is already gone, nothing to respond to

    os.replace(tmp_path, path)
    conn.send_line(f"201 Stored {size} bytes")
    log(">>", f"201 Stored {size} bytes")


def handle_get(conn, storage_dir, filename):
    safe = safe_filename(filename)
    if safe is None:
        conn.send_line("400 Bad Request")
        log(">>", "400 Bad Request")
        return
    path = os.path.join(storage_dir, safe)
    if not os.path.isfile(path):
        conn.send_line("404 Not Found")
        log(">>", "404 Not Found")
        return
    # Re-check right before opening: file could vanish between the isfile()
    # check above and here (e.g. a concurrent DELETE) — respond 500, not a
    # crash. Only guarded up to the first byte sent: once streaming starts,
    # the 200 OK header is already committed on the wire.
    try:
        size = os.path.getsize(path)
        f = open(path, "rb")
    except OSError:
        conn.send_line("500 Server Error")
        log(">>", "500 Server Error")
        return
    with f:
        conn.send_line(f"200 OK {size}")
        log(">>", f"200 OK {size}")
        sent = 0
        last_pct = -1
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            conn.send_bytes(chunk)
            sent += len(chunk)
            pct = int(sent / size * 100) if size else 100
            if pct != last_pct:
                print(f"    ...get {pct}% ({sent}/{size} bytes)")
                last_pct = pct


def handle_list(conn, storage_dir):
    names = sorted(
        n for n in os.listdir(storage_dir)
        if os.path.isfile(os.path.join(storage_dir, n)) and not n.endswith(".partial")
    )
    conn.send_line(f"200 OK {len(names)}")
    log(">>", f"200 OK {len(names)}")
    for n in names:
        conn.send_line(n)
        log(">>", n)


def handle_delete(conn, storage_dir, filename):
    safe = safe_filename(filename)
    if safe is None:
        conn.send_line("400 Bad Request")
        log(">>", "400 Bad Request")
        return
    path = os.path.join(storage_dir, safe)
    if not os.path.isfile(path):
        conn.send_line("404 Not Found")
        log(">>", "404 Not Found")
        return
    try:
        os.remove(path)
    except OSError:
        conn.send_line("500 Server Error")
        log(">>", "500 Server Error")
        return
    conn.send_line("200 OK Deleted")
    log(">>", "200 OK Deleted")


def client_session(sock, addr, storage_dir):
    print(f"[server] connection from {addr}")
    conn = ConnBuffer(sock)
    conn.send_line("220 SFTP-Lite ready")
    log(">>", "220 SFTP-Lite ready")

    try:
        while True:
            line = conn.read_line()
            if line is None:
                break
            log("<<", line)
            parts = line.split(" ", 2)
            cmd = parts[0].upper() if parts else ""

            if cmd == "STORE" and len(parts) == 3:
                handle_store(conn, storage_dir, parts[1], parts[2])
            elif cmd == "GET" and len(parts) == 2:
                handle_get(conn, storage_dir, parts[1])
            elif cmd == "LIST" and len(parts) == 1:
                handle_list(conn, storage_dir)
            elif cmd == "DELETE" and len(parts) == 2:
                handle_delete(conn, storage_dir, parts[1])
            elif cmd == "QUIT":
                conn.send_line("221 Closing")
                log(">>", "221 Closing")
                break
            else:
                conn.send_line("400 Bad Request")
                log(">>", "400 Bad Request")
    except ConnectionError:
        pass
    finally:
        sock.close()
        print(f"[server] connection from {addr} closed")


def run_tcp_server(host, port, storage_dir):
    os.makedirs(storage_dir, exist_ok=True)
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(5)
    print(f"[server] TCP listening on {host}:{port}, storage_dir={storage_dir}")
    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=client_session, args=(conn, addr, storage_dir), daemon=True)
        t.start()


def run_discovery_beacon(tcp_port, discovery_port, broadcast_addr):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    message = f"{DISCOVERY_MAGIC} {tcp_port}".encode("ascii")
    print(f"[discovery] broadcasting on {broadcast_addr}:{discovery_port} every {BEACON_INTERVAL_SEC}s")
    while True:
        sock.sendto(message, (broadcast_addr, discovery_port))
        threading.Event().wait(BEACON_INTERVAL_SEC)


def main():
    p = argparse.ArgumentParser(description="SFTP-Lite server")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=DEFAULT_TCP_PORT)
    p.add_argument("--storage-dir", default="./storage")
    p.add_argument("--discovery-port", type=int, default=DEFAULT_DISCOVERY_PORT)
    p.add_argument("--broadcast-addr", default=DEFAULT_BROADCAST_ADDR)
    p.add_argument("--no-discovery", action="store_true", help="disable the UDP discovery beacon")
    args = p.parse_args()

    if not args.no_discovery:
        beacon_thread = threading.Thread(
            target=run_discovery_beacon,
            args=(args.port, args.discovery_port, args.broadcast_addr),
            daemon=True,
        )
        beacon_thread.start()

    run_tcp_server(args.host, args.port, args.storage_dir)


if __name__ == "__main__":
    main()
