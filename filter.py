# filter.py - Checks whether a request should be blocked

from config import BLOCKED_HOSTS, BLOCKED_IPS


def is_blocked_ip(client_ip):
    return client_ip in BLOCKED_IPS


def is_blocked_host(host):
    return host in BLOCKED_HOSTS


BLOCK_RESPONSE = (
    "403 Forbidden: This request has been blocked by the proxy.\r\n"
).encode()