# metrics.py - Tracks response times for cache hits and misses

import threading

lock = threading.Lock()
# each entry = { 'url': str, 'type': 'hit'|'miss', 'ms': float }
timings = []

MAX_TIMINGS = 100


def record(url, timing_type, ms):
    """
    Save a new timing entry.

    - timing_type: 'hit' or 'miss'
    - ms: response time in milliseconds
    """
    with lock:
        # Add new entry
        timings.append({
            'url': url,
            'type': timing_type,
            'ms': round(ms, 2)
        })

        # Keep list size under limit (remove oldest)
        if len(timings) > MAX_TIMINGS:
            timings.pop(0)


def get_summary():
    """
    Calculate and return performance statistics.
    """
    with lock:
        # Separate hit and miss timings
        hits = []
        misses = []

        for entry in timings:
            if entry['type'] == 'hit':
                hits.append(entry['ms'])
            elif entry['type'] == 'miss':
                misses.append(entry['ms'])

        # ── AVERAGES ────────────────────────────────
        avg_hit = None
        if hits:
            avg_hit = round(sum(hits) / len(hits), 2)

        avg_miss = None
        if misses:
            avg_miss = round(sum(misses) / len(misses), 2)

        # ── SPEEDUP ────────────────────────────────
        # How many times faster cache hits are compared to misses
        speedup = None
        if avg_hit and avg_miss and avg_hit > 0:
            speedup = round(avg_miss / avg_hit, 1)

        # ── TOTAL TIME SAVED ───────────────────────
        total_saved_ms = 0
        if avg_miss:
            for entry in timings:
                if entry['type'] == 'hit':
                    total_saved_ms += (avg_miss - entry['ms'])

            total_saved_ms = round(total_saved_ms, 2)

        # ── RECENT ENTRIES ─────────────────────────
        # Last 10 entries, newest first
        recent = []
        last_entries = timings[-10:]

        for entry in reversed(last_entries):
            recent.append(entry)

        # ── RESULT ─────────────────────────────────
        return {
            'avg_hit_ms': avg_hit,
            'avg_miss_ms': avg_miss,
            'speedup': speedup,
            'total_saved_ms': total_saved_ms,
            'hit_count': len(hits),
            'miss_count': len(misses),
            'recent': recent
        }