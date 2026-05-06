# proxy.py - Entry point. Starts the proxy server.

import socket
import threading
from config import PROXY_HOST, PROXY_PORT
from logger import log
from handler import handle_client
from Admin import start_admin


def start_proxy():
    """Create the server socket and accept incoming client connections."""
    
    # Create TCP socket using IPv4 and TCP
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# bind socket to the IP and the port
    server_socket.bind((PROXY_HOST, PROXY_PORT))
    server_socket.listen(10)
    
    start_admin()

    log(f"Proxy running on {PROXY_HOST}:{PROXY_PORT}")
    log("Press Ctrl+C to stop.\n")

    try:
        while True:
            #socket used to communicate with client | (IP,port) of client
            client_socket, client_address = server_socket.accept()

            # Spawn a new thread for this client so we can immediately
            # go back and accept the next one without waiting.
            thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address)
            )
            thread.daemon = True   # thread dies immediately intead of waiting to finish when exiting.
            thread.start()

    except KeyboardInterrupt:
        log("Proxy stopped.")
    finally:
        server_socket.close()


if __name__ == '__main__':
    start_proxy()
