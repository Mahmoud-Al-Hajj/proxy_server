# cache.py - In-memory cache for GET responses
import time
import threading
import config

cacheStore = {}
# key   → URL
# value → { response, timestamp, last_used }

# Lock ensures thread-safe access since multiple clients (threads)
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
# Note: with lock means only one thread can run this part of code, others wait
    with lock:
        entry = cacheStore.get(url)
        if not entry:
            return None

        now = time.time()

        # Check expiration
        # If current time - stored time > TTL → expired
        if now - entry['timestamp'] > CACHE_TTL:
            cacheStore.pop(url, None)
            return None

        entry['last_used'] = now
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
        if url in cacheStore:
            cacheStore[url] = {
                'response': response,
                'timestamp': now,
                'last_used': now
            }
            return

        if len(cacheStore) >= CACHE_MAX_SIZE:

            # Find the least recently used entry manually
            lru_url = None
            oldest_time = float('inf') # Start with a very large number so any real timestamp is smaller
            
            for key, value in cacheStore.items():
                if value['last_used'] < oldest_time:
                    oldest_time = value['last_used']
                    lru_url = key

            cacheStore.pop(lru_url, None)

        cacheStore[url] = {
            'response': response,
            'timestamp': now,
            'last_used': now
        }

def clear():
    with lock:
        cacheStore.clear()

def size():
    with lock:
        return len(cacheStore)

def keys():
    """Return all cached URLs."""
    with lock:
        return list(cacheStore.keys())