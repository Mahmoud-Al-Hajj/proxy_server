# handler.py - Handles the full lifecycle of one client connection
# receive request → parse → check cache → fetch if needed → send response → close connection

import datetime
from config import BUFFER_SIZE
from logger import log
from parser import parse_request
from forwarder import fetch_from_server
import cache


def handle_client(client_socket, client_address):
    """
    Handle one client connection:
    receive request → parse → check cache → fetch → relay response.
    """
    client_ip, client_port = client_address
    client_id = f"{client_ip}:{client_port}"

    log(f"Connection from {client_id}")

    try:
        raw_data = client_socket.recv(BUFFER_SIZE)
        if not raw_data:
            return

        raw_request = raw_data.decode('utf-8', errors='replace')
        request_line = raw_request.split('\r\n')[0]

        log(f"[{client_id}] Request received | {request_line}")

        # ── Parse request ──────────────────────────────
        try:
            method, host, port, path = parse_request(raw_request)
        except ValueError as e:
            log(f"[{client_id}] Bad request: {e}")
            client_socket.sendall(b"HTTP/1.0 400 Bad Request\r\n\r\nBad Request\r\n")
            return

        url = f"http://{host}:{port}{path}"

        # ── CACHE CHECK ────────────────────────────────
        cached_response = cache.get(url)

        if cached_response:
            log(f"[{client_id}] Cache HIT | {url}")
            client_socket.sendall(cached_response)
            log(f"[{client_id}] Response sent from cache | {url}")
            return

        log(f"[{client_id}] Cache MISS | {url}")

        # ── FETCH FROM SERVER ──────────────────────────
        try:
            response = fetch_from_server(host, port, method, path)
        except Exception as e:
            log(f"[{client_id}] Could not reach {host}: {e}")
            client_socket.sendall(b"HTTP/1.0 502 Bad Gateway\r\n\r\nBad Gateway\r\n")
            return

        status_line = response.split(b'\r\n', 1)[0].decode('utf-8', errors='replace')

        log(f"[{client_id}] Response received | {status_line}")

        # ── STORE IN CACHE ─────────────────────────────
        cache.store(url, response)
        log(f"[{client_id}] Stored in cache | {url}")

        # ── SEND RESPONSE ──────────────────────────────
        client_socket.sendall(response)
        log(f"[{client_id}] Response sent | {status_line}")

    except Exception as e:
        log(f"[{client_id}] Unexpected error: {e}")

    finally:
        client_socket.close()
        log(f"[{client_id}] Connection closed")