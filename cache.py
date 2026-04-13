# cache.py - In-memory cache for GET responses
import time
import threading
import config

cache = {}
lock = threading.Lock()

CACHE_TTL = config.CACHE_TTL
CACHE_MAX_SIZE = config.CACHE_MAX_SIZE


def get(url):
    """
    Return the cached response for this URL if it exists and is still fresh.
    Returns None on a cache miss or expired entry.
    """
    # Note: with lock means only one thread can run this part of code, others wait
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
    Save a response in the cache.
    If the cache is full, evict the oldest entry first.
    """
    with lock:
        now = time.time()

        # Update existing
        if url in cache:
            cache[url] = {'response': response, 'timestamp': now}
            return

        # Evict oldest (first inserted)
        if len(cache) >= CACHE_MAX_SIZE:
            oldest = next(iter(cache))   # first key in dict
            cache.pop(oldest, None)

        cache[url] = {'response': response, 'timestamp': now}


def size():
    with lock:
        return len(cache)