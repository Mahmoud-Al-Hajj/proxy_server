# forwarder.py - Handles forwarding requests to the target web server

import socket
from config import BUFFER_SIZE


def fetch_from_server(host, port, method, path):
    """
    Connect to the target web server, send the request,
    and return the full response as bytes.
    """
    # HTTP/1.0 to avoid chunked encoding complexity
    request = (
        f"{method} {path} HTTP/1.0\r\n"
        f"Host: {host}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    )

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((host, port))
    server_socket.sendall(request.encode())

    # Read the full response in chunks
    response = b''
    while True:
        chunk = server_socket.recv(BUFFER_SIZE)
        if not chunk:
            break
        response += chunk

    server_socket.close()
    return response