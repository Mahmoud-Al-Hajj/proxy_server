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

        log(f"Request received at {datetime.datetime.now()}")
        raw_request = raw_data.decode('utf-8', errors='replace') # decode bytes to string, replace errors

#extract the HTTP method (GET), hostname, port, and request path from the raw string.
        try:
            method, host, port, path = parse_request(raw_request)
        except ValueError as e:
            log(f"Bad request: {e}")
            client_socket.sendall(b"HTTP/1.0 400 Bad Request\r\n\r\nBad Request\r\n")
            return

        log(f"URL: http://{host}:{port}{path}")

#  open a socket to the real web server, send the HTTP request, and get the response.
        try:
            response = fetch_from_server(host, port, method, path)
        except Exception as e:
            log(f"Could not reach {host}: {e}")
            client_socket.sendall(b"HTTP/1.0 502 Bad Gateway\r\n\r\nBad Gateway\r\n")
            return

        log(f"Response received: {len(response)} bytes")
        client_socket.sendall(response)
        log(f"Response sent at {datetime.datetime.now()}")

    except Exception as e:
        log(f"Unexpected error: {e}")

    finally:
        client_socket.close()
        log(f"Connection closed\n")
