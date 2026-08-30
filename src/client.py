"""SFTP-Lite client CLI: store, get, list, delete, discover."""

import argparse
import os
import socket
import sys
import time

from protocol import (
    ConnBuffer,
    DEFAULT_DISCOVERY_PORT,
    DEFAULT_TCP_PORT,
    DISCOVERY_MAGIC,
    log,
)


def connect(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    conn = ConnBuffer(sock)
    greeting = conn.read_line()
    log("<<", greeting)
    return sock, conn


def quit_session(conn):
    # Server may already have dropped the socket (crash, killed mid-demo) —
    # fail quietly instead of a raw traceback on the client's last line.
    try:
        conn.send_line("QUIT")
        log(">>", "QUIT")
        reply = conn.read_line()
        log("<<", reply)
    except (ConnectionError, OSError):
        pass


def cmd_store(host, port, local_path):
    if not os.path.isfile(local_path):
        print(f"error: local file not found: {local_path}")
        return 1
    size = os.path.getsize(local_path)
    filename = os.path.basename(local_path)

    sock, conn = connect(host, port)
    try:
        header = f"STORE {filename} {size}"
        conn.send_line(header)
        log(">>", header)

        reply = conn.read_line()
        log("<<", reply)
        if reply is None or not reply.startswith("100"):
            # Server rejected the header (400) — do NOT send payload, or the
            # bytes would sit in the stream and desync the next command.
            print("store rejected, aborting (no payload sent)")
            quit_session(conn)
            return 1

        with open(local_path, "rb") as f:
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
                    print(f"    ...store {pct}% ({sent}/{size} bytes)")
                    last_pct = pct
        reply = conn.read_line()
        log("<<", reply)
        quit_session(conn)
    finally:
        sock.close()
    return 0


def cmd_get(host, port, filename, out_path):
    sock, conn = connect(host, port)
    try:
        line = f"GET {filename}"
        conn.send_line(line)
        log(">>", line)
        reply = conn.read_line()
        log("<<", reply)
        if reply is None:
            print("error: connection closed unexpectedly")
            return 1
        parts = reply.split(" ")
        if parts[0] != "200" or len(parts) < 3:
            quit_session(conn)
            return 1
        try:
            size = int(parts[2])
        except ValueError:
            print(f"error: malformed response: {reply}")
            quit_session(conn)
            return 1
        dest = os.path.expanduser(out_path) if out_path else filename
        if os.path.isdir(dest):
            dest = os.path.join(dest, os.path.basename(filename))
        received = 0
        last_pct = -1
        with open(dest, "wb") as f:
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
                    print(f"    ...get {pct}% ({received}/{size} bytes)")
                    last_pct = pct
        if received != size:
            print("error: connection dropped mid-transfer, file incomplete")
            os.remove(dest)
            return 1
        print(f"saved to {dest}")
        quit_session(conn)
    finally:
        sock.close()
    return 0


def cmd_list(host, port):
    sock, conn = connect(host, port)
    try:
        conn.send_line("LIST")
        log(">>", "LIST")
        reply = conn.read_line()
        log("<<", reply)
        if reply is None:
            print("error: connection closed unexpectedly")
            return 1
        parts = reply.split(" ")
        if parts[0] != "200" or len(parts) < 3:
            quit_session(conn)
            return 1
        try:
            count = int(parts[2])
        except ValueError:
            print(f"error: malformed response: {reply}")
            quit_session(conn)
            return 1
        for _ in range(count):
            name = conn.read_line()
            log("<<", name)
            print(f"  {name}")
        quit_session(conn)
    finally:
        sock.close()
    return 0


def cmd_delete(host, port, filename):
    sock, conn = connect(host, port)
    try:
        line = f"DELETE {filename}"
        conn.send_line(line)
        log(">>", line)
        reply = conn.read_line()
        log("<<", reply)
        quit_session(conn)
        if reply is None or not reply.startswith("200"):
            return 1
    finally:
        sock.close()
    return 0


def cmd_discover(discovery_port, timeout):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", discovery_port))
    print(f"listening for SFTP-Lite servers for {timeout}s...")
    found = set()
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        sock.settimeout(remaining)
        try:
            data, addr = sock.recvfrom(1024)
        except socket.timeout:
            break
        text = data.decode("ascii", errors="replace")
        if text.startswith(DISCOVERY_MAGIC):
            beacon_parts = text.split(" ")
            if len(beacon_parts) < 2:
                continue  # malformed beacon, ignore rather than crash
            tcp_port = beacon_parts[1]
            key = (addr[0], tcp_port)
            if key not in found:
                found.add(key)
                print(f"found server: {addr[0]}:{tcp_port}")
    if not found:
        print("no servers found")
        return 1
    return 0


def main():
    p = argparse.ArgumentParser(description="SFTP-Lite client")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=DEFAULT_TCP_PORT)
    p.add_argument("--discovery-port", type=int, default=DEFAULT_DISCOVERY_PORT)
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("store")
    sp.add_argument("file")

    sp = sub.add_parser("get")
    sp.add_argument("file")
    sp.add_argument("--out", default=None)

    sub.add_parser("list")

    sp = sub.add_parser("delete")
    sp.add_argument("file")

    sp = sub.add_parser("discover")
    sp.add_argument("--timeout", type=int, default=5)

    args = p.parse_args()

    if args.command == "store":
        rc = cmd_store(args.host, args.port, args.file)
    elif args.command == "get":
        rc = cmd_get(args.host, args.port, args.file, args.out)
    elif args.command == "list":
        rc = cmd_list(args.host, args.port)
    elif args.command == "delete":
        rc = cmd_delete(args.host, args.port, args.file)
    elif args.command == "discover":
        rc = cmd_discover(args.discovery_port, args.timeout)
    else:
        rc = 1
    sys.exit(rc)


if __name__ == "__main__":
    main()
