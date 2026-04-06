# proxy.py - Entry point. Starts the proxy server.

import socket
from config import PROXY_HOST, PROXY_PORT
from logger import log
from handler import handle_client


def start_proxy():
    """Create the server socket and accept incoming client connections."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((PROXY_HOST, PROXY_PORT))
    server_socket.listen(10)

    log(f"Proxy running on {PROXY_HOST}:{PROXY_PORT}")
    log("Press Ctrl+C to stop.\n")

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            handle_client(client_socket, client_address)
    except KeyboardInterrupt:
        log("Proxy stopped.")
    finally:
        server_socket.close()


if __name__ == '__main__':
    start_proxy()