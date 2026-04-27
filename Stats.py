# stats.py - Shared counters for the admin panel
# All functions are thread-safe using a lock.

import threading

lock = threading.Lock()

total_requests = 0
cache_hits     = 0
blocked        = 0


def record_request():
    global total_requests
    with lock:
        total_requests += 1

def record_hit():
    global cache_hits
    with lock:
        cache_hits += 1

def record_blocked():
    global blocked
    with lock:
        blocked += 1

def get():
    with _lock:
        return {
            'total':   total_requests,
            'hits':    cache_hits,
            'blocked': blocked,
        }