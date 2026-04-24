# console + file logging (Level 4)
# logger.py - Handles all console logging for the proxy

import datetime
from config import LOG_FILE

def log(message):
    """Print a timestamped message to the console and append it to the log file."""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {message}"
    print(line)

    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')