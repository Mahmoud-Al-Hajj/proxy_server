# handler.py - Handles the full lifecycle of one client connection
# receive request → parse → check cache → fetch if needed → send response → close connection

import datetime
from config import BUFFER_SIZE
from logger import log
from parser import parse_request
from forwarder import fetch_from_server
from filter import is_blocked_ip, is_blocked_host, BLOCK_RESPONSE
import cache
import Stats

def handle_client(client_socket, client_address):
    """
    Handle one client connection:
    receive → filter → check cache → fetch if needed → relay response.
    """
    client_ip, client_port = client_address
    client_id = f"{client_ip}:{client_port}"

    log(f"Connection from {client_id}")

    try:
        Stats.record_request()
        if is_blocked_ip(client_ip):
            Stats.record_blocked()
            log(f"[{client_id}] BLOCKED IP | {datetime.datetime.now()} | connection refused")
            client_socket.sendall(BLOCK_RESPONSE)
            return

        data = client_socket.recv(BUFFER_SIZE)
        if not data:
            return

        request = data.decode('utf-8', errors='replace')
        request_line = request.split('\r\n')[0]

        log(f"[{client_id}] Request received  | {datetime.datetime.now()} | {request_line}")
        log(f"[{client_id}] Full request:\n{raw_request.strip()}\n")

        # ── Parse request ──────────────────────────────
        try:
            method, host, port, path = parse_request(request)
        except ValueError as e:
            log(f"[{client_id}] Bad request: {e}")
            client_socket.sendall(b"HTTP/1.0 400 Bad Request\r\n\r\nBad Request\r\n")
            return

        if is_blocked_host(host):
            Stats.record_blocked()
            log(f"[{client_id}] BLOCKED HOST      | {datetime.datetime.now()} | {host}")
            client_socket.sendall(BLOCK_RESPONSE)
            return
            
        url = f"http://{host}:{port}{path}"

        # ── CACHE CHECK ────────────────────────────────
        cached_response = cache.get(url)

        if cached_response:
            Stats.record_hit()

            log(f"[{client_id}] Cache HIT | {url}")
            client_socket.sendall(cached_response)
            log(f"[{client_id}] Response sent from cache | {url}")
            return

        log(f"[{client_id}] Cache MISS        | {datetime.datetime.now()} | {url}")
        log(f"[{client_id}] Request forwarded | {datetime.datetime.now()} | {method} {url}")


        # ── FETCH FROM SERVER ──────────────────────────
        try:
            response = fetch_from_server(host, port, method, path)
        except Exception as e:
            log(f"[{client_id}] Could not reach {host}: {e}")
            client_socket.sendall(b"HTTP/1.0 502 Bad Gateway\r\n\r\nBad Gateway\r\n")
            return

        status_line = response.split(b'\r\n', 1)[0].decode('utf-8', errors='replace')

        log(f"[{client_id}] Response received | {datetime.datetime.now()} | {status_line} ({len(response)} bytes)")
        log(f"[{client_id}] Response headers:\n{response_headers}\n")


        # ── STORE IN CACHE ─────────────────────────────
        cache.store(url, response)
        log(f"[{client_id}] Stored in cache   | {url} (cache size: {cache.size()})")


        # ── SEND RESPONSE ──────────────────────────────
        client_socket.sendall(response)
        log(f"[{client_id}] Response sent     | {datetime.datetime.now()} | {len(response)} bytes → client")

    except Exception as e:
        log(f"[{client_id}] Unexpected error: {e}")

    finally:
        client_socket.close()
        log(f"[{client_id}] Connection closed")

