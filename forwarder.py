# forwarder.py - Handles forwarding requests to the target web server

import socket
import threading
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

    # Read the full response
    response = b'' #b is bytes
    while True:
        chunk = server_socket.recv(BUFFER_SIZE)
        if not chunk:
            break
        response += chunk

    server_socket.close()
    return response


def forward(source, destination):
    while True:
        data = source.recv(BUFFER_SIZE)
        if not data:
            break
        destination.sendall(data)

def tunnel(client_socket, host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((host, port))

    # Tell the client the tunnel is ready
    client_socket.sendall(b"HTTP/1.0 200 Connection Established\r\n\r\n")

    # One thread sends client → server, the other sends server → client
    t1 = threading.Thread(target=forward, args=(client_socket, server_socket))
    t2 = threading.Thread(target=forward, args=(server_socket, client_socket))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    server_socket.close()




    