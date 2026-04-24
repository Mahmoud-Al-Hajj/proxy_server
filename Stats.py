# stats.py - Shared counters for the admin panel
# All functions are thread-safe using a lock.

import threading

_lock = threading.Lock()

_total_requests = 0
_cache_hits     = 0
_blocked        = 0


def record_request():
    global _total_requests
    with _lock:
        _total_requests += 1

def record_hit():
    global _cache_hits
    with _lock:
        _cache_hits += 1

def record_blocked():
    global _blocked
    with _lock:
        _blocked += 1

def get():
    with _lock:
        return {
            'total':   _total_requests,
            'hits':    _cache_hits,
            'blocked': _blocked,
        }