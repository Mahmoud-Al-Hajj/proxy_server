# handler.py - Handles the full lifecycle of one client connection

import datetime
from config import BUFFER_SIZE
from logger import log
from parser import parse_request
from forwarder import fetch_from_server


def handle_client(client_socket, client_address):
    """
    Handle one client connection:
    receive request → parse → fetch → relay response.
    """
    client_ip, client_port = client_address
    log(f"Connection from {client_ip}:{client_port}")

    try:
        raw_data = client_socket.recv(BUFFER_SIZE)
        if not raw_data:
            return

        raw_request = raw_data.decode('utf-8', errors='replace')
        log(f"[{client_ip}:{client_port}] Request received | {raw_request.splitlines()[0]}")

        try:
            method, host, port, path = parse_request(raw_request)
        except ValueError as e:
            log(f"Bad request: {e}")
            client_socket.sendall(b"HTTP/1.0 400 Bad Request\r\n\r\nBad Request\r\n")
            return

        log(f"[{client_ip}:{client_port}] Request sent: http://{host}:{port}{path} (method: {method})")

#  open a socket to the real web server, send the HTTP request, and get the response.
        try:
            response = fetch_from_server(host, port, method, path)
        except Exception as e:
            log(f"[{client_ip}:{client_port}] Could not reach {host}: {e}")
            client_socket.sendall(b"HTTP/1.0 502 Bad Gateway\r\n\r\nBad Gateway\r\n")
            return

        response_str = response.decode('utf-8', errors='replace')
        status_line = response_str.splitlines()[0] # only show "HTTP/1.0 200 OK"
        log(f"[{client_ip}:{client_port}] Response received | { status_line }")
        
        client_socket.sendall(response)
        log(f"[{client_ip}:{client_port}] Response sent | {status_line}")

    except Exception as e:
        log(f"Unexpected error: {e}")

    finally:
        client_socket.close()
        log(f"Connection closed\n")
