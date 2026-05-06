# filter.py - Checks whether a request should be blocked
import threading
from config import BLOCKED_HOSTS, BLOCKED_IPS

blocked_hosts = list(BLOCKED_HOSTS)
lock = threading.Lock()

def is_blocked_ip(client_ip):
    return client_ip in BLOCKED_IPS


def is_blocked_host(host):
    with lock:
        return host in blocked_hosts

def is_blocked_host(host):
    with lock:
        return host in BLOCKED_HOSTS

def add_blocked_host(host):
    """Add a host to the blacklist at runtime (from the admin panel)."""
    with lock:
        if host not in blocked_hosts:
            blocked_hosts.append(host)
 
 
def get_blocked_hosts():
    """Return a copy of the current blacklist."""
    with lock:
        return list(blocked_hosts)
 

BLOCK_RESPONSE = (
    "403 Forbidden: This request has been blocked by the proxy.\r\n"
).encode() # Convert string to bytes (required for socket.sendall)