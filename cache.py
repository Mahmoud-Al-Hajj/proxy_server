# cache.py - In-memory cache for GET responses
import time
import threading
import config

cache = {}
# key   → URL
# value → { response, timestamp, last_used }


# Note: with lock means only one thread can run this part of code, others wait
lock = threading.Lock()

CACHE_TTL = config.CACHE_TTL
CACHE_MAX_SIZE = config.CACHE_MAX_SIZE


def get(url):
    """
    Retrieve cached response if it exists and is still valid.

    Flow:
    1. Check if entry exists
    2. Check if expired (TTL)
    3. Update last_used (LRU behavior)
    4. Return response
    """
    with lock:
        entry = cache.get(url)
        if not entry:
            return None

        now = time.time()

        # Check expiration
        if now - entry['timestamp'] > CACHE_TTL:
            cache.pop(url, None)
            return None

        return entry['response']



def store(url, response):
    """
    Store a response in cache.

    Behavior:
    - If exists → update
    - If full → remove least recently used
    - Insert new entry
    """
    with lock:
        now = time.time()

        # ── UPDATE EXISTING ENTRY ────────────────────
        if url in cache:
            cache[url] = {
                'response': response,
                'timestamp': now,
                'last_used': now
            }
            return

        if len(cache) >= CACHE_MAX_SIZE:

            # Find the least recently used entry manually
            lru_url = None
            oldest_time = float('inf')
            
            for key, value in cache.items():
                if value['last_used'] < oldest_time:
                    oldest_time = value['last_used']
                    lru_url = key

            cache.pop(lru_url, None)

        cache[url] = {
            'response': response,
            'timestamp': now,
            'last_used': now
        }

def clear():
    with lock:
        cache.clear()

def size():
    with lock:
        return len(cache)

def keys():
    """Return all cached URLs."""
    with lock:
        return list(cache.keys())