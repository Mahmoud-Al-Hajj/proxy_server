# console + file logging (Level 4)
# logger.py - Handles all console logging for the proxy

import datetime
 
def log(message):
    """Print a timestamped message to the console."""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")
 